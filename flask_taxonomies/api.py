import jsonpatch
import jsonpointer
import sqlalchemy
from flask import current_app
from flask_sqlalchemy import get_state
from slugify import slugify
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.util import deprecated
from sqlalchemy_utils import Ltree

from .constants import INCLUDE_DATA, INCLUDE_DESCENDANTS
from .models import Taxonomy, TaxonomyTerm, TermStatusEnum, TaxonomyError
from .signals import before_taxonomy_created, after_taxonomy_created, before_taxonomy_updated, \
    after_taxonomy_updated, before_taxonomy_deleted, after_taxonomy_deleted, before_taxonomy_term_created, \
    after_taxonomy_term_created, before_taxonomy_term_deleted, after_taxonomy_term_deleted, \
    before_taxonomy_term_updated, after_taxonomy_term_updated, before_taxonomy_term_moved, after_taxonomy_term_moved

import logging

log = logging.getLogger(__name__)


class TermIdentification:
    def __init__(self, taxonomy=None, parent=None, slug=None, term=None):
        if term:
            if parent:
                raise TaxonomyError('`parent` should not be used when `term` is specified')
            if taxonomy:
                raise TaxonomyError('`taxonomy` should not be used when `term` is specified')
            if slug:
                raise TaxonomyError('`slug` should not be used when `term` is specified')
        elif parent:
            if not slug:
                raise TaxonomyError('`slug` must be used when `parent` is specified')
            if taxonomy:
                raise TaxonomyError('`taxonomy` must not be used when `parent` is specified')
        elif taxonomy:
            if not slug:
                raise TaxonomyError('`slug` must be used when `taxonomy` is specified')
        else:
            if not slug or '/' not in slug:
                raise TaxonomyError(
                    '`slug` including taxonomy code must be used when no other parameters are specified')

        if not term:
            if not parent:
                if taxonomy is None:
                    taxonomy, slug = slug.split('/', maxsplit=1)
            elif isinstance(parent, str):
                slug = parent + '/' + slug
                taxonomy, slug = slug.split('/', maxsplit=1)
            else:
                slug = parent.slug + '/' + slug
                taxonomy = parent.taxonomy_id

        self.term = term
        self.taxonomy = taxonomy
        self.slug = slug

    def _filter_taxonomy(self, query):
        if isinstance(self.taxonomy, Taxonomy):
            return query.filter(TaxonomyTerm.taxonomy_id == self.taxonomy.id)
        elif isinstance(self.taxonomy, str):
            return query.join(Taxonomy).filter(Taxonomy.code == self.taxonomy)
        else:
            return query.filter(TaxonomyTerm.taxonomy_id == self.taxonomy)

    def parent_identification(self):
        if self.term:
            if not self.term.parent_id:
                return None
            return TermIdentification(term=self.term.parent)
        if '/' not in self.slug:
            return None
        return TermIdentification(taxonomy=self.taxonomy, slug='/'.join(self.slug.split('/')[:-1]))

    def term_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(TaxonomyTerm.id == self.term.id)
        ret = self._filter_taxonomy(ret)
        if self.slug:
            ret = ret.filter(TaxonomyTerm.slug == self.slug)
        return ret

    def descendant_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(
                TaxonomyTerm.taxonomy_id == self.term.taxonomy_id,
                TaxonomyTerm.slug.descendant_of(self.term.slug),
            )
        ret = self._filter_taxonomy(ret)
        if self.slug:
            ret = ret.filter(TaxonomyTerm.slug.descendant_of(self.slug))
        return ret

    def ancestor_query(self, session):
        ret = session.query(TaxonomyTerm)
        if self.term:
            return ret.filter(
                TaxonomyTerm.taxonomy_id == self.term.taxonomy_id,
                TaxonomyTerm.slug.ancestor_of(self.term.slug),
            )
        ret = self._filter_taxonomy(ret)
        return ret.filter(TaxonomyTerm.slug.ancestor_of(self.slug))

    @property
    def leaf_slug(self):
        if self.slug:
            return self.slug.split('/')[-1]
        if self.term:
            return self.term.slug.split('/')[-1]

    @property
    def whole_slug(self):
        if self.slug:
            return self.slug
        if self.term:
            return self.term.slug

    def get_taxonomy(self, session):
        if isinstance(self.taxonomy, Taxonomy):
            return self.taxonomy
        if self.term:
            return self.term.taxonomy
        if isinstance(self.taxonomy, str):
            return session.query(Taxonomy).filter(Taxonomy.code == self.taxonomy).one()
        else:
            return session.query(Taxonomy).filter(Taxonomy.id == self.taxonomy).one()

    def __eq__(self, other):
        if not isinstance(other, TermIdentification):
            return False
        if self.term:
            if other.term:
                return self.term == other.term
            # other is taxonomy, slug
            if other.slug != self.term.slug:
                return False
            # check if in the same taxonomy
            if isinstance(other.taxonomy, Taxonomy):
                return other.taxonomy.id == self.term.taxonomy_id
            if isinstance(other.taxonomy, str):
                return other.taxonomy == self.term.taxonomy.code
            return other.taxonomy == self.term.taxonomy_id
        if other.term:
            return other == self
        # note: taxonomy
        self_tax = _coerce_tax(self.taxonomy, other.taxonomy)
        other_tax = _coerce_tax(other.taxonomy, self_tax)

        if type(self_tax) != type(other_tax):
            raise ValueError('Can not compare different types of taxonomy identification: %s(%s), %s(%s)' % (
                self_tax, type(self_tax), other_tax, type(other_tax)
            ))

        return self_tax == other_tax and self.slug == other.slug

    @property
    def level(self):
        if self.term:
            return self.term.level
        return len(self.slug.split('/')) - 1

    def contains(self, other):
        if self.whole_slug == other.whole_slug:
            return True
        return other.whole_slug.startswith(self.whole_slug + '/')


def _coerce_tax(tax, target):
    if isinstance(target, Taxonomy):
        return tax
    if isinstance(tax, Taxonomy):
        if isinstance(target, str):
            return tax.code
        return tax.id
    return tax


def _coerce_ti(ti):
    if isinstance(ti, TermIdentification):
        return ti
    if isinstance(ti, TaxonomyTerm):
        return TermIdentification(term=ti)
    return TermIdentification(slug=ti)


class Api:
    def __init__(self, app=None):
        self.app = app

    @property
    def session(self):
        db = get_state(self.app).db
        return db.session

    def list_taxonomies(self, session=None):
        """Return a list of all available taxonomies."""
        session = session or self.session
        return self.session.query(Taxonomy)

    @deprecated(version='7.0.0')
    def taxonomy_list(self):
        return self.list_taxonomies()  # pragma: no cover

    def get_taxonomy(self, code, session=None):
        session = session or self.session
        return session.query(Taxonomy).filter(Taxonomy.code == code).one()

    def create_taxonomy(self, code, extra_data=None, url=None, session=None) -> Taxonomy:
        """Creates a new taxonomy.
        :param code: taxonomy code
        :param extra_data: taxonomy metadata
        :param session: use a different db session
        :raises IntegrityError
        :returns Taxonomy
        """
        session = session or self.session
        with session.begin_nested():
            before_taxonomy_created.send(self, code=code, extra_data=extra_data)
            created = Taxonomy(code=code, url=url, extra_data=extra_data)
            session.add(created)
            after_taxonomy_created.send(created)
        return created

    def update_taxonomy(self, taxonomy: [Taxonomy, str], extra_data, session=None) -> Taxonomy:
        """Updates a taxonomy.
        :param taxonomy: taxonomy instance to be updated
        :param extra_data: new taxonomy metadata
        :param session: use a different db session
        :return Taxonomy: updated taxonomy
        """
        session = session or self.session
        if isinstance(taxonomy, str):
            taxonomy = session.query(Taxonomy).filter(Taxonomy.code == taxonomy).one()
        with session.begin_nested():
            before_taxonomy_updated.send(taxonomy, taxonomy=taxonomy, extra_data=extra_data)
            taxonomy.extra_data = extra_data
            flag_modified(taxonomy, "extra_data")
            session.add(taxonomy)
            after_taxonomy_updated.send(taxonomy, taxonomy=taxonomy)
        return taxonomy

    def delete_taxonomy(self, taxonomy: Taxonomy, session=None):
        """Delete a taxonomy.
        :param taxonomy: taxonomy instance to be deleted
        :param session: use a different db session
        :raise TaxonomyError
        """
        session = session or self.session
        with session.begin_nested():
            before_taxonomy_deleted.send(taxonomy, taxonomy=taxonomy)
            session.delete(taxonomy)
            after_taxonomy_deleted.send(taxonomy)

    def list_taxonomy(self, taxonomy: [Taxonomy, str], levels=None,
                      status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                      order=True, session=None):
        session = session or self.session
        if isinstance(taxonomy, Taxonomy):
            query = session.query(TaxonomyTerm).filter(TaxonomyTerm.taxonomy_id == taxonomy.id)
        else:
            query = session.query(TaxonomyTerm).join(Taxonomy).filter(Taxonomy.code == taxonomy)
        if status_cond is not None:
            query = query.filter(status_cond)
        if levels is not None:
            query = query.filter(TaxonomyTerm.level < levels)
        if order:
            query = query.order_by(TaxonomyTerm.slug)
        return query

    def taxonomy_url(self, taxonomy: [Taxonomy, str], descendants=False):
        proto = current_app.config.get('FLASK_TAXONOMIES_PROTOCOL')
        prefix = current_app.config.get('FLASK_TAXONOMIES_URL_PREFIX')
        base = current_app.config.get('FLASK_TAXONOMIES_SERVER_NAME')
        if not base:
            base = current_app.config.get('SERVER_NAME')
        if not base:
            log.error('Error retrieving taxonomies, FLASK_TAXONOMIES_SERVER_NAME nor SERVER_NAME set')
            base = 'localhost'
        ret = '{}://{}{}{}/'.format(
            proto,
            base,
            prefix,
            taxonomy.code if isinstance(taxonomy, Taxonomy) else taxonomy
        )
        if descendants:
            ret = ret + '?representation:include=' + INCLUDE_DESCENDANTS
        return ret

    def taxonomy_term_url(self, taxonomy_term: TaxonomyTerm, descendants=False):
        taxonomy_url = self.taxonomy_url(taxonomy_term.taxonomy_code)
        ret = taxonomy_url + taxonomy_term.slug
        if descendants:
            ret = ret + '?representation:include=' + INCLUDE_DESCENDANTS
        return ret

    def create_term(self, ti: TermIdentification, extra_data=None, session=None):
        """Creates a taxonomy term identified by term identification
        """
        ti = _coerce_ti(ti)
        session = session or self.session
        with session.begin_nested():
            parent_identification = ti.parent_identification()
            if parent_identification:
                parent = parent_identification.term_query(session).one()
                if parent.status != TermStatusEnum.alive:
                    raise TaxonomyError('Can not create term inside inactive parent')
            else:
                parent = None

            slug = self._slugify(parent.slug if parent else None, ti.leaf_slug)
            taxonomy = ti.get_taxonomy(session)
            before_taxonomy_term_created.send(taxonomy, slug=slug, extra_data=extra_data)

            parent = TaxonomyTerm(slug=slug,
                                  extra_data=extra_data,
                                  level=(parent.level + 1) if parent else 0,
                                  parent_id=parent.id if parent else None,
                                  taxonomy_id=taxonomy.id,
                                  taxonomy_code=taxonomy.code)
            session.add(parent)
            after_taxonomy_term_created.send(parent, taxonomy=taxonomy, term=parent)
            return parent

    def filter_term(self, ti: TermIdentification,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                    session=None):
        ti = _coerce_ti(ti)
        session = session or self.session
        return ti.term_query(session).filter(status_cond)

    def update_term(self, ti: TermIdentification,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                    extra_data=None, patch=False, session=None):
        ti = _coerce_ti(ti)
        session = session or self.session
        with session.begin_nested():
            term = self.filter_term(ti, status_cond=status_cond, session=session).one()

            before_taxonomy_term_updated.send(term, term=term, taxonomy=term.taxonomy,
                                              extra_data=extra_data)
            if patch:
                # apply json patch
                term.extra_data = jsonpatch.apply_patch(
                    term.extra_data or {}, extra_data, in_place=True)
            else:
                term.extra_data = extra_data
            flag_modified(term, "extra_data")
            session.add(term)
            after_taxonomy_term_updated.send(term, term=term, taxonomy=term.taxonomy)
            return term

    def descendants(self, ti: TermIdentification, levels=None,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                    order=True, session=None):
        ret = self._descendants(ti, levels=levels, return_term=False,
                                status_cond=status_cond, session=session)
        if order:
            return ret.order_by(TaxonomyTerm.slug)
        return ret  # pragma: no cover

    def descendants_or_self(self, ti: TermIdentification, levels=None,
                            status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                            order=True, session=None):
        ret = self._descendants(ti, levels=levels, return_term=True,
                                status_cond=status_cond, session=session)
        if order:
            return ret.order_by(TaxonomyTerm.slug)
        return ret

    def _descendants(self, ti: TermIdentification, levels=None,
                     return_term=True, status_cond=None, session=None):
        ti = _coerce_ti(ti)
        session = session or self.session
        query = ti.descendant_query(session)
        if levels is not None:
            query = query.filter(TaxonomyTerm.level <= ti.level + levels)
        if not return_term:
            query = query.filter(TaxonomyTerm.level > ti.level)
        if status_cond is not None:
            query = query.filter(status_cond)
        return query

    def ancestors(self, ti: TermIdentification, status_cond=TaxonomyTerm.status == TermStatusEnum.alive, session=None):
        return self._ancestors(ti, return_term=False, status_cond=status_cond, session=session)

    def ancestors_or_self(self, ti: TermIdentification,
                          status_cond=TaxonomyTerm.status == TermStatusEnum.alive, session=None):
        return self._ancestors(ti, return_term=True, status_cond=status_cond, session=session)

    def _ancestors(self, ti: TermIdentification, return_term=True, status_cond=None, session=session):
        ti = _coerce_ti(ti)
        session = session or self.session
        query = ti.ancestor_query(session)
        if status_cond is not None:
            query = query.filter(status_cond)
        if not return_term:
            query = query.filter(TaxonomyTerm.level < ti.level)
        return query

    def delete_term(self, ti: TermIdentification, remove_after_delete=True, session=None):
        ti = _coerce_ti(ti)
        session = session or self.session
        with session.begin_nested():
            terms = self.descendants_or_self(ti,
                                             order=False, status_cond=sqlalchemy.sql.true())
            locked_terms = terms.with_for_update().values('id')  # get ids to actually lock the terms
            if terms.filter(TaxonomyTerm.busy_count > 0).count():
                raise TaxonomyError('Can not delete busy terms')

            term = terms.first()
            self.mark_busy(terms, TermStatusEnum.delete_pending if remove_after_delete else TermStatusEnum.deleted)
            # can call mark_busy if the deletion should be postponed
            taxonomy = term.taxonomy
            before_taxonomy_term_deleted.send(term, taxonomy=taxonomy, term=term, terms=terms)
            self.unmark_busy(terms)
            after_taxonomy_term_deleted.send(term, taxonomy=taxonomy, term=term)

    def mark_busy(self, terms, status=None, session=None):
        session = session or self.session
        with session.begin_nested():
            if status:
                terms.update({
                    TaxonomyTerm.busy_count: TaxonomyTerm.busy_count + 1,
                    TaxonomyTerm.status: status
                }, synchronize_session=False)
            else:
                terms.update({TaxonomyTerm.busy_count: TaxonomyTerm.busy_count + 1},
                             synchronize_session=False)
        session.expire_all()

    def unmark_busy(self, terms, session=None):
        session = session or self.session
        with session.begin_nested():
            terms.update({TaxonomyTerm.busy_count: TaxonomyTerm.busy_count - 1},
                         synchronize_session=False)
            # delete those that are marked as 'delete_pending'
            terms.filter(
                TaxonomyTerm.busy_count <= 0,
                TaxonomyTerm.status == TermStatusEnum.delete_pending).delete(
                synchronize_session=False
            )
        session.expire_all()

    def rename_term(self, ti: TermIdentification, new_slug=None,
                    remove_after_delete=True, session=None):
        ti = _coerce_ti(ti)
        elements = self.descendants_or_self(ti, status_cond=sqlalchemy.sql.true(), order=False)
        return self._rename_or_move(elements, parent_query=None, slug=new_slug,
                                    remove_after_delete=remove_after_delete, session=session)

    def move_term(self, ti: TermIdentification, new_parent=None,
                  remove_after_delete=True, session=None):
        session = session or self.session
        ti = _coerce_ti(ti)
        if new_parent:
            new_parent = _coerce_ti(new_parent)
            if ti.contains(new_parent):
                raise TaxonomyError('Can not move inside self')
            new_parent = self.filter_term(new_parent, session=session)
        elements = self.descendants_or_self(ti, status_cond=sqlalchemy.sql.true(), order=False, session=session)
        return self._rename_or_move(elements, parent_query=new_parent,
                                    remove_after_delete=remove_after_delete, session=session)

    def extract_data(self, representation, obj):
        data = obj.extra_data or {}
        if INCLUDE_DATA not in representation:
            return {}
        if representation.selectors is None:
            # include everything
            return data

        # include selected data
        ret = {}
        for sel in representation.selectors:
            if not representation.startswith('/'):
                sel = '/' + sel
            ptr = jsonpointer.JsonPointer(sel)
            selected_data = ptr.resolve(data)
            if selected_data:
                ret[ptr.path[-1]] = selected_data
        return ret

    def _rename_or_move(self, elements, parent_query=None, slug=None,
                        remove_after_delete=False, session=None):
        session = session or self.session
        with session.begin_nested():
            if slug and '/' in slug:
                raise TaxonomyError('/ is not allowed when renaming term')
            root = elements.order_by(TaxonomyTerm.slug).first()

            if slug:
                if not parent_query and root.parent_id:
                    parent_query = session.query(TaxonomyTerm).filter(TaxonomyTerm.id == root.parent_id)

            parent = None
            if parent_query:
                parent = parent_query.with_for_update().one()

            if slug:
                if parent:
                    target_path = parent.slug + '/' + slug
                else:
                    target_path = slug
            elif parent:
                target_path = parent.slug + '/' + self._last_slug_element(root.slug)
            else:
                target_path = self._last_slug_element(root.slug)

            self.mark_busy(elements.with_for_update(),
                           status=(
                               TermStatusEnum.delete_pending
                               if remove_after_delete else TermStatusEnum.deleted
                           ))
            before_taxonomy_term_moved.send(root, target_path=target_path, terms=elements)
            target_root = self._copy(root, parent, target_path, session)
            self.unmark_busy(elements)
            after_taxonomy_term_moved.send(root, term=root, new_term=target_root)
            return root, target_root

    def _copy(self, term: TaxonomyTerm, parent, target_path, session):
        new_term = TaxonomyTerm(
            taxonomy_id=term.taxonomy_id,
            parent_id=parent.id if parent else None,
            slug=target_path,
            level=parent.level + 1 if parent else 0,
            extra_data=term.extra_data
        )
        session.add(new_term)
        session.flush()
        assert new_term.id > 0
        term.obsoleted_by_id = new_term.id
        session.add(term)
        for child in term.children:
            self._copy(child, new_term,
                       target_path + '/' + self._last_slug_element(child.slug),
                       session)
        return new_term

    @staticmethod
    def _slugify(parent_path, slug):
        slug = slugify(slug)
        if parent_path:
            return parent_path + '/' + slug
        return slug

    @staticmethod
    def _last_slug_element(slug):
        return slug.split('/')[-1]
