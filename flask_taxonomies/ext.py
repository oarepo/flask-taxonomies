# -*- coding: utf-8 -*-
"""Extension module for Flask Taxonomies."""
from werkzeug.utils import cached_property

from flask_taxonomies import config
from flask_taxonomies.api import TaxonomyAPI
from flask_taxonomies.models import (
    after_taxonomy_term_moved,
    after_taxonomy_term_updated,
    after_taxonomy_updated,
    before_taxonomy_deleted,
    before_taxonomy_term_deleted,
)
from flask_taxonomies.signals import (
    check_references_before_delete,
    reindex_referencing_records,
)
from flask_taxonomies.utils import load_or_import_from_config


class _FlaskTaxonomiesState(object):
    """Flask Taxonomies state object."""

    def __init__(self, app):
        """Initialize state."""
        self.app = app
        self.api = TaxonomyAPI()

    def taxonomy_list(self):
        return self.api.taxonomy_list()

    def create_taxonomy(self, code, extra_data=None):
        return self.api.create_taxonomy(code, extra_data)

    def update_taxonomy(self, taxonomy, extra_data):
        return self.api.update_taxonomy(taxonomy, extra_data)

    def delete_taxonomy(self, taxonomy):
        self.api.delete_taxonomy(taxonomy)

    def move_term(self, taxonomy, term_path='', target_path=None, destination_order=''):
        return self.api.move_term(taxonomy, term_path, target_path, destination_order)

    def create_term(self, taxonomy, term_path='', slug=None, extra_data=None):
        return self.api.create_term(taxonomy, term_path, slug, extra_data)

    def term_links(self, taxonomy_code: str, path: str=None, parent_path: str=None):
        return self.api.term_links(taxonomy_code, path, parent_path)

    def update_term(self, taxonomy, term, changes):
        return self.api.update_term(taxonomy, term, changes)

    def delete_term(self, taxonomy, term):
        self.api.delete_term(taxonomy, term)

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

        # Connect signals
        after_taxonomy_updated.connect(reindex_referencing_records)
        after_taxonomy_term_moved.connect(reindex_referencing_records)
        after_taxonomy_term_updated.connect(reindex_referencing_records)

        app.extensions['flask-taxonomies'] = _FlaskTaxonomiesState(app)

    def init_config(self, app):
        """Initialize configuration."""
        for k in dir(config):
            if k.startswith('FLASK_TAXONOMIES_'):
                app.config.setdefault(k,
                                      getattr(config, k))  # pragma: no cover
