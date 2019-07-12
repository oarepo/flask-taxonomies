# -*- coding: utf-8 -*-
"""Extension module for Flask Taxonomies."""
from flask_taxonomies import config


class FlaskTaxonomies(object):
    """App Extension for Flask Taxonomies."""

    def __init__(self, app=None, db=None):
        """Extension initialization."""
        if app:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions['flask-taxonomies'] = self

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('TAXONOMIES_'):
                app.config.setdefault(k,
                                      getattr(config, k))  # pragma: no cover
