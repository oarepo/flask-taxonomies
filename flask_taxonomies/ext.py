# -*- coding: utf-8 -*-
"""Extension module for Flask Taxonomies."""
from werkzeug.utils import cached_property

from flask_taxonomies import config
from flask_taxonomies.permissions import permission_factory
from flask_taxonomies.utils import load_or_import_from_config


class _FlaskTaxonomiesState(object):
    """Flask Taxonomies state object."""

    def __init__(self, app):
        """Initialize state."""
        self.app = app

    @cached_property
    def permission_factory(self):
        """Load default permission factory for Flask Taxonomies."""
        return load_or_import_from_config(
            'FLASK_TAXONOMIES_PERMISSION_FACTORY', app=self.app
        )


class FlaskTaxonomies(object):
    """App Extension for Flask Taxonomies."""

    def __init__(self, app=None, db=None):
        """Extension initialization."""
        if app:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        """Flask application initialization."""
        self.init_config(app)
        app.extensions['flask-taxonomies'] = _FlaskTaxonomiesState(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('FLASK_TAXONOMIES_'):
                app.config.setdefault(k,
                                      getattr(config, k))  # pragma: no cover
