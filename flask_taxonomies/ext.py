# -*- coding: utf-8 -*-
"""Extension module for Flask Taxonomies."""
import flask_taxonomies.db


class FlaskTaxonomies(object):
    """App for Flask Taxonomies."""

    def __init__(self, app=None, db=None):
        """Extension initialization."""
        if app:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        """Flask application initialization."""
        if db:
            flask_taxonomies.db.db = db
