import functools
import traceback

from flask import Blueprint, jsonify, abort
from sqlalchemy.orm.exc import NoResultFound
from webargs.flaskparser import use_kwargs

from flask_taxonomies.constants import INCLUDE_DESCENDANTS, INCLUDE_DELETED
from flask_taxonomies.marshmallow import HeaderSchema, QuerySchema
from flask_taxonomies.models import TaxonomyTerm, TermStatusEnum
from flask_taxonomies.proxies import current_flask_taxonomies

blueprint = Blueprint('flask_taxonomies', __name__, url_prefix='/api/1.0/taxonomies')


# @parser.location_handler("extra_data")
# def parse_extra_data(request, name, field):
#     if name == 'extra_data':
#         extra = {**request.json}
#         extra.pop('code', None)
#         extra.pop('slug', None)
#         return extra

def with_prefer(func):
    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        prefer = kwargs.pop('prefer')
        include = kwargs.pop('include')
        exclude = kwargs.pop('exclude')
        selectors = kwargs.pop('selectors')
        levels = kwargs.pop('levels')

        options = {}
        if levels is not None:
            options['levels'] = int(levels)
        prefer = prefer.copy(include=include, exclude=exclude, selectors=selectors, options=options or None)
        kwargs['prefer'] = prefer
        return func(*args, **kwargs)

    return wrapped


@blueprint.route('/')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(QuerySchema, location="query")
@with_prefer
def list_taxonomies(prefer=None):
    taxonomies = [
        x.json(representation=prefer) for x in current_flask_taxonomies.list_taxonomies()
    ]
    return jsonify(taxonomies)


def build_descendants(descendants, representation):
    stack = []
    tops = []
    for desc in descendants:
        while stack and not desc.slug.startswith(stack[-1][0]):
            stack.pop()
        desc_repr = desc.json(representation)
        if stack:
            stack[-1][1].setdefault('children', []).append(desc_repr)
        else:
            tops.append(desc_repr)
        stack.append([desc.slug + '/', desc_repr])
    return tops


@blueprint.route('/<code>')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(QuerySchema, location="query")
@with_prefer
def get_taxonomy(code=None, prefer=None):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        taxonomy_repr = taxonomy.json(representation=prefer)
        if INCLUDE_DESCENDANTS in prefer:
            if INCLUDE_DELETED in prefer:
                status_cond = None
            else:
                status_cond = TaxonomyTerm.status == TermStatusEnum.alive
            taxonomy_repr['children'] = build_descendants(current_flask_taxonomies.list_taxonomy(
                taxonomy,
                levels=prefer.options.get('levels', None),
                status_cond=status_cond
            ), prefer)
        return jsonify(taxonomy_repr)
    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise
