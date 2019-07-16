# -*- coding: utf-8 -*-
"""User models."""
from invenio_db import db
from sqlalchemy import asc, event
from sqlalchemy.orm import relationship
from sqlalchemy_mptt import BaseNestedSets, mptt_sessionmaker


# From Mike Bayer's "Building the app" talk
# https://speakerdeck.com/zzzeek/building-the-app
class SurrogatePK(object):
    """
    A mixin that adds a surrogate integer 'primary key' column.
    Named ``id`` to any declarative-mapped class.
    """

    __table_args__ = {"extend_existing": True}

    id = db.Column(db.Integer, primary_key=True)

    @classmethod
    def get_by_id(cls, record_id):
        """Get record by ID."""
        if any(
                (
                        isinstance(record_id, str) and record_id.isdigit(),
                        isinstance(record_id, (int, float)),
                )
        ):
            return cls.query.get(int(record_id))
        return None


class Taxonomy(SurrogatePK, db.Model):
    """Taxonomy model."""

    __tablename__ = "taxonomy"
    code = db.Column(db.String(64), unique=True)
    extra_data = db.Column(db.JSON)
    root_id = db.Column(db.Integer, db.ForeignKey("taxonomy_term.id"),
                        nullable=False)
    root = relationship("TaxonomyTerm", uselist=False,
                        back_populates="root_of")

    def __init__(self, code: str,
                 root: 'TaxonomyTerm',
                 extra_data: dict = None):
        """Taxonomy constructor."""
        self.code = code
        self.root = root
        self.extra_data = extra_data

    @classmethod
    def create(cls, session, code: str, extra_data: dict = None):
        root = TaxonomyTerm(slug=code, title={'en': 'Root'})
        self = cls(code=code, root=root, extra_data=extra_data)
        session.add(root)
        session.add(self)
        return self

    def update(self, extra_data: dict = None):
        """Update taxonomy extra_data."""
        self.extra_data = extra_data

        session = mptt_sessionmaker(db.session)
        session.add(self)
        session.commit()

    def append(self, term):
        term.parent = self.root

    @property
    def terms(self):
        return TaxonomyTerm.query.filter(
            TaxonomyTerm.tree_id == self.root.tree_id,
            TaxonomyTerm.left > self.root.left,
            TaxonomyTerm.right < self.root.right).order_by('lft')

    def __repr__(self):
        """Represent taxonomy instance as a unique string."""
        return "<Taxonomy({code})>".format(code=self.code)

    def dump(self):
        for term in self.terms:
            print(' ' * term.level, term.slug,
                  term.level, term.left, term.right)


class TaxonomyTerm(SurrogatePK, db.Model, BaseNestedSets):
    """TaxonomyTerm adjacency list model."""

    __tablename__ = "taxonomy_term"
    __table_args__ = (
        db.UniqueConstraint('slug', 'tree_id'),
    )
    slug = db.Column(db.String(64), unique=False)
    title = db.Column(db.JSON)
    extra_data = db.Column(db.JSON)
    root_of = relationship(
        "Taxonomy", back_populates="root", uselist=False
    )

    def __repr__(self):
        """Represent taxonomy term instance as a unique string."""
        return "<TaxonomyTerm({slug}:{path})>" \
            .format(slug=self.slug, path=self.id)

    def __init__(self,
                 slug: str,
                 title: dict,
                 extra_data: dict = None,
                 parent=None):
        """Taxonomy Term constructor."""
        self.slug = slug
        self.title = title
        self.extra_data = extra_data
        self.parent = parent

    def update(self, title: dict = None, extra_data: dict = None):
        """Update Taxonomy Term data."""
        self.title = title
        self.extra_data = extra_data

        session = mptt_sessionmaker(db.session)
        session.add(self)
        session.commit()

    @property
    def tree_path(self) -> str:
        """Get path in a taxonomy tree."""
        return "/{path}".format(
            path="/".join([t.slug for t in self.path_to_root(order=asc).all()]),  # noqa
        )

    def append(self, term):
        term.move_inside(self.id)


@event.listens_for(db.session, 'before_flush')
def remove_orphans(session, flush_context, *args, **kwargs):
    removed_roots = []
    for deleted_object in session.deleted:
        if isinstance(deleted_object, Taxonomy):
            removed_roots.append(deleted_object.root)
    for root in removed_roots:
        session.delete(root)


__all__ = ('TaxonomyTerm', 'Taxonomy')
