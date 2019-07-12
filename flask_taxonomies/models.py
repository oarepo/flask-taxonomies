# -*- coding: utf-8 -*-
"""User models."""
from invenio_db import db
from sqlalchemy import asc
from sqlalchemy.orm import relationship
from sqlalchemy_mptt import BaseNestedSets, mptt_sessionmaker


# From Mike Bayer's "Building the app" talk
# https://speakerdeck.com/zzzeek/building-the-app
class SurrogatePK(object):
    """A mixin that adds a surrogate integer 'primary key' column named ``id`` to any declarative-mapped class."""

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
    terms = relationship(
        "TaxonomyTerm", cascade="all,delete", back_populates="taxonomy"
    )

    def __init__(self, code: str, extra_data: dict = None):
        """Taxonomy constructor."""
        self.code = code
        self.extra_data = extra_data

    def update(self, extra_data: dict = None):
        """Update taxonomy extra_data."""
        self.extra_data = extra_data

        session = mptt_sessionmaker(db.session)
        session.add(self)
        session.commit()

    def __repr__(self):
        """Represent taxonomy instance as a unique string."""
        return "<Taxonomy({code})>".format(code=self.code)


class TaxonomyTerm(SurrogatePK, db.Model, BaseNestedSets):
    """TaxonomyTerm adjacency list model."""

    __tablename__ = "taxonomy_term"
    slug = db.Column(db.String(64), unique=False)
    title = db.Column(db.JSON)
    extra_data = db.Column(db.JSON)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey("taxonomy.id"))
    taxonomy = relationship("Taxonomy", back_populates="terms")

    def __repr__(self):
        """Represent taxonomy term instance as a unique string."""
        return "<TaxonomyTerm({slug}:{path})>".format(slug=self.slug, path=self.id)

    def __init__(
            self, slug: str, title: dict, taxonomy: Taxonomy, extra_data: dict = None
    ):
        """Taxonomy Term constructor."""
        self.slug = slug
        self.title = title
        self.taxonomy = taxonomy
        self.extra_data = extra_data

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
        return "/{code}/{path}".format(
            code=self.taxonomy.code,
            path="/".join([t.slug for t in self.path_to_root(order=asc).all()]),
        )
