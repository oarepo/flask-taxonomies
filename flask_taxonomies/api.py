# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Miroslav Bauer, CESNET.
#
# flask-taxonomies is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Taxonomy API"""

from __future__ import absolute_import, print_function

from flask import current_app, url_for
from invenio_db import db
from slugify import slugify
from sqlalchemy.exc import IntegrityError

from flask_taxonomies.models import Taxonomy, before_taxonomy_created, after_taxonomy_created, \
    before_taxonomy_term_moved, MovePosition, after_taxonomy_term_moved, TaxonomyTerm, after_taxonomy_term_created, \
    before_taxonomy_term_created, before_taxonomy_deleted, after_taxonomy_deleted, before_taxonomy_term_deleted, \
    after_taxonomy_term_deleted, before_taxonomy_updated, after_taxonomy_updated, before_taxonomy_term_updated, \
    after_taxonomy_term_updated
from flask_taxonomies.signals import check_references_before_delete


class TaxonomyAPI(object):
    """Represents a taxonomy API.
    """
    @classmethod
    def taxonomy_list(cls):
        """Return a list of all available taxonomies."""
        return Taxonomy.taxonomies()

    @classmethod
    def create_taxonomy(cls, code, extra_data=None) -> Taxonomy:
        """Creates a new taxonomy.
        :param code: taxonomy code
        :param extra_data: taxonomy metadata
        :raises IntegrityError
        :returns Taxonomy
        """
        before_taxonomy_created.send(current_app._get_current_object(),
                                     code=code, extra_data=extra_data)
        created = Taxonomy.create_taxonomy(code=code, extra_data=extra_data)
        db.session.commit()
        after_taxonomy_created.send(created)
        return created

    @classmethod
    def update_taxonomy(cls, taxonomy: Taxonomy, extra_data) -> Taxonomy:
        """Updates a taxonomy.
        :param taxonomy: taxonomy instance to be updated
        :param extra_data: new taxonomy metadata
        :return Taxonomy: updated taxonomy
        """
        before_taxonomy_updated.send(taxonomy, taxonomy=taxonomy, extra_data=extra_data)
        taxonomy.update(extra_data)
        db.session.commit()
        after_taxonomy_updated.send(taxonomy, taxonomy=taxonomy)
        return taxonomy

    @classmethod
    def delete_taxonomy(cls, taxonomy: Taxonomy):
        """Delete a taxonomy.
        :param taxonomy: taxonomy instance to be deleted
        :raise TaxonomyDeleteError
        """
        before_taxonomy_deleted.send(taxonomy, taxonomy=taxonomy)
        check_references_before_delete(taxonomy, taxonomy=taxonomy)
        taxonomy.delete()
        db.session.commit()
        after_taxonomy_deleted.send(taxonomy)

    @classmethod
    def move_term(cls, taxonomy, term_path='', target_path=None, destination_order=''):
        """Moves a taxonomy term to a different path.
        :param taxonomy: source taxonomy instance
        :param term_path: current path of a term
        :param target_path: desired path of a term
        :param destination_order: order in a destination tree
        :raise AttributeError
        :raise NoResultFound
        :return Tuple(Taxonomy, Taxonomy, Optional[Taxonomy]): target taxonomy and moved term
        """
        term = taxonomy.find_term(term_path)
        if not term:
            raise AttributeError('Invalid Term path given.')

        before_taxonomy_term_moved.send(
            term, taxonomy=taxonomy,
            target_path=target_path, order=destination_order)

        if not target_path:
            target_path = f'{taxonomy.code}/'

        target_taxonomy, target_term = Taxonomy.find_taxonomy_and_term(target_path)

        term.move(target_term, position=MovePosition(destination_order or 'inside'))
        db.session.commit()

        after_taxonomy_term_moved.send(term, taxonomy=taxonomy)
        db.session.refresh(term)
        return (term, target_taxonomy, target_term)

    @classmethod
    def create_term(cls, taxonomy, term_path='', slug=None, extra_data=None) -> TaxonomyTerm:
        """Creates a taxonomy term.
        :param taxonomy: taxonomy in which to create a term
        :param term_path: path on which to create a term
        :param slug: term slug
        :param extra_data: term metadata]
        :raise AttributeError
        :raise IntegrityError
        :return TaxonomyTerm
        """
        term = taxonomy.find_term(term_path)
        if not term:
            raise AttributeError('Invalid Term path given.')

        try:
            slug = slugify(slug)
            before_taxonomy_term_created.send(taxonomy, slug=slug, extra_data=extra_data)
            created = term.create_term(slug=slug, extra_data=extra_data)
            db.session.commit()
            after_taxonomy_term_created.send(term, taxonomy=taxonomy)
            return created
        except IntegrityError as ie:
            db.session.rollback()
            raise ie

    def term_links(self, taxonomy_code: str, path: str, parent_path: str=None):
        """Return a reference URIs for a given term."""
        links = {
            "self": url_for(
                "taxonomies.taxonomy_get_term",
                taxonomy_code=taxonomy_code,
                term_path=path[1:],
                _external=True,
            ),
            "tree": url_for(
                "taxonomies.taxonomy_get_term",
                taxonomy_code=taxonomy_code,
                term_path=path[1:],
                drilldown=True,
                _external=True,
            )
        }
        if parent_path is not None:
            if parent_path != '':
                txc = taxonomy_code + parent_path
                txc = txc.split('/', maxsplit=1)
                links.update({
                    "parent": url_for(
                        "taxonomies.taxonomy_get_term",
                        taxonomy_code=txc[0],
                        term_path=txc[1],
                        _external=True,
                    ),
                    "parent_tree": url_for(
                        "taxonomies.taxonomy_get_term",
                        taxonomy_code=txc[0],
                        term_path=txc[1],
                        drilldown=True,
                        _external=True,
                    )
                })
            else:
                # parent is a taxonomy
                links.update({
                    "parent": url_for(
                        "taxonomies.taxonomy_get_roots",
                        taxonomy_code=taxonomy_code,
                        _external=True,
                    ),
                    "parent_tree": url_for(
                        "taxonomies.taxonomy_get_roots",
                        taxonomy_code=taxonomy_code,
                        drilldown=True,
                        _external=True,
                    )
                })

        return links

    @classmethod
    def update_term(cls, taxonomy: Taxonomy, term: TaxonomyTerm, changes) -> TaxonomyTerm:
        """Updates a taxonomy term.
        :param taxonomy: taxonomy instance of the term
        :param term: term instance to be updated
        :param extra_data: new term metadata
        :return TaxonomyTerm: updated taxonomy term
        """
        before_taxonomy_term_updated.send(term, term=term, taxonomy=taxonomy, extra_data=changes['extra_data'])
        term.update(**changes)
        db.session.commit()
        after_taxonomy_term_updated.send(term, term=term, taxonomy=taxonomy)
        return term

    @classmethod
    def delete_term(cls, taxonomy: Taxonomy, term: TaxonomyTerm):
        """Delete a taxonomy term.
        :param taxonomy: taxonomy of the term
        :param term: term instance to be deleted
        :raise TaxonomyDeleteError
        """
        before_taxonomy_term_deleted.send(term, taxonomy=taxonomy, term=term)
        check_references_before_delete(term, taxonomy=taxonomy, term=term)
        term.delete()
        db.session.commit()
        after_taxonomy_term_deleted.send(term, taxonomy=taxonomy, term=term)

    @classmethod
    def reindex_referencing_records(cls, reference):
        pass


__all__ = (
    'TaxonomyAPI',
)
