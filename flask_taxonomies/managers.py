# -*- coding: utf-8 -*-
"""Managers module for database models."""
from typing import Iterator, Optional

from sqlalchemy import and_

from flask_taxonomies.extensions import db
from flask_taxonomies.models import Taxonomy, TaxonomyTerm


class TaxonomyManager(object):
    """Manager of Taxonomy tree db models."""

    @staticmethod
    def create(slug: str, title: dict, path: str, extra_data=None) -> TaxonomyTerm:
        """Create TaxonomyTerm on a given path."""
        taxonomy, parent_term = TaxonomyManager.get_from_path(path)
        if not taxonomy:
            raise AttributeError('Invalid Taxonomy path.')

        for term in taxonomy.terms:
            if term.slug == slug:
                raise ValueError('Slug {slug} already exists within {tax}.'.format(slug=slug, tax=taxonomy))

        t = TaxonomyTerm(slug, title, taxonomy, extra_data)

        if parent_term:
            TaxonomyManager.insert_term_under(t, parent_term)

        db.session.add(t)
        db.session.commit()

        return t

    @staticmethod
    def delete_tree(path: str):
        """Delete a subtree of Terms on a given path."""
        taxo, term = TaxonomyManager.get_from_path(path)
        if not term:
            raise AttributeError('Invalid TaxonomyTerm path.')

        db.session.delete(term)
        db.session.commit()

    @staticmethod
    def get_from_path(path: str) -> (Taxonomy, TaxonomyTerm):
        """Get Taxonomy and Term on a given path in Taxonomy."""
        taxonomy = None
        term = None
        parts = list(filter(None, path.lstrip('/').split('/', 1)))

        if len(parts) >= 1:
            taxonomy = TaxonomyManager.get_taxonomy(parts[0])

        if taxonomy and len(parts) == 2:
            slug = parts[1].rstrip('/').split('/')[-1]
            term = TaxonomyManager.get_term(taxonomy=taxonomy, slug=slug)
            if not term:
                raise AttributeError('TaxonomyTerm path {path} does not exist.'.format(path=parts))

        return (taxonomy, term)

    @staticmethod
    def get_taxonomy(code) -> Optional[Taxonomy]:
        """Return taxonomy identified by code or None if not found."""
        return Taxonomy.query.filter(Taxonomy.code == code).first()

    @staticmethod
    def get_taxonomy_roots(taxonomy: Taxonomy) -> Iterator:
        """Return a list of top-level TaxonomyTerms."""
        return filter(lambda t: t.parent is None, taxonomy.terms)

    @staticmethod
    def get_term(taxonomy: Taxonomy, slug: str) -> Optional[TaxonomyTerm]:
        """Get TaxonomyTerm by its slug or None if not found."""
        return TaxonomyTerm.query.filter(and_(TaxonomyTerm.slug == slug, TaxonomyTerm.taxonomy == taxonomy)).first()

    @staticmethod
    def insert_term_under(term: TaxonomyTerm, under: TaxonomyTerm):
        """Insert/Move Term under another term in tree structure"""
        term.move_inside(under.id)

    @staticmethod
    def move_tree(source_path: str, destination_path: str):
        stax, sterm = TaxonomyManager.get_from_path(source_path)
        dtax, dterm = TaxonomyManager.get_from_path(destination_path)

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
            # db.session.add(node)
            return node

        children = sterm.drilldown_tree()[0]
        _update_children(children)

        if dterm:
            sterm.move_inside(dterm.id)
        else:
            sterm.move_inside(dtax.id)

        db.session.add(sterm)
        db.session.commit()
