# -*- coding: utf-8 -*-
"""User models."""
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


class Taxonomy(SurrogatePK, db.Model, BaseNestedSets):
    """Taxonomy adjacency list model."""

    __tablename__ = "taxonomy"
    slug = db.Column(db.String(64), unique=True)
    title = db.Column(db.JSON)
    description = db.Column(db.String(256))

    def __repr__(self):
        """Represent taxonomy instance as a unique string."""
        return "<Taxonomy({slug})>".format(slug=self.slug)

    @classmethod
    def get_by_slug(cls, slug):
        """Get Taxonomy unique slug."""
        if isinstance(slug, str):
            return cls.query.filter(cls.slug == slug).first()
        return None
