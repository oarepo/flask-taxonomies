# -*- coding: utf-8 -*-
"""Managers module for database models."""
from sqlalchemy import and_

from flask_taxonomies.extensions import db
from flask_taxonomies.models import TaxonomyTerm, Taxonomy


class TaxonomyManager(object):
    """Manager of Taxonomy tree db models."""

    def create(self, slug: str, title: dict, path: str, extra_data=None) -> TaxonomyTerm:
        """Create TaxonomyTerm on a given path."""
        taxonomy, parent_term = self.get_from_path(path)
        if not taxonomy:
            raise AttributeError('Invalid Taxonomy path.')

        for term in taxonomy.terms:
            if term.slug == slug:
                raise ValueError('Slug {slug} already exists within {tax}.'.format(slug=slug, tax=taxonomy))

        t = TaxonomyTerm(slug, title, taxonomy, extra_data)

        if parent_term:
            self.insert_term_under(t, parent_term)

        db.session.add(t)
        db.session.commit()

        return t

    def delete_tree(self, path: str):
        """Delete a subtree of Terms on a given path."""
        taxo, term = self.get_from_path(path)
        if not term:
            raise AttributeError('Invalid TaxonomyTerm path.')

        db.session.delete(term)
        db.session.commit()

    def delete_taxonomy(self, taxonomy: Taxonomy):
        """Delete whole Taxonomy including all its terms."""

    def get_from_path(self, path: str) -> (Taxonomy, TaxonomyTerm):
        """Get Taxonomy and Term on a given path in Taxonomy."""
        taxonomy = None
        term = None
        parts = list(filter(None, path.lstrip('/').split('/', 1)))

        if len(parts) >= 1:
            taxonomy = self.get_taxonomy(parts[0])

        if taxonomy and len(parts) == 2:
            slug = parts[1].rstrip('/').split('/')[-1]
            term = self.get_term(taxonomy=taxonomy, slug=slug)
            if not term:
                raise AttributeError('TaxonomyTerm path {path} does not exist.'.format(path=parts))

        return (taxonomy, term)

    def get_taxonomy(self, code) -> Taxonomy:
        """Return taxonomy identified by code."""
        return Taxonomy.query.filter(Taxonomy.code == code).first()

    def get_term(self, taxonomy: Taxonomy, slug: str) -> TaxonomyTerm:
        """Get TaxonomyTerm by its slug."""
        return TaxonomyTerm.query.filter(and_(TaxonomyTerm.slug == slug, TaxonomyTerm.taxonomy == taxonomy)).first()

    def insert_term_under(self, term: TaxonomyTerm, under: TaxonomyTerm):
        """Insert/Move Term under another term in tree structure"""
        term.move_inside(under.id)

    def move_tree(self, source_path: str, destination_path: str):
        stax, sterm = self.get_from_path(source_path)
        dtax, dterm = self.get_from_path(destination_path)

        if not stax or not sterm:
            raise AttributeError('Invalid source Taxonomy tree path.')
        if not dtax:
            raise AttributeError('Invalid destination Taxonomy tree path')

        def _update_children(children: dict) -> TaxonomyTerm:
            if 'children' in children:
                for child in children['children']:
                    node = _update_children(child)

            node = children['node']
            node.taxonomy = dtax
            #db.session.add(node)
            return node

        children = sterm.drilldown_tree()[0]
        _update_children(children)

        sterm.move_inside(dterm)
        db.session.add(sterm)
        db.session.commit()
