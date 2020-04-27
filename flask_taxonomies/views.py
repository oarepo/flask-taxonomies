import functools
import traceback

from flask import Blueprint, jsonify, abort
from sqlalchemy.orm.exc import NoResultFound
from webargs.flaskparser import use_kwargs

from flask_taxonomies.api import TermIdentification
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
        select = kwargs.pop('select')
        levels = kwargs.pop('levels')

        options = {}
        if levels is not None:
            options['levels'] = int(levels)
        prefer = prefer.copy(include=include, exclude=exclude, select=select, options=options or None)
        kwargs['prefer'] = prefer
        return func(*args, **kwargs)

    return wrapped


class Paginator:
    def __init__(self, data, page, size, json_converter):
        self.data = data
        self.page = page
        self.size = size
        self.count = None
        self.json_converter = json_converter

    def paginate(self):
        if self.size:
            self.count = self.data.count()
            return self.data[(self.page - 1) * self.size: self.page * self.size]
        return self.data

    @property
    def paginated_data(self):
        resp = self.json_converter(self.paginate())
        if not self.size:
            return resp
        return {
            'page': self.page,
            'size': self.size,
            'total': self.count,
            'data': resp
        }

    @property
    def no_pagination(self):
        return not self.size


@blueprint.route('/')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(QuerySchema, location="query")
@with_prefer
def list_taxonomies(prefer=None, page=None, size=None):
    taxonomies = current_flask_taxonomies.list_taxonomies()
    paginator = Paginator(taxonomies, page, size, lambda data: [
        x.json(representation=prefer) for x in data
    ])
    return jsonify(paginator.paginated_data)


def build_ancestors(term, tops, stack, representation, root_slug):
    if INCLUDE_DELETED in representation:
        status_cond = None
    else:
        status_cond = TaxonomyTerm.status == TermStatusEnum.alive

    ancestors = current_flask_taxonomies.ancestors(
        TermIdentification(term=term), status_cond=status_cond
    )
    if root_slug is not None:
        ancestors = ancestors.filter(TaxonomyTerm.slug > root_slug)
    ancestors = ancestors.order_by(TaxonomyTerm.slug)
    build_descendants(ancestors, representation, root_slug, stack=stack, tops=tops)


def build_descendants(descendants, representation, root_slug, stack=None, tops=None):
    if stack is None:
        stack = []
    if tops is None:
        tops = []

    for desc in descendants:
        while stack and not desc.slug.startswith(stack[-1][0]):
            stack.pop()
        if not stack and desc.parent_slug != root_slug:
            # ancestors are missing, serialize them before this element
            build_ancestors(desc, tops, stack, representation, root_slug)

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
def get_taxonomy(code=None, prefer=None, page=None, size=None):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        taxonomy_repr = taxonomy.json(representation=prefer)
        if INCLUDE_DESCENDANTS in prefer:
            if INCLUDE_DELETED in prefer:
                status_cond = None
            else:
                status_cond = TaxonomyTerm.status == TermStatusEnum.alive

            paginator = Paginator(current_flask_taxonomies.list_taxonomy(
                taxonomy,
                levels=prefer.options.get('levels', None),
                status_cond=status_cond
            ), page, size, lambda data: build_descendants(data, prefer, root_slug=None))
            if paginator.no_pagination:
                taxonomy_repr['children'] = paginator.paginated_data
            else:
                # move page, size, total to top-level to follow paginated response pattern
                data = paginator.paginated_data
                taxonomy_repr['children'] = data['data']
                data['data'] = taxonomy_repr
                taxonomy_repr = data
        return jsonify(taxonomy_repr)

    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise
