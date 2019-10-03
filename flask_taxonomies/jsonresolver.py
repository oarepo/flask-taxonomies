# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2015-2018 CERN.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""JSON resolver for JSON schemas."""

from __future__ import absolute_import, print_function

import traceback

import jsonresolver
from flask import current_app
from werkzeug.routing import Rule

from flask_taxonomies.models import Taxonomy
from flask_taxonomies.views import format_ancestor, jsonify_taxonomy_term


@jsonresolver.hookimpl
def jsonresolver_loader(url_map):
    """JSON resolver plugin that loads the schema endpoint.

    Injected into Invenio-Records JSON resolver.
    """
    url_map.add(Rule(
        "/api/taxonomies/<string:code>/<path:slug>",
        endpoint=get_taxonomy_term,
        host=current_app.config.get('SERVER_NAME')
    ))


def get_taxonomy_term(code=None, slug=None):

    try:
        taxonomy = Taxonomy.get(code)
        term = taxonomy.find_term(slug)
        parents = [format_ancestor(x) for x in term.ancestors]
    except:
        traceback.print_exc()
        raise ValueError("The taxonomy term does not exist.")
    return jsonify_taxonomy_term(term, taxonomy.code, term.tree_path,
                                 term.parent.tree_path or '', parents)
