# -*- coding: utf-8 -*-
"""User models."""
import logging
from enum import Enum

import sqlalchemy.dialects.postgresql
import wrapt
from blinker import Namespace
from flask import url_for
from invenio_db import db
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

logger = logging.getLogger('taxonomies')

taxonomy_signals = Namespace()

# signals emitted by REST methods
before_taxonomy_created = taxonomy_signals.signal('before-taxonomy-created')
after_taxonomy_created = taxonomy_signals.signal('after-taxonomy-created')

before_taxonomy_updated = taxonomy_signals.signal('before-taxonomy-updated')
after_taxonomy_updated = taxonomy_signals.signal('after-taxonomy-updated')

before_taxonomy_deleted = taxonomy_signals.signal('before-taxonomy-deleted')
after_taxonomy_deleted = taxonomy_signals.signal('after-taxonomy-deleted')

before_taxonomy_term_created = taxonomy_signals.signal('before-taxonomy-term-created')
after_taxonomy_term_created = taxonomy_signals.signal('after-taxonomy-term-created')

before_taxonomy_term_updated = taxonomy_signals.signal('before-taxonomy-term-updated')
after_taxonomy_term_updated = taxonomy_signals.signal('after-taxonomy-term-updated')

before_taxonomy_term_deleted = taxonomy_signals.signal('before-taxonomy-term-deleted')
after_taxonomy_term_deleted = taxonomy_signals.signal('after-taxonomy-term-deleted')

before_taxonomy_term_moved = taxonomy_signals.signal('before-taxonomy-term-moved')
after_taxonomy_term_moved = taxonomy_signals.signal('after-taxonomy-term-moved')

before_taxonomy_jsonresolve = taxonomy_signals.signal('before_taxonomy_json_resolve')
after_taxonomy_jsonresolve = taxonomy_signals.signal('after_taxonomy_json_resolve')


class MovePosition(Enum):
    INSIDE = 'inside'
    BEFORE = 'before'
    AFTER = 'after'


class TaxonomyError(Exception):
    pass


class TreeId(db.Model):
    __tablename__ = "taxonomy_tree_id"
    id = db.Column(db.Integer, primary_key=True)


class TaxonomyTerm(db.Model):
    """TaxonomyTerm adjacency list model."""
    __tablename__ = "taxonomy_term"
    __table_args__ = (
        db.UniqueConstraint('slug', 'parent_id', name='uq_taxonomy_term_slug_parent'),
        db.UniqueConstraint('slug', 'tree_id', name='uq_taxonomy_term_slug_tree'),
        #
        # can not use constraints here as db can not perform update
        # which would temporarily invalidate constraints
        #
        # db.UniqueConstraint('left', 'tree_id', name='uq_taxonomy_term_left_tree'),
        # db.UniqueConstraint('right', 'tree_id', name='uq_taxonomy_term_right_tree'),
        # db.UniqueConstraint('order', 'parent_id', name='uq_taxonomy_term_order_parent'),
    )

    id = db.Column(db.Integer, primary_key=True)
    slug = db.Column(db.String(64), unique=False, index=True)
    extra_data = db.Column(db.JSON().with_variant(
        sqlalchemy.dialects.postgresql.JSONB, 'postgresql'))

    tree_id = db.Column("tree_id", db.Integer, nullable=False)
    left = db.Column("left", db.Integer, nullable=False)
    right = db.Column("right", db.Integer, nullable=False)
    level = db.Column("level", db.Integer, nullable=False)
    order = db.Column("order", db.Integer, nullable=False)

    parent_id = db.Column(db.Integer, db.ForeignKey(__tablename__ + '.id'))
    parent = relationship("TaxonomyTerm", back_populates="children", remote_side=[id])
    children = relationship("TaxonomyTerm", back_populates="parent", order_by=order,
                            cascade="all, delete", lazy="dynamic")

    def __init__(self,
                 slug: str,
                 extra_data: dict = None,
                 parent=None,
                 tree_id=None,
                 left=None,
                 right=None,
                 level=None,
                 order=None):
        """Taxonomy Term constructor."""
        self.slug = slug
        self.extra_data = extra_data
        self.parent = parent
        if not tree_id:
            # can not use db generator as it is not supported in sqlite
            with db.session.begin_nested():
                t = TreeId()
                db.session.add(t)
            tree_id = t.id

        self.tree_id = tree_id
        self.left = left
        self.right = right
        self.level = level
        self.order = order

    def create_term(self, **kwargs):
        db.session.refresh(self)

        with db.session.begin_nested():
            # move all following nodes by 2 to make space for the new node
            t = TaxonomyTerm.__table__
            following_terms_cond = and_(
                TaxonomyTerm.left > self.right,
                TaxonomyTerm.tree_id == self.tree_id
            )
            db.session.execute(
                t.update().where(following_terms_cond).values(
                    left=TaxonomyTerm.left + 2,
                    right=TaxonomyTerm.right + 2)
            )

            # on path to parent move the right property by 2
            # as the hierarchy will contain the new node
            ancestors_cond = and_(
                TaxonomyTerm.left <= self.left,
                TaxonomyTerm.right >= self.right,
                TaxonomyTerm.tree_id == self.tree_id
            )
            db.session.execute(
                t.update().where(ancestors_cond).values(
                    right=TaxonomyTerm.right + 2)
            )

            # self is still not modified here, so can use its unchanged "right" property
            term = self.__class__(
                **kwargs, tree_id=self.tree_id, left=self.right,
                right=self.right + 1, level=self.level + 1,
                order=self.children.count(),
                parent=self
            )
            db.session.add(term)

        return term

    def update(self, extra_data: dict = None):
        """Update Taxonomy Term data."""
        self.extra_data = extra_data
        with db.session.begin_nested():
            db.session.add(self)

    def delete(self):
        # refetch it from db just to be sure that all props are up to date
        db.session.refresh(self)

        parent_id = self.parent_id
        order = self.order
        right = self.right
        left = self.left
        tree_id = self.tree_id

        if parent_id is None:
            # top-level object
            with db.session.begin_nested():
                db.session.delete(self)
        else:

            # get space occupied by the term
            occupied_space = right - left + 1

            with db.session.begin_nested():

                # delete current object and all its children
                with db.session.begin_nested():
                    db.session.delete(self)

                with db.session.begin_nested():
                    t = TaxonomyTerm.__table__
                    # update order on following siblings

                    following_siblings_cond = and_(
                        TaxonomyTerm.order > order,
                        TaxonomyTerm.parent_id == parent_id
                    )
                    db.session.execute(
                        t.update().where(following_siblings_cond).values(
                            order=TaxonomyTerm.order - 1)
                    )

                    # move all following nodes to the left by the occupied space
                    following_terms_cond = and_(
                        TaxonomyTerm.left > right,
                        TaxonomyTerm.tree_id == tree_id
                    )
                    db.session.execute(
                        t.update().where(following_terms_cond).values(
                            left=TaxonomyTerm.left - occupied_space,
                            right=TaxonomyTerm.right - occupied_space)
                    )

                    # on path to parent move the right property left by the occupied space
                    ancestors_cond = and_(
                        TaxonomyTerm.left < left,
                        TaxonomyTerm.right > right,
                        TaxonomyTerm.tree_id == tree_id
                    )
                    db.session.execute(
                        t.update().where(ancestors_cond).values(
                            right=TaxonomyTerm.right - occupied_space)
                    )

    def check(self, path=None):
        """
        Checks consistency of MPTT tree

        :param path:    internal, always pass None
        :raise ValueError:  when tree is corrupted
        """
        if not path:
            path = []
            db.session.refresh(self)

        path = path + [self.slug]

        children = list(self.children)
        for c in children:
            db.session.refresh(c)  # make sure cached data are not used here

        if not children:
            if self.left + 1 != self.right:
                raise ValueError(  # pragma: no cover
                    'Error in childless element {}: bad left {} or right{}'.format(
                        path, self.left, self.right))
        else:
            # check lefts and rights
            if self.left + 1 != children[0].left:
                raise ValueError(  # pragma: no cover
                    'First child "{}" of {} has bad left {}, expecting {}'.format(
                        children[0].slug, path, children[0].left, self.left + 1))
            if self.right - 1 != children[-1].right:
                raise ValueError(  # pragma: no cover
                    'Last child "{}" of {} has bad right {}, expecting {}'.format(
                        children[-1].slug, path, children[0].right, self.right - 1))
            # check lefts and rights between children
            for i in range(0, len(children) - 1):
                c1 = children[i]
                c2 = children[i + 1]
                if c1.right + 1 != c2.left:
                    raise ValueError(  # pragma: no cover
                        'Child with slug "{}" of element {} has bad left {}, expecting {}'.format(
                            c2.slug, path, c2.left, c1.right + 1))
            for ci, c in enumerate(children):
                if c.level != self.level + 1:
                    raise ValueError(  # pragma: no cover
                        'Child with slug "{}" of {} has bad level {}, expecting {}'.format(
                            c.slug, path, c.level, self.level + 1))
                if c.order != ci:
                    raise ValueError(  # pragma: no cover
                        'Child with slug "{}" of {} has bad order {}, expecting {}'.format(
                            c.slug, path, c.order, ci))

            for c in children:
                c.check(path)

    def move(self, target_node, position: MovePosition):
        db.session.refresh(self)
        db.session.refresh(target_node)

        if self == target_node:
            raise TaxonomyError('Can not move term inside, before or after the same term')

        if (
                self.tree_id == target_node.tree_id and
                self.left < target_node.left and
                self.right > target_node.right
        ):
            raise TaxonomyError('Can not move a term inside its own descendants')

        with db.session.begin_nested():
            if self.tree_id != target_node.tree_id:
                return self._move_between_trees(target_node, position)

            return self._move_within_tree(target_node, position)

    def _move_within_tree(self, target_node, position):
        (
            target_parent_id, target_parent_left,
            target_parent_right, target_left,
            target_level, target_order
        ) = target_node._get_insertion_position(position)

        self_right = self.right
        self_left = self.left
        self_level = self.level
        self_parent_id = self.parent_id
        self_order = self.order
        occupied_space = self_right - self_left + 1
        tree_id = self.tree_id

        t = TaxonomyTerm.__table__

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug(f'target parent id {target_parent_id}, '
                          f'target parent left {target_parent_left}, '
                          f'target parent right {target_parent_right}\n'
                          f'target_left {target_left}, target_level {target_level}, '
                          f'target_order {target_order}, occupied space {occupied_space}\n'
                          f'self left {self_left}, '
                          f'self right {self_right}\n'
                          )

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 0: before move right   \n%s", self.taxonomy.dump(True))

        if self_left == target_left:
            # nothing to do, already there
            return

        # just a sanity check that can not move the term inside itself
        assert not self_left <= target_left < self_right

        with db.session.begin_nested():
            # make space for the tree by moving subsequent terms to the right
            target_following_cond = and_(
                TaxonomyTerm.left >= target_left,
                TaxonomyTerm.tree_id == tree_id
            )
            db.session.execute(
                t.update().where(target_following_cond).values(
                    left=TaxonomyTerm.left + occupied_space,
                    right=TaxonomyTerm.right + occupied_space)
            )

        with db.session.begin_nested():
            # update ancestors' right
            if target_parent_left < target_left:
                # target parent's right has not been moved
                # in the previous condition, so add it as well
                target_ancestors_cond = and_(
                    TaxonomyTerm.left <= target_parent_left,
                    TaxonomyTerm.right >= target_parent_right,
                    TaxonomyTerm.tree_id == tree_id
                )
                db.session.execute(
                    t.update().where(target_ancestors_cond).values(
                        right=TaxonomyTerm.right + occupied_space))
            else:  # pragma: no cover
                raise RuntimeError('Should not get here as we are moving into parent, not onto it')

        if self_left >= target_left:
            # if self was in subsequent terms, fix its left and right
            self_left += occupied_space
            self_right += occupied_space

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 1: after move right    \n%s", self.taxonomy.dump(True))

        with db.session.begin_nested():
            # update order on the future siblings that will be after the moved element
            future_siblings_cond = and_(TaxonomyTerm.order >= target_order,
                                        TaxonomyTerm.parent_id == target_parent_id)
            db.session.execute(
                t.update().where(future_siblings_cond).values(
                    order=TaxonomyTerm.order + 1)
            )

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 2: after order future siblings\n%s", self.taxonomy.dump(True))

        with db.session.begin_nested():
            # move the descendants of the moved term to the new location, fixing left, right, level
            term_descendants_cond = and_(
                TaxonomyTerm.left > self_left,
                TaxonomyTerm.right < self_right,
                TaxonomyTerm.tree_id == tree_id)
            db.session.execute(
                t.update().where(term_descendants_cond).values(
                    left=TaxonomyTerm.left + target_left - self_left,
                    right=TaxonomyTerm.right + target_left - self_left,
                    level=TaxonomyTerm.level + target_level - self_level)
            )

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 3: after move children \n%s", self.taxonomy.dump(True))

        with db.session.begin_nested():
            # move the self only to the new location, fixing left, right, level, parent and order
            db.session.execute(
                t.update().where(TaxonomyTerm.id == self.id).values(
                    left=TaxonomyTerm.left + target_left - self_left,
                    right=TaxonomyTerm.right + target_left - self_left,
                    level=target_level,
                    parent_id=target_parent_id,
                    order=target_order)
            )

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 4: after move term     \n%s", self.taxonomy.dump(True))

        with db.session.begin_nested():
            # remove the space left by the moved element
            orig_following_cond = and_(TaxonomyTerm.left >= self_left,
                                       TaxonomyTerm.tree_id == tree_id)
            db.session.execute(
                t.update().where(orig_following_cond).values(
                    left=TaxonomyTerm.left - occupied_space,
                    right=TaxonomyTerm.right - occupied_space)
            )

        with db.session.begin_nested():
            # and parents ...
            orig_parents_cond = and_(
                TaxonomyTerm.left < self_left,
                TaxonomyTerm.right > self_right,
                TaxonomyTerm.tree_id == tree_id)
            db.session.execute(
                t.update().where(orig_parents_cond).values(
                    right=TaxonomyTerm.right - occupied_space)
            )

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 5: after removing space\n%s", self.taxonomy.dump(True))

        with db.session.begin_nested():
            # fix order on siblings following the previously moved term
            orig_siblings_cond = and_(TaxonomyTerm.order > self_order,
                                      TaxonomyTerm.parent_id == self_parent_id)
            db.session.execute(
                t.update().where(orig_siblings_cond).values(order=TaxonomyTerm.order - 1))

        if logger.isEnabledFor(logging.DEBUG):  # pragma: no cover
            logging.debug("Phase 6: after fixing order, done\n%s", self.taxonomy.dump(True))

    def _get_insertion_position(self, position: MovePosition):
        db.session.refresh(self)
        if position == MovePosition.INSIDE:
            return self.id, self.left, self.right, self.right, \
                   self.level + 1, self.children.count()
        parent = self.parent
        db.session.refresh(parent)
        if position == MovePosition.AFTER:
            return parent.id, parent.left, parent.right, self.right + 1, \
                   self.level, self.order + 1
        if position == MovePosition.BEFORE:
            return parent.id, parent.left, parent.right, self.left, \
                   self.level, self.order
        raise Exception('Unhandled MovePosition %s' % position)  # pragma: no cover

    @property
    def taxonomy(self):
        term = TaxonomyTerm.query.filter_by(tree_id=self.tree_id, level=1).one()
        return Taxonomy(term)

    def lock(self):
        # lock the whole tree
        TreeId.query.filter_by(id=self.tree_id).with_for_update()

    @property
    def tree_path(self) -> [str, None]:
        """Get path in a taxonomy tree."""
        path = [
            x[0] for x in self.ancestors_or_self.values(TaxonomyTerm.slug)
        ]
        if not path:
            return None
        return '/' + '/'.join(path)

    def __repr__(self):
        """Represent taxonomy term instance as a unique string."""
        return "({slug}:{path})" \
            .format(slug=self.slug, path=self.id)

    @property
    def descendants(self):
        # need to have up to date left and right
        db.session.refresh(self)

        return TaxonomyTerm.query.filter(
            TaxonomyTerm.tree_id == self.tree_id,
            TaxonomyTerm.left > self.left,
            TaxonomyTerm.right < self.right).order_by('left')

    @property
    def descendants_or_self(self):
        # need to have up to date left and right
        db.session.refresh(self)

        return TaxonomyTerm.query.filter(
            TaxonomyTerm.tree_id == self.tree_id,
            TaxonomyTerm.left >= self.left,
            TaxonomyTerm.right <= self.right).order_by('left')

    @property
    def ancestors(self):
        ancestor_cond = and_(TaxonomyTerm.tree_id == self.tree_id,
                             TaxonomyTerm.left > 1,  # do not take root
                             TaxonomyTerm.left < self.left,
                             TaxonomyTerm.right > self.right)
        return TaxonomyTerm.query.filter(ancestor_cond).order_by(TaxonomyTerm.left)

    @property
    def ancestors_or_self(self):
        ancestor_cond = and_(TaxonomyTerm.tree_id == self.tree_id,
                             TaxonomyTerm.left > 1,  # do not take root
                             TaxonomyTerm.left <= self.left,
                             TaxonomyTerm.right >= self.right)
        return TaxonomyTerm.query.filter(ancestor_cond).order_by(TaxonomyTerm.left)

    @property
    def link_self(self):
        taxonomy_code, term_path = self.tree_path.lstrip('/').split('/', 1)
        return url_for(
            "taxonomies.taxonomy_get_term",
            taxonomy_code=taxonomy_code,
            term_path=term_path,
            _external=True,
        )

    @property
    def link_tree(self, parent_path):
        taxonomy_code, term_path = self.tree_path.lstrip('/').split('/', 1)

        return url_for(
            "taxonomies.taxonomy_get_term",
            taxonomy_code=taxonomy_code,
            term_path=term_path,
            drilldown=True,
            _external=True,
        )


