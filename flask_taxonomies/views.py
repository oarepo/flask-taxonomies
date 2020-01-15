# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
from functools import wraps
from typing import List
from urllib.parse import urlsplit

from flask import Blueprint, abort, jsonify, make_response, url_for
from flask_login import current_user
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from webargs import fields
from webargs.flaskparser import parser, use_kwargs
from werkzeug.exceptions import BadRequest

from flask_taxonomies.errors import TaxonomyDeleteError
from flask_taxonomies.flask_routing_ext import accept_fallback
from flask_taxonomies.permissions import (
    permission_taxonomy_create_all,
    permission_taxonomy_read_all,
    permission_term_create_all,
)
from flask_taxonomies.proxies import (
    current_flask_taxonomies,
    current_permission_factory,
)

from .models import Taxonomy, TaxonomyTerm

blueprint = Blueprint("taxonomies", __name__, url_prefix="/taxonomies")


def url_to_path(url):
    """
    Convert schema URL to path.
    :param url: The target URL.
    :returns: The target path
    """
    if url == '/':
        return ''
    parts = urlsplit(url)
    path = parts.path
    # invenio uses proxy hack to map /api, so need to do it here as well
    if path.startswith('/api/'):
        path = path[4:]
    if path.startswith(blueprint.url_prefix):
        return path[len(blueprint.url_prefix):]
    else:
        raise ValueError('Invalid URL passed.')


def pass_taxonomy(f):
    """Decorate to retrieve a Taxonomy."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop("taxonomy_code")
        try:
            taxonomy = Taxonomy.get(code, required=True)
            return f(taxonomy=taxonomy, *args, **kwargs)
        except NoResultFound:
            abort(404, "Taxonomy does not exist.")

    return decorate


@parser.location_handler("extra_data")
def parse_extra_data(request, name, field):
    if name == 'extra_data':
        extra = {**request.json}
        extra.pop('code', None)
        extra.pop('slug', None)
        return extra


def pass_term(f):
    """Decorate to retrieve a bucket."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop("taxonomy_code")
        path = kwargs.pop("term_path")
        try:
            taxonomy = Taxonomy.get(code)
            term = taxonomy.find_term(path)
        except:
            term = None
            taxonomy = None
        if not term:
            abort(404, "Taxonomy Term does not exist on a specified path.")
        return f(taxonomy=taxonomy, term=term, *args, **kwargs)

    return decorate


def check_permission(permission):
    """
    Check if permission is allowed.
    If permission fails then the connection is aborted.
    :param permission: The permission to check.
    """
    if permission is not None and not permission.can():
        if current_user.is_authenticated:
            abort(403,
                  'You do not have a permission for this action')
        abort(401)


def need_permissions(object_getter, action):
    """
    Get permission for an action or abort.
    :param object_getter: The function used to retrieve the object and pass it
        to the permission factory.
    :param action: The action needed.
    """

    def decorator_builder(f):
        @wraps(f)
        def decorate(*args, **kwargs):
            check_permission(current_permission_factory(
                object_getter(*args, **kwargs),
                action(*args, **kwargs) if callable(action) else action))
            return f(*args, **kwargs)

        return decorate

    return decorator_builder


def need_move_permissions(object_getter, action):
    """Get permission to move a Term if trying to move."""

    def decorator_builder(f):
        @wraps(f)
        def decorate(*args, **kwargs):
            taxonomy, term_path, destination = object_getter(*args, **kwargs)
            if destination:
                try:
                    term = taxonomy.find_term(term_path)
                    check_permission(
                        current_permission_factory(term, action))
                    check_permission(permission_term_create_all)
                except AttributeError:
                    pass
            return f(*args, **kwargs)

        return decorate

    return decorator_builder


def jsonify_taxonomy(t: Taxonomy) -> dict:
    """Prepare Taxonomy to be easily jsonified."""
    return {
        **(t.extra_data or {}),
        "id": t.id,
        "code": t.code,
        "links": {
            "tree": t.link_tree,
            "self": t.link_self
        },
    }


def jsonify_taxonomy_term(t: TaxonomyTerm,
                          taxonomy_code,
                          path: str,
                          parent_path: str = None,
                          parents: List = None) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    if not path.startswith('/'):
        raise Exception()
    result = {
        **(t.extra_data or {}),
        "id": t.id,
        "slug": t.slug,
        "path": path,
        "links": current_flask_taxonomies.term_links(taxonomy_code, path, parent_path),
        "level": t.level - 1
    }

    if parents:
        result['ancestors'] = [*parents]

    descendants_count = (t.right - t.left - 1) / 2
    if descendants_count:
        result["descendants_count"] = descendants_count

    return result


