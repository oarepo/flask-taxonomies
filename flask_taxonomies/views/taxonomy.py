import traceback

import jsonpatch
import sqlalchemy
from flask import Response, abort, request
from sqlalchemy.orm.exc import NoResultFound
from webargs.flaskparser import use_kwargs

from flask_taxonomies.constants import (
    INCLUDE_DELETED,
    INCLUDE_DESCENDANTS,
    INCLUDE_DESCENDANTS_COUNT,
)
from flask_taxonomies.marshmallow import HeaderSchema, PaginatedQuerySchema, QuerySchema
from flask_taxonomies.models import EnvelopeLinks, TaxonomyTerm, TermStatusEnum
from flask_taxonomies.proxies import current_flask_taxonomies

from .common import (
    blueprint,
    build_descendants,
    enrich_data_with_computed,
    json_abort,
    with_prefer,
)
from .paginator import Paginator


@blueprint.route('/')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def list_taxonomies(prefer=None, page=None, size=None):
    current_flask_taxonomies.permissions.taxonomy_list.enforce(request=request)
    taxonomies = current_flask_taxonomies.list_taxonomies(return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer)
    paginator = Paginator(
        prefer, taxonomies, page, size,
        json_converter=lambda data: [x.json(representation=prefer) for x in data],
        envelope_links=EnvelopeLinks(
            envelope={'self': request.url},
            headers={'self': request.url}
        )
    )
    return paginator.jsonify()


@blueprint.route('/<code>', strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def get_taxonomy(code=None, prefer=None, page=None, size=None, status_code=200):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(
            code, return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer
        )
        taxonomy = enrich_data_with_computed(taxonomy)
    except NoResultFound:
        json_abort(404, {})
        return  # make pycharm happy

    current_flask_taxonomies.permissions.taxonomy_read.enforce(request=request, status_code=404)

    prefer = taxonomy.merge_select(prefer)

    try:
        paginator = Paginator(
            prefer, [taxonomy], page=0, size=0,
            json_converter=lambda data: [x.json(prefer) for x in data],
            envelope_links=lambda prefer, data, original_data: original_data[0].links(
                prefer) if original_data else EnvelopeLinks({}, {}),
            single_result=True, allow_empty=False)

        if INCLUDE_DESCENDANTS not in prefer:
            return paginator.jsonify(status_code=status_code)

        if INCLUDE_DESCENDANTS in prefer:
            if INCLUDE_DELETED in prefer:
                status_cond = sqlalchemy.sql.true()
            else:
                status_cond = TaxonomyTerm.status == TermStatusEnum.alive

            child_paginator = Paginator(
                prefer, current_flask_taxonomies.list_taxonomy(
                    taxonomy,
                    levels=prefer.options.get('levels', None),
                    status_cond=status_cond,
                    return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer
                ), page, size,
                json_converter=lambda data: build_descendants(data, prefer, root_slug=None)
            )

            paginator.set_children(child_paginator.paginated_data_without_envelope)

            # reset page, size, count from the child paginator
            paginator.page = page
            paginator.size = size
            paginator.count = child_paginator.count

        return paginator.jsonify(status_code=status_code)

    except NoResultFound:
        json_abort(404, {})
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>', methods=['PUT'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_update_taxonomy(code=None, prefer=None, page=None, size=None):
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)

    if tax:
        current_flask_taxonomies.permissions.taxonomy_update.enforce(request=request, taxonomy=tax)
    else:
        current_flask_taxonomies.permissions.taxonomy_create.enforce(request=request, code=code)

    data = request.json
    url = data.pop('url', None)
    select = data.pop('select', None)
    if not tax:
        current_flask_taxonomies.create_taxonomy(code=code, extra_data=request.json, url=url, select=select)
        status_code = 201
    else:
        current_flask_taxonomies.update_taxonomy(tax, extra_data=request.json, url=url, select=select)
        status_code = 200

    return get_taxonomy(code, prefer=prefer, page=page, size=size, status_code=status_code)


@blueprint.route('/<code>', methods=['PATCH'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def patch_taxonomy(code=None, prefer=None, page=None, size=None):
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)
    if not tax:
        json_abort(404, {})

    current_flask_taxonomies.permissions.taxonomy_update.enforce(request=request, taxonomy=tax)

    data = {
        **(tax.extra_data or {}),
        'url': tax.url,
        'select': tax.select
    }
    data = jsonpatch.apply_patch(data, request.json)
    url = data.pop('url', None)
    select = data.pop('select', None)
    current_flask_taxonomies.update_taxonomy(tax, extra_data=data, url=url, select=select)
    status_code = 200

    return get_taxonomy(code, prefer=prefer, page=page, size=size, status_code=status_code)


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
    select = data.pop('select', None)
    tax = current_flask_taxonomies.get_taxonomy(code=code, fail=False)
    if not tax:
        current_flask_taxonomies.permissions.taxonomy_create.enforce(request=request, code=code)
        current_flask_taxonomies.create_taxonomy(code=code, extra_data=data, url=url, select=select)
        status_code = 201
    else:
        current_flask_taxonomies.permissions.taxonomy_update.enforce(request=request, taxonomy=tax)
        current_flask_taxonomies.update_taxonomy(tax, extra_data=data, url=url, select=select)
        status_code = 200

    return get_taxonomy(code, prefer=prefer, status_code=status_code)


@blueprint.route('/<code>', methods=['DELETE'], strict_slashes=False)
def delete_taxonomy(code=None):
    """
    Deletes a taxonomy.

    Note: this call is destructive in a sense that all its terms, regardless if used or not,
    are deleted as well. A tight user permissions should be employed.
    """
    try:
        tax = current_flask_taxonomies.get_taxonomy(code=code)
    except NoResultFound:
        json_abort(404, {})
        return  # make pycharm happy

    current_flask_taxonomies.permissions.taxonomy_delete.enforce(request=request, code=code)
    current_flask_taxonomies.delete_taxonomy(tax)
    return Response(status=204)
