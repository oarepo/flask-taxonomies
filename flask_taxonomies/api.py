import sqlalchemy
from flask_sqlalchemy import get_state
from slugify import slugify
from sqlalchemy.util import deprecated
from sqlalchemy_utils import Ltree

from .models import Taxonomy, TaxonomyTerm, TermStatusEnum, TaxonomyError
from .signals import before_taxonomy_created, after_taxonomy_created, before_taxonomy_updated, \
    after_taxonomy_updated, before_taxonomy_deleted, after_taxonomy_deleted, before_taxonomy_term_created, \
    after_taxonomy_term_created, before_taxonomy_term_deleted, after_taxonomy_term_deleted


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

    def update_taxonomy(self, taxonomy: Taxonomy, extra_data, session=None) -> Taxonomy:
        """Updates a taxonomy.
        :param taxonomy: taxonomy instance to be updated
        :param extra_data: new taxonomy metadata
        :param session: use a different db session
        :return Taxonomy: updated taxonomy
        """
        session = session or self.session
        with session.begin_nested:
            before_taxonomy_updated.send(taxonomy, taxonomy=taxonomy, extra_data=extra_data)
            taxonomy.extra_data = extra_data
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
            print('mark busy', list(terms))
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
            print('unmark busy', list(terms))
            terms.update({TaxonomyTerm.busy_count: TaxonomyTerm.busy_count - 1},
                         synchronize_session=False)
            # delete those that are marked as 'delete_pending'
            terms.filter(
                TaxonomyTerm.busy_count <= 0,
                TaxonomyTerm.status == TermStatusEnum.delete_pending).delete(
                synchronize_session=False
            )
        session.expire_all()

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