@blueprint.route("/", methods=("GET",))
@permission_taxonomy_read_all.require(http_exception=403)
def taxonomy_list():
    """List all available taxonomies."""
    return jsonify([jsonify_taxonomy(t) for t in current_flask_taxonomies.taxonomy_list()])


@blueprint.route("/", methods=("POST",))
@use_kwargs(
    {
        "code": fields.Str(required=True),
        "extra_data": fields.Dict(location='extra_data')
    }
)
@permission_taxonomy_create_all.require(http_exception=403)
def taxonomy_create(code: str, extra_data: dict = None):
    """Create a new Taxonomy."""
    try:
        created = current_flask_taxonomies.create_taxonomy(code=code, extra_data=extra_data)
        created_dict = jsonify_taxonomy(created)

        response = jsonify(created_dict)
        response.status_code = 201
        response.headers['Location'] = created_dict['links']['self']
        return response
    except IntegrityError:
        raise BadRequest("Taxonomy with this code already exists.")


@blueprint.route("/<string:taxonomy_code>/", methods=("GET",))
@pass_taxonomy
@need_permissions(
    lambda taxonomy: taxonomy,
    'taxonomy-read'
)
@use_kwargs({
    "drilldown": fields.Bool(empty_value=False, location='querystring')
})
def taxonomy_get_roots(taxonomy, drilldown=False):
    """Get top-level terms in a Taxonomy."""
    if not drilldown:
        roots = taxonomy.roots
        return jsonify([
            jsonify_taxonomy_term(t, taxonomy.code, f'/{t.slug}')
            for t in roots])

    ret = build_tree_from_list(taxonomy.code, taxonomy.terms, '')
    return jsonify(ret)


def format_ancestor(item):
    return {
        **(item.extra_data or {}),
        'level': item.level - 1,
        'slug': item.slug
    }


def build_tree_from_list(taxonomy_code, tree_as_list, parent_path=None, parents=None):
    ret = []
    stack = []
    root_level = None

    for item in tree_as_list:
        if root_level is None:
            root_level = item.level

        while item.level - root_level < len(stack):
            stack.pop()

        if not stack:
            if parent_path:
                item_path = f'{parent_path}/{item.slug}'
            else:
                item_path = f'/{item.slug}'
        else:
            item_path = f'{stack[-1]["path"]}/{item.slug}'

        item_json = jsonify_taxonomy_term(
            item, taxonomy_code, item_path,
            parent_path if not stack else None, parents if not stack else None)

        if item.level == root_level:
            # top element in tree_as_list
            ret.append(item_json)
        else:
            # append to parent element
            if 'children' not in stack[-1]:
                stack[-1]['children'] = []
            stack[-1]['children'].append(item_json)

        stack.append(item_json)

    return ret


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("GET",))
@pass_term
@need_permissions(
    lambda taxonomy, term: term,
    'taxonomy-term-read'
)
@use_kwargs({
    "drilldown": fields.Bool(empty_value=False, location='querystring')
})
def taxonomy_get_term(taxonomy, term, drilldown=False):
    """Get Taxonomy Term detail."""
    parents = [format_ancestor(x) for x in term.ancestors]
    if not drilldown:
        return jsonify(
            jsonify_taxonomy_term(term, taxonomy.code, term.tree_path,
                                  term.parent.tree_path or '', parents),
        )
    else:
        return jsonify(
            build_tree_from_list(taxonomy.code,
                                 term.descendants_or_self,
                                 term.parent.tree_path or '', parents)[0])


@blueprint.route("/<string:taxonomy_code>/", methods=("POST",))
@pass_taxonomy
@use_kwargs(
    {
        "slug": fields.Str(required=False),
        "extra_data": fields.Dict(location='extra_data'),
    }
)
@permission_term_create_all.require(http_exception=403)
def taxonomy_create_root_term(taxonomy, slug=None, term_path='', extra_data=None):
    return _taxonomy_create_term_internal(taxonomy=taxonomy, slug=slug,
                                          term_path='', extra_data=extra_data)


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("POST",))
@accept_fallback('content_type')
@pass_taxonomy
@use_kwargs(
    {
        "slug": fields.Str(required=False),
        "extra_data": fields.Dict(location='extra_data'),
    }
)
@permission_term_create_all.require(http_exception=403)
def taxonomy_create_child_term(taxonomy, slug=None, term_path='', extra_data=None):
    return _taxonomy_create_term_internal(taxonomy=taxonomy, slug=slug,
                                          term_path=term_path, extra_data=extra_data)


