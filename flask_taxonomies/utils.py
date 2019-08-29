# -*- coding: utf-8 -*-
"""Taxonomy utility functions."""
import json

import six
import sqlalchemy
from flask import current_app
from werkzeug.utils import import_string

from flask_taxonomies.models import TaxonomyTerm


def obj_or_import_string(value, default=None):
    """
    Import string or return object.
    :params value: Import path or class object to instantiate.
    :params default: Default object to return if the import fails.
    :returns: The imported object.
    """
    if isinstance(value, six.string_types):
        return import_string(value)
    elif value:  # pragma: nocover
        return value  # pragma: nocover
    return default  # pragma: nocover


def load_or_import_from_config(key, app=None, default=None):
    """
    Load or import value from config.
    :returns: The loaded value.
    """
    app = app or current_app
    imp = app.config.get(key)
    return obj_or_import_string(imp, default=default)


def find_in_json(search_term: str, taxonomy, tree_address=("title", 0, "value")):
    """
    Function returns taxonomy field based on searching term in json tree.
    :param search_term: searched term
    :param taxonomy: Taxonomy class
    :param tree_address: Address of searched field. Address is inserted as tuple.
    :return: SQLAlchemy BaseQuery
    """
    ed = TaxonomyTerm.extra_data
    for t in tree_address:
        ed = ed[t]
    expr = sqlalchemy.cast(ed, sqlalchemy.String) == json.dumps(search_term, ensure_ascii=False)
    query = taxonomy.descendants.filter(expr)
    return query


def find_in_json_contains(search_term: str, taxonomy, tree_address="aliases"):
    """
    Function returns taxonomy field based on searching term in json tree.
    :param search_term: searched term
    :param taxonomy: Taxonomy class
    :param tree_address: Address of searched field.
    :return: SQLAlchemy BaseQuery
    """
    expr = sqlalchemy.cast(TaxonomyTerm.extra_data[tree_address], sqlalchemy.String).\
        contains(search_term)
    query = taxonomy.descendants.filter(expr)
    return query
