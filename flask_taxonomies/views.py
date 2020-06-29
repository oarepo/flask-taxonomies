import functools
import traceback
from urllib.parse import urljoin

from flask import Blueprint, jsonify, abort, request, Response
from link_header import LinkHeader, Link
from sqlalchemy.orm.exc import NoResultFound
from webargs.flaskparser import use_kwargs
from werkzeug.utils import cached_property

from flask_taxonomies.api import TermIdentification
from flask_taxonomies.constants import INCLUDE_DESCENDANTS, INCLUDE_DELETED, INCLUDE_ENVELOPE
from flask_taxonomies.marshmallow import HeaderSchema, QuerySchema, PaginatedQuerySchema
from flask_taxonomies.models import TaxonomyTerm, TermStatusEnum, EnvelopeLinks
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


class Paginator:
    def __init__(self, representation, data, page, size,
                 json_converter=None, envelope_links=None,
                 allow_empty=True, single_result=False):
        self.data = data
        self.page = page
        self.size = size
        self.count = None
        self.use_envelope = INCLUDE_ENVELOPE in representation
        self.json_converter = json_converter or (lambda _data: [x.json(representation=representation) for x in _data])
        self.allow_empty = allow_empty
        self.single_result = single_result
        self._envelope_links = envelope_links or self._default_envelope_links
        self.representation = representation

    @cached_property
    def _data(self):
        if self.size:
            self.count = self.data.count()
            data = list(self.data[(self.page - 1) * self.size: self.page * self.size])
        else:
            data = list(self.data)
        if not self.allow_empty and not data:
            raise NoResultFound()
        return self.json_converter(data), data

    def set_children(self, children):
        self._data[0][0]['children'] = children

    @property
    def headers(self):
        data, original = self._data
        links = self.envelope_links(self.representation, data, original).headers
        headers = {
            'Link': str(LinkHeader([Link(v, rel=k) for k, v in links.items()]))
        }
        if self.size:
            headers.update({
                'X-Page': self.page,
                'X-PageSize': self.size,
                'X-Total': self.count,
            })

        return headers

    def check_single_result(self, data, original):
        if self.single_result:
            if not data:
                raise NoResultFound()
            data = data[0]
        elif INCLUDE_ENVELOPE in self.representation:
            data = {
                'data': data,
                'links': self.envelope_links(self.representation, data, original).envelope
            }
            if self.size:
                data.update({
                    'page': self.page,
                    'size': self.size,
                    'total': self.count,
                })

        return data

    @property
    def paginated_data(self):
        data, original = self._data
        return self.check_single_result(data, original)

    @property
    def no_pagination(self):
        return not self.size

    def jsonify(self):
        ret = jsonify(self.paginated_data)
        ret.headers = self.headers
        return ret

    def envelope_links(self, representation, data, links) -> EnvelopeLinks:
        el = self._envelope_links
        if callable(el):
            el = el(representation, data, links)
        return el

    def _default_envelope_links(self, representation, data, original_data):
        if not data:
            return EnvelopeLinks({}, {})
        return original_data[0].links(representation)


@blueprint.route('/')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def list_taxonomies(prefer=None, page=None, size=None):
    taxonomies = current_flask_taxonomies.list_taxonomies()
    paginator = Paginator(
        prefer, taxonomies, page, size,
        json_converter=lambda data: [x.json(representation=prefer) for x in data],
        envelope_links=EnvelopeLinks(
            envelope={'self': request.url},
            headers={'self': request.url}
        )
    )
    return paginator.jsonify()


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


@blueprint.route('/<code>', strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def get_taxonomy(code=None, prefer=None, page=None, size=None):
    taxonomy = current_flask_taxonomies.get_taxonomy(code)
    prefer = taxonomy.merge_select(prefer)

    try:
        paginator = Paginator(
            prefer, [taxonomy], page, size,
            json_converter=lambda data: [x.json(prefer) for x in data],
            envelope_links=lambda prefer, data, original_data: original_data[0].links(
                prefer) if original_data else EnvelopeLinks({}, {}),
            single_result=True, allow_empty=False)

        if not INCLUDE_DESCENDANTS in prefer:
            return paginator.jsonify()

        if INCLUDE_DESCENDANTS in prefer:
            if INCLUDE_DELETED in prefer:
                status_cond = None
            else:
                status_cond = TaxonomyTerm.status == TermStatusEnum.alive

            child_paginator = Paginator(
                prefer, current_flask_taxonomies.list_taxonomy(
                    taxonomy,
                    levels=prefer.options.get('levels', None),
                    status_cond=status_cond
                ), page, size,
                json_converter=lambda data: build_descendants(data, prefer, root_slug=None)
            )

            paginator.set_children(child_paginator.paginated_data)

        return paginator.jsonify()

    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>', methods=['PUT'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_update_taxonomy(code=None, prefer=None, page=None, size=None):
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)
    if not tax:
        current_flask_taxonomies.create_taxonomy(code=code, extra_data=request.json)
    else:
        current_flask_taxonomies.update_taxonomy(tax, extra_data=request.json)

    return get_taxonomy(code, prefer=prefer, page=page, size=size)