@taxonomy_create_child_term.support('application/vnd.move')
@pass_taxonomy
@use_kwargs(
    {
        "destination": fields.Str(location='headers', load_from='Destination'),
        "destination_order":
            fields.Str(location='headers', load_from='Destination-Order', default='inside'),
    }
)
@need_move_permissions(
    lambda **kwargs: (kwargs.get('taxonomy'),
                      kwargs.get('term_path'),
                      kwargs.get('destination')),
    'taxonomy-term-move'
)
def taxonomy_move_term(taxonomy, term_path='', destination='', destination_order=''):
    """Create a Term inside a Taxonomy tree."""
    target_path = None
    if not destination:
        abort(400, "No destination given.")

    try:
        target_path = url_to_path(destination)
    except ValueError:
        abort(400, 'Invalid target URL passed.')

    try:
        term, target_taxonomy, target_term = current_flask_taxonomies.move_term(
            taxonomy, term_path, target_path, destination_order)
        moved = jsonify_taxonomy_term(term, target_taxonomy.code, term.tree_path)
        response = jsonify(moved)
        response.headers['Location'] = moved['links']['self']
        return response
    except AttributeError as e:
        abort(400, str(e))
    except NoResultFound:
        abort(400, "Target path not found.")


def _taxonomy_create_term_internal(taxonomy, slug=None,
                                   term_path='', extra_data=None, move_target=None):
    """Create a Term inside a Taxonomy tree."""
    if not slug:
        abort(400, "No slug given for created element.")

    try:
        created = current_flask_taxonomies.create_term(taxonomy=taxonomy,
                                                       term_path=term_path,
                                                       slug=slug,
                                                       extra_data=extra_data)
        created_dict = \
            jsonify_taxonomy_term(created, taxonomy.code, created.tree_path)
        response = jsonify(created_dict)
        response.headers['Location'] = created_dict['links']['self']
        response.status_code = 201
        return response
    except AttributeError as e:
        abort(400, str(e))
    except IntegrityError:
        abort(400, 'Term with this slug already exists on this path.')


@blueprint.route("/<string:taxonomy_code>/", methods=("DELETE",))
@pass_taxonomy
@need_permissions(
    lambda taxonomy: taxonomy,
    'taxonomy-delete'
)
def taxonomy_delete(taxonomy):
    """Delete whole taxonomy tree."""
    try:
        current_flask_taxonomies.delete_taxonomy(taxonomy)
        response = make_response()
        response.status_code = 204
        return response
    except TaxonomyDeleteError as e:
        abort(409, {'reason': str(e), 'records': e.records})


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("DELETE",))  # noqa
@pass_term
@need_permissions(
    lambda taxonomy, term: term,
    'taxonomy-term-delete'
)
def taxonomy_delete_term(taxonomy, term):
    """Delete a Term subtree in a Taxonomy."""
    try:
        current_flask_taxonomies.delete_term(taxonomy, term)
        response = make_response()
        response.status_code = 204
        return response
    except TaxonomyDeleteError as e:
        abort(409, {'reason': str(e), 'records': e.records})


@blueprint.route("/<string:taxonomy_code>/", methods=("PATCH",))
@use_kwargs(
    {"extra_data": fields.Dict(empty_value={}, location='extra_data')}
)
@pass_taxonomy
@need_permissions(
    lambda taxonomy, extra_data: taxonomy,
    'taxonomy-update'
)
def taxonomy_update(taxonomy, extra_data):
    """Update Taxonomy."""
    taxonomy = current_flask_taxonomies.update_taxonomy(taxonomy, extra_data)

    return jsonify(jsonify_taxonomy(taxonomy))


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("PATCH",))  # noqa
@pass_term
@use_kwargs(
    {
        "extra_data": fields.Dict(empty_value={}, location='extra_data'),
    }
)
@need_permissions(
    lambda **kwargs: kwargs.get('term'),
    'taxonomy-term-update'
)
def taxonomy_update_term(taxonomy, term, extra_data=None):
    """Update Term in Taxonomy."""
    changes = {}
    if extra_data:
        changes["extra_data"] = extra_data

    term = current_flask_taxonomies.update_term(taxonomy, term, changes)

    return jsonify(
        jsonify_taxonomy_term(term, taxonomy.code, term.tree_path),
    )
