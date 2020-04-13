import jsonpatch
import sqlalchemy
from flask_sqlalchemy import get_state
from slugify import slugify
from sqlalchemy.orm.attributes import flag_modified
from sqlalchemy.util import deprecated
from sqlalchemy_utils import Ltree

from .models import Taxonomy, TaxonomyTerm, TermStatusEnum, TaxonomyError
from .signals import before_taxonomy_created, after_taxonomy_created, before_taxonomy_updated, \
    after_taxonomy_updated, before_taxonomy_deleted, after_taxonomy_deleted, before_taxonomy_term_created, \
    after_taxonomy_term_created, before_taxonomy_term_deleted, after_taxonomy_term_deleted, \
    before_taxonomy_term_updated, after_taxonomy_term_updated, before_taxonomy_term_moved, after_taxonomy_term_moved


class Api:
    def __init__(self, app=None):
        self.app = app

    @property
    def session(self):
        db = get_state(self.app).db
        return db.session

    def list_taxonomies(self):
        """Return a list of all available taxonomies."""
        return self.session.query(Taxonomy)

    @deprecated(version='7.0.0')
    def taxonomy_list(self):
        return self.list_taxonomies()  # pragma: no cover

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

    def create_term(self, taxonomy: [Taxonomy, str] = None,
                    parent_path=None, parent: TaxonomyTerm = None,
                    slug: str = None, extra_data=None,
                    session=None):
        """Creates a taxonomy term.
        :param taxonomy: taxonomy in which to create a term, if None, term or term_path must be set
        :param parent_path: path on which to create a term; if taxonomy is None, first part is taxonomy code
        :param parent: create as a direct child of this term
        :param slug: term slug
        :param extra_data: term metadata]
        :raise AttributeError
        :raise IntegrityError
        :return TaxonomyTerm
        """
        session = session or self.session
        with session.begin_nested():
            if parent:
                if parent.status != TermStatusEnum.alive:
                    raise TaxonomyError('Can not create term inside inactive parent')
                taxonomy_id, parent_id, level, parent_path = parent.taxonomy_id, parent.id, parent.level, parent.slug
            else:
                taxonomy_id, parent_id, level, parent_path = self._find_term_id(session, taxonomy, parent_path)

            slug = self._slugify(parent_path, slug)

            before_taxonomy_term_created.send(taxonomy, slug=slug, extra_data=extra_data)
            # check if the slug exists and if so, create a new slug (append -1, -2, ... until ok)
            parent = TaxonomyTerm(slug=self._database_slug(session, slug),
                                  extra_data=extra_data, level=level + 1,
                                  parent_id=parent_id, taxonomy_id=taxonomy_id)
            session.add(parent)
            after_taxonomy_term_created.send(parent, taxonomy=taxonomy, term=parent)
            return parent

    def filter_term(self, taxonomy=None, parent=None, slug=None,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive):

        if parent and isinstance(parent, TaxonomyTerm):
            if slug:
                return self.session.query(TaxonomyTerm).filter(
                    TaxonomyTerm.taxonomy_id == parent.taxonomy_id,
                    TaxonomyTerm.slug == parent.slug + '/' + slug,
                    status_cond)
            else:
                # just return the parent as slug is not set
                return self.session.query(TaxonomyTerm).filter(
                    TaxonomyTerm.taxonomy_id == parent.taxonomy_id,
                    TaxonomyTerm.slug == parent.slug,
                    status_cond
                )

        taxonomy, parent = self._get_taxonomy_and_slug(taxonomy, parent, slug)

        if not parent:
            raise TaxonomyError('Please specify taxonomy term slug')

        # it is slug from taxonomy
        if isinstance(taxonomy, str):
            return self.session.query(TaxonomyTerm).join(Taxonomy).filter(
                Taxonomy.code == taxonomy,
                TaxonomyTerm.slug == parent,
                status_cond
            )
        else:
            return self.session.query(TaxonomyTerm).filter(
                TaxonomyTerm.taxonomy_id == taxonomy,
                TaxonomyTerm.slug == parent,
                status_cond
            )

    def update_term(self, taxonomy=None, parent=None, slug=None,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                    extra_data=None, patch=False, session=None):
        session = session or self.session
        with session.begin_nested():
            if isinstance(parent, TaxonomyTerm) and not slug:
                term = parent
            else:
                term = self.filter_term(taxonomy=taxonomy, parent=parent, slug=slug,
                                        status_cond=status_cond).one()

            before_taxonomy_term_updated.send(term, term=term, taxonomy=taxonomy,
                                              extra_data=extra_data)
            if patch:
                # apply json patch
                term.extra_data = jsonpatch.apply_patch(
                    term.extra_data or {}, extra_data, in_place=True)
            else:
                term.extra_data = extra_data
            flag_modified(term, "extra_data")
            session.add(term)
            after_taxonomy_term_updated.send(term, term=term, taxonomy=taxonomy)
            return term

    def descendants(self, taxonomy=None, parent=None, slug=None, levels=None,
                    status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                    order=True):
        ret = self._descendants(taxonomy=taxonomy, parent=parent, slug=slug, levels=levels,
                                return_term=False, status_cond=status_cond)
        if order:
            return ret.order_by(TaxonomyTerm.slug)
        return ret  # pragma: no cover

    def descendants_or_self(self, taxonomy=None, parent=None, slug=None, levels=None, removed=False,
                            status_cond=TaxonomyTerm.status == TermStatusEnum.alive,
                            order=True):
        ret = self._descendants(taxonomy=taxonomy, parent=parent, slug=slug, levels=levels,
                                return_term=True, status_cond=status_cond)
        if order:
            return ret.order_by(TaxonomyTerm.slug)
        return ret

    def _descendants(self, taxonomy=None, parent=None, slug=None, levels=None,
                     return_term=True, status_cond=None):

        if parent and isinstance(parent, TaxonomyTerm):
            levels_query = []
            if levels != None:
                levels_query = [
                    TaxonomyTerm.level <= levels + parent.level
                ]
            if not return_term:
                return_term_query = [
                    TaxonomyTerm.level > parent.level
                ]
            else:
                return_term_query = []
            if slug:
                return self.session.query(TaxonomyTerm).filter(
                    TaxonomyTerm.taxonomy_id == parent.taxonomy_id,
                    TaxonomyTerm.slug.descendant_of(parent.slug + '/' + slug),
                    status_cond,
                    *return_term_query,
                    *levels_query
                )
            else:
                return self.session.query(TaxonomyTerm).filter(
                    TaxonomyTerm.taxonomy_id == parent.taxonomy_id,
                    TaxonomyTerm.slug.descendant_of(parent.slug),
                    status_cond,
                    *return_term_query,
                    *levels_query
                )

        taxonomy, parent = self._get_taxonomy_and_slug(taxonomy, parent, slug)

        if not parent:
            # list the whole taxonomy
            levels_query = []
            if levels != None:
                levels_query = [
                    TaxonomyTerm.level < levels
                ]
            # list taxonomy
            if isinstance(taxonomy, str):
                return self.session.query(TaxonomyTerm).join(Taxonomy).filter(
                    Taxonomy.code == taxonomy,
                    status_cond,
                    *levels_query
                )
            else:
                # it is taxonomy id
                return self.session.query(TaxonomyTerm).filter(
                    TaxonomyTerm.taxonomy_id == taxonomy,
                    status_cond,
                    *levels_query
                )

        # list specific path inside the taxonomy
        levels_query = []
        if levels != None:
            levels_query = [
                TaxonomyTerm.level < levels + len(parent.split('/'))
            ]

        if not return_term:
            return_term_query = [
                TaxonomyTerm.level >= len(parent.split('/'))
            ]
        else:
            return_term_query = []

        # it is slug from taxonomy
        if isinstance(taxonomy, str):
            return self.session.query(TaxonomyTerm).join(Taxonomy).filter(
                Taxonomy.code == taxonomy,
                TaxonomyTerm.slug.descendant_of(parent),
                status_cond,
                *levels_query,
                *return_term_query
            )
        else:
            return self.session.query(TaxonomyTerm).filter(
                TaxonomyTerm.taxonomy_id == taxonomy,
                TaxonomyTerm.slug.descendant_of(parent),
                status_cond,
                *levels_query,
                *return_term_query
            )

    def ancestors(self, taxonomy=None, term=None, slug=None, status_cond=TaxonomyTerm.status == TermStatusEnum.alive):
        return self._ancestors(taxonomy=taxonomy, term=term, slug=slug, return_term=False, status_cond=status_cond)

    def ancestors_or_self(self, taxonomy=None, term=None, slug=None,
                          status_cond=TaxonomyTerm.status == TermStatusEnum.alive):
        return self._ancestors(taxonomy=taxonomy, term=term, slug=slug, return_term=True, status_cond=status_cond)

    def _ancestors(self, taxonomy=None, term=None, slug=None, return_term=True, status_cond=None):
        if term is not None and isinstance(term, TaxonomyTerm):
            if return_term:
                return_term_query = []
            else:
                return_term_query = [
                    TaxonomyTerm.slug != term.slug
                ]
            return self.session.query(TaxonomyTerm).filter(
                TaxonomyTerm.taxonomy_id == term.taxonomy_id,
                TaxonomyTerm.slug.ancestor_of(term.slug),
                status_cond,
                *return_term_query
            )
        if term:
            if slug:
                term = term + '/' + slug
        else:
            term = slug
            if not term:
                return self.session.query(TaxonomyTerm).filter(sqlalchemy.sql.false())

        if taxonomy is None:
            if '/' not in term:
                # only taxonomy given => return empty QS
                return self.session.query(TaxonomyTerm).filter(sqlalchemy.sql.false())
            taxonomy, term = term.split('/', maxsplit=1)

        if return_term:
            return_term_query = []
        else:
            return_term_query = [
                TaxonomyTerm.slug != term
            ]

        if isinstance(taxonomy, Taxonomy):
            return self.session.query(TaxonomyTerm).filter(
                TaxonomyTerm.taxonomy_id == taxonomy.id,
                TaxonomyTerm.slug.ancestor_of(term),
                status_cond,
                *return_term_query
            )
        else:
            return self.session.query(TaxonomyTerm).join(Taxonomy).filter(
                Taxonomy.code == taxonomy,
                TaxonomyTerm.slug.ancestor_of(term),
                status_cond,
                *return_term_query
            )

    def delete_term(self, taxonomy=None, term=None, slug=None, remove_after_delete=True):
        session = self.session
        with session.begin_nested():
            terms = self.descendants_or_self(taxonomy=taxonomy, parent=term, slug=slug,
                                             order=False, status_cond=sqlalchemy.sql.true())
            locked_terms = terms.with_for_update().values('id')  # get ids to actually lock the terms
            if terms.filter(TaxonomyTerm.busy_count > 0).count():
                raise TaxonomyError('Can not delete busy terms')

            term = terms.first()
            self.mark_busy(terms, TermStatusEnum.delete_pending if remove_after_delete else TermStatusEnum.deleted)
            # can call mark_busy if the deletion should be postponed
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

    def rename_term(self, taxonomy=None, parent=None, slug=None, new_slug=None,
                    remove_after_delete=True, session=None):
        elements = self.descendants_or_self(taxonomy=taxonomy, parent=parent, slug=slug,
                                            status_cond=sqlalchemy.sql.true(), order=False)
        return self._rename_or_move(elements, parent_query=None, slug=new_slug,
                                    remove_after_delete=remove_after_delete, session=session)

    def move_term(self, taxonomy=None, parent=None, slug=None, new_parent=None,
                  remove_after_delete=True, session=None):
        elements = self.descendants_or_self(taxonomy=taxonomy, parent=parent, slug=slug,
                                            status_cond=sqlalchemy.sql.true(),
                                            order=False)
        new_parent = self.filter_term(taxonomy=taxonomy, parent=new_parent)
        return self._rename_or_move(elements, parent_query=new_parent,
                                    remove_after_delete=remove_after_delete, session=session)

    def _rename_or_move(self, elements, parent_query=None, slug=None,
                        remove_after_delete=False, session=None):
        session = session or self.session
        with session.begin_nested():
            if slug and '/' in slug:
                raise TaxonomyError('/ is not allowed when renaming term')
            root = elements.order_by(TaxonomyTerm.slug).first()

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

    def _find_term_id(self, session, taxonomy, term_path):
        """

        :param session:
        :param taxonomy:
        :param term_path:
        :return: (taxonomy_id, term_id, term_level, term_slug)
        """
        if not taxonomy:
            if not term_path:
                raise TaxonomyError('At least a taxonomy or path starting with taxonomy must be provided')
            if '/' in term_path:
                taxonomy, term_path = term_path.split('/', maxsplit=1)
            else:
                taxonomy = term_path
                term_path = None

        if not term_path:
            if isinstance(taxonomy, Taxonomy):
                return taxonomy.id, None, -1, None
            return session.query(Taxonomy.id).filter(Taxonomy.code == taxonomy).one()[0], None, -1, None

        parent_database_slug = self._database_slug(session, term_path)
        if isinstance(taxonomy, Taxonomy):
            return (
                session.query(TaxonomyTerm.taxonomy_id, TaxonomyTerm.id, TaxonomyTerm.level, TaxonomyTerm.slug).
                    filter(
                    TaxonomyTerm.busy_count == 0,  # can not create term inside a busy term
                    TaxonomyTerm.obsoleted_by_id.is_(None),  # can not create term inside obsoleted term
                    TaxonomyTerm.slug == parent_database_slug,
                    TaxonomyTerm.taxonomy_id == taxonomy.id,
                    TaxonomyTerm.status == TermStatusEnum.alive).
                    one()
            )
        return (
            session.query(TaxonomyTerm.taxonomy_id, TaxonomyTerm.id, TaxonomyTerm.level, TaxonomyTerm.slug).join(
                Taxonomy).
                filter(
                TaxonomyTerm.busy_count == 0,  # can not create term inside a busy term
                TaxonomyTerm.obsoleted_by_id.is_(None),  # can not create term inside obsoleted term
                TaxonomyTerm.slug == parent_database_slug,
                Taxonomy.code == taxonomy,
                TaxonomyTerm.status == TermStatusEnum.alive).
                one()
        )

    @staticmethod
    def _database_slug(session, slug):
        if session.bind.dialect.name == 'postgresql':
            return Ltree(slug.replace('/', '.'))
        return slug

    @staticmethod
    def _slugify(parent_path, slug):
        slug = slugify(slug)
        if parent_path:
            return parent_path + '/' + slug
        return slug

    @staticmethod
    def _get_taxonomy_and_slug(taxonomy, parent, slug):
        if parent:
            if slug:
                parent = parent + '/' + slug
        else:
            parent = slug
        if taxonomy:
            if isinstance(taxonomy, Taxonomy):
                taxonomy = taxonomy.id
        else:
            if not parent:
                raise TaxonomyError('Taxonomy or full slug must be passed')
            if '/' in parent:
                taxonomy, parent = parent.split('/', maxsplit=1)
            else:
                taxonomy = parent
                parent = None
        return taxonomy, parent

    @staticmethod
    def _last_slug_element(slug):
        return slug.split('/')[-1]