class Taxonomy(wrapt.ObjectProxy):

    def __init__(self, node):
        super().__init__(node)

    @classmethod
    def create_taxonomy(cls, code, extra_data: dict = None):
        if TaxonomyTerm.query.filter_by(parent=None, slug=code).count() > 0:
            raise IntegrityError('Error creating taxonomy - duplicated code', '', [], None)
        with db.session.begin_nested():
            ret = cls(TaxonomyTerm(slug=code, extra_data=extra_data, parent=None,
                                   left=1, right=2, level=1, order=0))
            db.session.add(ret)
            return ret

    @property
    def code(self):
        return self.slug

    @property
    def terms(self):
        return self.descendants

    @property
    def roots(self):
        return self.children

    @property
    def link_self(self):
        return url_for(
            "taxonomies.taxonomy_get_roots",
            taxonomy_code=self.code,
            _external=True,
        )

    @property
    def link_tree(self):
        return url_for(
            "taxonomies.taxonomy_get_roots",
            taxonomy_code=self.code,
            drilldown=True,
            _external=True,
        )

    @classmethod
    def taxonomies(cls, _filter=None):
        terms = TaxonomyTerm.query.filter_by(parent=None)
        if _filter:
            terms = _filter(terms)
        for term in terms:
            yield cls(term)

    @classmethod
    def get(cls, code, required=False):
        if required:
            tax = TaxonomyTerm.query.filter_by(parent=None, slug=code).one()
        else:
            tax = TaxonomyTerm.query.filter_by(parent=None, slug=code).one_or_none()
            if not tax:
                return None
        return cls(tax)

    def dump(self, as_string=False):
        """Only for debug purposes !!!"""
        ret = []
        for c in TaxonomyTerm.query.filter(TaxonomyTerm.tree_id == self.tree_id).order_by('left'):
            db.session.refresh(c)
            ret.append((c.slug, c.level, c.left, c.right, c.order))
        if not as_string:
            return ret
        return '\n'.join(['     %s%s' % ('  ' * x[1], str(x)) for x in ret])

    @classmethod
    def find_taxonomy_and_term(cls, path):
        parts = _parse_path(path)
        taxonomy = Taxonomy.get(parts[0])
        if len(parts) > 1 and taxonomy:
            term = taxonomy.get_term(parts[-1], required=True)
        else:
            term = taxonomy
        if not taxonomy:
            raise NoResultFound('No result for path %s' % path)
        return taxonomy, term

    def find_term(self, path):

        parts = _parse_path(path)
        if parts:
            slug = parts[-1]
            return self.get_term(slug)

        return self

    def get_term(self, slug, required=False):
        found = self.descendants_or_self.filter_by(slug=slug)
        if required:
            return found.one()
        return found.one_or_none()


def _parse_path(path):
    path = (path or '').strip('/')
    return [x for x in path.split('/') if x]


__all__ = ('TaxonomyTerm', 'Taxonomy')
