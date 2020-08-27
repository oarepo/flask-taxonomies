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
    INCLUDE_SELF,
    INCLUDE_STATUS,
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
@use_kwargs(HeaderSchema, locations=("headers",))
@use_kwargs(PaginatedQuerySchema, locations=("query",))
@with_prefer
def list_taxonomies(prefer=None, page=None, size=None, q=None):
    current_flask_taxonomies.permissions.taxonomy_list.enforce(request=request)
    taxonomies = current_flask_taxonomies.list_taxonomies(
        return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer,
        return_descendants_busy_count=INCLUDE_STATUS in prefer)
    if q:
        taxonomies = current_flask_taxonomies.apply_taxonomy_query(taxonomies, q)
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
@use_kwargs(HeaderSchema, locations=("headers",))
@use_kwargs(PaginatedQuerySchema, locations=("query",))
@with_prefer
def get_taxonomy(code=None, prefer=None, page=None, size=None, status_code=200, q=None):
    try:
        taxonomies = current_flask_taxonomies.filter_taxonomy(
            code, return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer,
            return_descendants_busy_count=INCLUDE_STATUS in prefer
        )
        taxonomy = taxonomies.one()
        taxonomy = enrich_data_with_computed(taxonomy)
    except NoResultFound:
        json_abort(404, {})
        return  # make pycharm happy

    current_flask_taxonomies.permissions.taxonomy_read.enforce(request=request, status_code=404)

    prefer = taxonomy.merge_select(prefer)

    try:
        if INCLUDE_SELF in prefer:
            paginator = Paginator(
                prefer, [taxonomy], page=0, size=0,
                json_converter=lambda data: [x.json(prefer) for x in data],
                envelope_links=lambda prefer, data, original_data: original_data[0].links(
                    prefer) if original_data else EnvelopeLinks({}, {}),
                single_result=True, allow_empty=False)

            if INCLUDE_DESCENDANTS not in prefer:
                return paginator.jsonify(status_code=status_code)
        else:
            paginator = None

        if INCLUDE_DESCENDANTS in prefer:
            if INCLUDE_DELETED in prefer:
                status_cond = sqlalchemy.sql.true()
            else:
                status_cond = TaxonomyTerm.status == TermStatusEnum.alive

            descendants = current_flask_taxonomies.list_taxonomy(
                taxonomy,
                levels=prefer.options.get('levels', None),
                status_cond=status_cond,
                return_descendants_count=INCLUDE_DESCENDANTS_COUNT in prefer,
                return_descendants_busy_count=INCLUDE_STATUS in prefer
            )
            if q:
                descendants = current_flask_taxonomies.apply_term_query(descendants, q, code)

            child_exclude = set(prefer.exclude)
            child_exclude.discard(INCLUDE_SELF)
            child_prefer = prefer.copy(exclude=child_exclude).extend(include=[INCLUDE_SELF])

            child_paginator = Paginator(
                child_prefer, descendants, page, size,
                json_converter=lambda data: build_descendants(data, prefer, root_slug=None)
            )

            if INCLUDE_SELF in prefer:
                paginator.set_children(child_paginator.paginated_data_without_envelope)
                # reset page, size, count from the child paginator
                paginator.page = page
                paginator.size = size
                paginator.count = child_paginator.count
            else:
                paginator = child_paginator

        return paginator.jsonify(status_code=status_code)

    except NoResultFound:
        json_abort(404, {})
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>', methods=['PUT'], strict_slashes=False)
@use_kwargs(HeaderSchema, locations=("headers",))
@use_kwargs(PaginatedQuerySchema, locations=("query",))
@with_prefer
def create_update_taxonomy(code=None, prefer=None, page=None, size=None, q=None):
    if q:
        json_abort(422, {
            'message': 'Query not appropriate when creating or updating taxonomy',
            'reason': 'search-query-not-allowed'
        })
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
    current_flask_taxonomies.commit()
    return get_taxonomy(code, prefer=prefer, page=page, size=size, status_code=status_code)


@blueprint.route('/<code>', methods=['PATCH'], strict_slashes=False)
@use_kwargs(HeaderSchema, locations=("headers",))
@use_kwargs(PaginatedQuerySchema, locations=("query",))
@with_prefer
def patch_taxonomy(code=None, prefer=None, page=None, size=None, q=None):
    if q:
        json_abort(422, {
            'message': 'Query not appropriate when creating or updating taxonomy',
            'reason': 'search-query-not-allowed'
        })

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
    current_flask_taxonomies.commit()

    return get_taxonomy(code, prefer=prefer, page=page, size=size, status_code=status_code)


@blueprint.route('/', methods=['POST'], strict_slashes=False)
@use_kwargs(HeaderSchema, locations=("headers",))
@use_kwargs(QuerySchema, locations=("query",))
@with_prefer
def create_update_taxonomy_post(prefer=None, q=None):
    if q:
        json_abort(422, {
            'message': 'Query not appropriate when creating or updating taxonomy',
            'reason': 'search-query-not-allowed'
        })
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
    current_flask_taxonomies.commit()

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
    current_flask_taxonomies.commit()
    return Response(status=204)
