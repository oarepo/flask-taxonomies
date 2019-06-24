# -*- coding: utf-8 -*-
"""User models."""
from sqlalchemy import asc
from sqlalchemy.orm import relationship
from sqlalchemy_mptt import BaseNestedSets

from flask_taxonomies.compat import basestring
from flask_taxonomies.extensions import db


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
                        isinstance(record_id, basestring) and record_id.isdigit(),
                        isinstance(record_id, (int, float)),
                )
        ):
            return cls.query.get(int(record_id))
        return None


class Taxonomy(SurrogatePK, db.Model):
    __tablename__ = 'taxonomy'
    code = db.Column(db.String(64), unique=True)
    extra_data = db.Column(db.JSON)
    terms = relationship('TaxonomyTerm', cascade='all,delete', back_populates='taxonomy')

    def __init__(self, code: str):
        """Taxonomy constructor."""
        self.code = code

    def update(self, extra_data: dict = None):
        self.extra_data = extra_data
        db.session.add(self)
        db.session.commit()

    def __repr__(self):
        """Represent taxonomy instance as a unique string."""
        return "<Taxonomy({code})>".format(code=self.code)


class TaxonomyTerm(SurrogatePK, db.Model, BaseNestedSets):
    """TaxonomyTerm adjacency list model."""

    __tablename__ = 'taxonomy_term'
    slug = db.Column(db.String(64), unique=False)
    title = db.Column(db.JSON)
    extra_data = db.Column(db.JSON)
    taxonomy_id = db.Column(db.Integer, db.ForeignKey('taxonomy.id'))
    taxonomy = relationship('Taxonomy', back_populates='terms')

    def __repr__(self):
        """Represent taxonomy term instance as a unique string."""
        return "<TaxonomyTerm({slug}:{path})>".format(slug=self.slug, path=self.id)

    def __init__(self, slug: str, title: dict, taxonomy: Taxonomy, extra_data: dict = None):
        """TaxonomyTerm constructor."""
        self.slug = slug
        self.title = title
        self.taxonomy = taxonomy
        self.extra_data = extra_data

    def update(self, title: dict = None, extra_data: dict = None):
        self.title = title
        self.extra_data = extra_data
        db.session.add(self)
        db.session.commit()

    @property
    def tree_path(self) -> str:
        return "/{code}/{path}".format(code=self.taxonomy.code,
                                       path='/'.join([t.slug for t in self.path_to_root(order=asc).all()]))