@blueprint.route('/', methods=['POST'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(QuerySchema, location="query")
@with_prefer
def create_update_taxonomy_post(prefer=None):
    data = request.json
    if 'code' not in data:
        abort(Response('Code missing', status=400))
    code = data.pop('code')
    url = data.pop('url', None)
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)
    if not tax:
        current_flask_taxonomies.create_taxonomy(code=code, extra_data=data, url=url)
    else:
        current_flask_taxonomies.update_taxonomy(tax, extra_data=data, url=url)

    return get_taxonomy(code, prefer=prefer)


@blueprint.route('/<code>', methods=['DELETE'], strict_slashes=False)
def delete_taxonomy(code=None):
    """
    Deletes a taxonomy.

    Note: this call is destructive in a sense that all its terms, regardless if used or not,
    are deleted as well. A tight user permissions should be employed.
    """
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)
    current_flask_taxonomies.delete_taxonomy(tax)
    return Response(status=204)


@blueprint.route('/<code>/<path:slug>', strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def get_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        prefer = taxonomy.merge_select(prefer)

        if INCLUDE_DELETED in prefer:
            status_cond = None
        else:
            status_cond = TaxonomyTerm.status == TermStatusEnum.alive

        return_descendants = INCLUDE_DESCENDANTS in prefer

        if return_descendants:
            query = current_flask_taxonomies.descendants_or_self(
                TermIdentification(taxonomy=code, slug=slug),
                levels=prefer.options.get('levels', None),
                status_cond=status_cond
            )
            single_result = False
        else:
            query = current_flask_taxonomies.filter_term(
                TermIdentification(taxonomy=code, slug=slug),
                status_cond=status_cond
            )
            single_result = True

        paginator = Paginator(
            prefer,
            query, page if return_descendants else None,
            size if return_descendants else None,
            json_converter=lambda data:
            build_descendants(data, prefer, root_slug=None) if return_descendants else [x.json(prefer) for x in data],
            allow_empty=False, single_result=single_result
        )

        return paginator.jsonify()

    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>/<path:slug>', methods=['PUT'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_update_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None):
    return _create_update_taxonomy_term_internal(code, slug, prefer, page, size, request.json)


def _create_update_taxonomy_term_internal(code, slug, prefer, page, size, extra_data):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        prefer = taxonomy.merge_select(prefer)

        if INCLUDE_DELETED in prefer:
            status_cond = None
        else:
            status_cond = TaxonomyTerm.status == TermStatusEnum.alive

        ti = TermIdentification(taxonomy=code, slug=slug)
        term = current_flask_taxonomies.filter_term(ti, status_cond=status_cond).one_or_none()

        if term:
            current_flask_taxonomies.update_term(
                term,
                status_cond=status_cond,
                extra_data=extra_data
            )
        else:
            current_flask_taxonomies.create_term(
                ti,
                extra_data=extra_data
            )

        paginator = Paginator(
            current_flask_taxonomies.descendants_or_self(
                TermIdentification(taxonomy=code, slug=slug),
                levels=prefer.options.get('levels', None),
                status_cond=status_cond
            ), page, size,
            lambda data: build_descendants(data, prefer, root_slug=None))

        result = paginator.paginated_data
        if not INCLUDE_DESCENDANTS in prefer:
            if paginator.no_pagination:
                result = result[0]
            else:
                result = result['data'][0]

        return jsonify(result)

    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>/<path:slug>', methods=['POST'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_taxonomy_term_post(code=None, slug=None, prefer=None, page=None, size=None):
    extra_data = {**request.json}
    if 'slug' not in extra_data:
        return Response('slug missing in payload', status=400)
    _slug = extra_data.pop('slug')
    return _create_update_taxonomy_term_internal(code, urljoin(slug, _slug), prefer, page, size, extra_data)


@blueprint.route('/<code>', methods=['POST'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_taxonomy_term_post_on_root(code=None, slug=None, prefer=None, page=None, size=None):
    extra_data = {**request.json}
    if 'slug' not in extra_data:
        return Response('slug missing in payload', status=400)
    _slug = extra_data.pop('slug')
    return _create_update_taxonomy_term_internal(code, urljoin(slug, _slug), prefer, page, size, extra_data)
