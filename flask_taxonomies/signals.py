# -*- coding: utf-8 -*-
#
# Copyright (C) 2019 Miroslav Bauer, CESNET.
#
# flask-taxonomies is free software; you can redistribute it and/or modify
# it under the terms of the MIT License; see LICENSE file for more details.

"""Taxonomy signal handlers"""

from __future__ import absolute_import, print_function

from werkzeug.exceptions import abort

from flask_taxonomies.proxies import current_flask_taxonomies
from oarepo_references.proxies import current_oarepo_references


def reindex_referencing_records(sender, taxonomy=None, term=None, *args, **kwargs):
    if taxonomy and not term:
        current_oarepo_references.reindex_referencing_records(taxonomy.link_self)
    elif taxonomy and term:
        links = current_flask_taxonomies.term_links(taxonomy.code, term.tree_path)
        current_oarepo_references.reindex_referencing_records(links['self'])


def check_references_before_delete(sender, taxonomy=None, term=None, *args, **kwargs):
    records = []
    if taxonomy and not term:
        # TODO: search for references of any term under a taxonomy
        records = current_oarepo_references.get_records(taxonomy.link_self)
    elif taxonomy and term:
        # TODO: search for references of any term under a taxonomy
        links = current_flask_taxonomies.term_links(taxonomy.code, term.tree_path)
        records = current_oarepo_references.get_records(links['self'])
    if len(records) > 0:
        raise ReferenceError('Cannot Delete. Taxonomy is being referenced from some records.')
