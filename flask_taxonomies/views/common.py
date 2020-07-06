import functools
import json

import sqlalchemy
from flask import Blueprint, Response, abort

from build.lib.flask_taxonomies.constants import INCLUDE_ANCESTORS
from flask_taxonomies.term_identification import TermIdentification
from flask_taxonomies.constants import INCLUDE_DELETED, INCLUDE_ANCESTORS_HIERARCHY
from flask_taxonomies.models import TaxonomyTerm, TermStatusEnum
from flask_taxonomies.proxies import current_flask_taxonomies

blueprint = Blueprint('flask_taxonomies', __name__)


def with_prefer(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        prefer = kwargs.pop('prefer')
        include = kwargs.pop('include')
        exclude = kwargs.pop('exclude')
        select = kwargs.pop('select')
        levels = kwargs.pop('levels')

        options = {}
        if levels is not None:
            options['levels'] = int(levels)
        prefer = prefer.copy(include=include, exclude=exclude, select=select, options=options or None)
        kwargs['prefer'] = prefer
        return func(*args, **kwargs)

    return wrapped


def build_ancestors(term, tops, stack, representation, root_slug, transformers=None):
    if INCLUDE_DELETED in representation:
        status_cond = sqlalchemy.sql.true()
    else:
        status_cond = TaxonomyTerm.status == TermStatusEnum.alive

    ancestors = current_flask_taxonomies.ancestors(
        TermIdentification(term=term), status_cond=status_cond
    )
    if root_slug is not None:
        ancestors = ancestors.filter(TaxonomyTerm.slug > root_slug)
    ancestors = ancestors.order_by(TaxonomyTerm.slug)
    if INCLUDE_ANCESTORS in representation and INCLUDE_ANCESTORS_HIERARCHY not in representation:
        ret = []
        for anc in ancestors:
            desc_repr = anc.json(representation)
            if transformers:
                for transformer in transformers:
                    desc_repr = transformer(json=desc_repr, term=anc, representation=representation)
            ret.append(desc_repr)
        return ret
    else:
        if not transformers:
            transformers = []

        def transformer(json, **kwargs):
            if 'ancestor' not in json:
                json['ancestor'] = True
            return json

        transformers = [*transformers, transformer]
        build_descendants(ancestors, representation, root_slug, stack=stack, tops=tops, transformers=transformers)


def build_descendants(descendants, representation, root_slug, stack=None, tops=None, transformers=None):
    if stack is None:
        stack = []
    if tops is None:
        tops = []

    for desc in descendants:
        while stack and not desc.slug.startswith(stack[-1][0]):
            stack.pop()
        ancestors = None
        if not stack and desc.parent_slug != root_slug:
            # ancestors are missing, serialize them before this element
            if INCLUDE_ANCESTORS_HIERARCHY in representation:
                build_ancestors(desc, tops, stack, representation, root_slug, transformers)
            elif INCLUDE_ANCESTORS in representation:
                ancestors = build_ancestors(desc, tops, stack, representation, root_slug, transformers)

        desc_repr = desc.json(representation)
        if ancestors and 'ancestors' not in desc_repr:
            desc_repr['ancestors'] = ancestors

        if transformers:
            for transformer in transformers:
                desc_repr = transformer(json=desc_repr, term=desc, representation=representation)
        if stack:
            stack[-1][1].setdefault('children', []).append(desc_repr)
        else:
            tops.append(desc_repr)
        stack.append([desc.slug + '/', desc_repr])

    return tops


def json_abort(status_code, detail):
    resp = Response(json.dumps(detail, indent=4, ensure_ascii=False),
                    status=status_code,
                    mimetype='application/json; charset=utf-8')
    abort(status_code, response=resp)
