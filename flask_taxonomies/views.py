# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
from functools import wraps
from urllib.parse import urlsplit

import accept
from flask import (
    Blueprint,
    abort,
    current_app,
    jsonify,
    make_response,
    request,
    url_for,
)
from flask_login import current_user
from invenio_db import db
from slugify import slugify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_mptt import mptt_sessionmaker
from webargs import fields
from webargs.flaskparser import parser, use_kwargs
from werkzeug.exceptions import BadRequest

from flask_taxonomies.models import (
    after_taxonomy_created,
    after_taxonomy_deleted,
    after_taxonomy_term_created,
    after_taxonomy_term_deleted,
    after_taxonomy_term_moved,
    after_taxonomy_term_updated,
    after_taxonomy_updated,
    before_taxonomy_created,
    before_taxonomy_deleted,
    before_taxonomy_term_created,
    before_taxonomy_term_deleted,
    before_taxonomy_term_moved,
    before_taxonomy_term_updated,
    before_taxonomy_updated,
)
from flask_taxonomies.permissions import (
    permission_taxonomy_create_all,
    permission_taxonomy_read_all,
    permission_term_create_all,
)
from flask_taxonomies.proxies import current_permission_factory

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
        abort(400, 'Invalid URL passed.')


def pass_taxonomy(f):
    """Decorate to retrieve a bucket."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop("taxonomy_code")
        try:
            taxonomy = Taxonomy.get(code)
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
        extra.pop('move_target', None)
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
            taxonomy, term_path, move_target = object_getter(*args, **kwargs)
            if move_target:
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
            "self": url_for(
                "taxonomies.taxonomy_get_roots",
                taxonomy_code=t.code,
                _external=True
            )
        },
    }


def jsonify_taxonomy_term(taxonomy_code: str,
                          t: TaxonomyTerm,
                          parent_path: str) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    if not parent_path.endswith('/'):
        parent_path += '/'
    path = parent_path + t.slug
    result = {
        **(t.extra_data or {}),
        "id": t.id,
        "slug": t.slug,
        "path": path,
        "links": {
            "self": url_for(
                "taxonomies.taxonomy_get_term",
                taxonomy_code=taxonomy_code,
                term_path=("".join(path.split("/", 2)[2:])),
                _external=True,
            )
        },
    }
    descendants_count = (t.right - t.left - 1) / 2
    if descendants_count:
        result["descendants_count"] = descendants_count

    return result


@blueprint.route("/", methods=("GET",))
@permission_taxonomy_read_all.require(http_exception=403)
def taxonomy_list():
    """List all available taxonomies."""
    return jsonify([jsonify_taxonomy(t) for t in Taxonomy.taxonomies()])


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
        session = mptt_sessionmaker(db.session)
        before_taxonomy_created.send(current_app._get_current_object(),
                                     code=code, extra_data=extra_data)
        created = Taxonomy.create_taxonomy(code=code, extra_data=extra_data)
        session.add(created)
        session.commit()
        after_taxonomy_created.send(created)
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
def taxonomy_get_roots(taxonomy):
    """Get top-level terms in a Taxonomy."""
    # default for drilldown on taxonomy is False
    accepts = accept.parse(
        request.headers.get("Accept",
                            "application/json; drilldown=false"))
    drilldown = (
            request.args.get('drilldown') or accepts[0].params.get('drilldown')
    )
    do_drilldown = drilldown in {'true', '1'}
    if not do_drilldown:
        roots = taxonomy.roots
        return jsonify([
            jsonify_taxonomy_term(taxonomy.code, t,
                                  f'/{taxonomy.code}/')
            for t in roots])

    ret = build_tree_from_list(taxonomy.code,
                               f'/{taxonomy.code}/',
                               taxonomy.terms)
    return jsonify(ret)


def build_tree_from_list(taxonomy_code, root_path, tree_as_list):
    ret = []
    stack = []
    root_level = None
    for item in tree_as_list:
        if root_level is None:
            root_level = item.level

        while item.level - root_level < len(stack):
            stack.pop()

        item_json = jsonify_taxonomy_term(
            taxonomy_code, item,
            root_path if not stack else stack[-1]['path'])

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
def taxonomy_get_term(taxonomy, term):
    """Get Taxonomy Term detail."""
    # default for drilldown on taxonomy term is True
    accepts = accept.parse(
        request.headers.get("Accept", "application/json; drilldown=true"))
    drilldown = (
            request.args.get('drilldown') or
            accepts[0].params.get('drilldown', 'true')
    )
    do_drilldown = drilldown in {'true', '1'}
    if not do_drilldown:
        return jsonify(
            jsonify_taxonomy_term(taxonomy.code, term, term.parent.tree_path))
    else:
        return jsonify(
            build_tree_from_list(taxonomy.code,
                                 term.parent.tree_path,
                                 term.descendants_or_self)[0])


@blueprint.route("/<string:taxonomy_code>/", methods=("POST",))
@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("POST",))  # noqa
@pass_taxonomy
@use_kwargs(
    {
        "slug": fields.Str(required=False),
        "extra_data": fields.Dict(location='extra_data'),
        "move_target": fields.Str(required=False,
                                  empty_value=None),
    }
)
@permission_term_create_all.require(http_exception=403)
@need_move_permissions(
    lambda **kwargs: (kwargs.get('taxonomy'),
                      kwargs.get('term_path'),
                      kwargs.get('move_target')),
    'taxonomy-term-move'
)
def taxonomy_create_term(taxonomy, slug=None,
                         term_path='', extra_data=None, move_target=None):
    """Create a Term inside a Taxonomy tree."""
    if not move_target and not slug:
        abort(400, "No slug given for created element.")

    term = taxonomy.find_term(term_path)
    if not term:
        abort(400, "Invalid Term path given.")

    full_path = "/{}/{}".format(taxonomy.code, term_path)
    print('Extra', extra_data)
    if taxonomy and term and move_target:
        target_path = url_to_path(move_target)
        before_taxonomy_term_moved.send(term, taxonomy=taxonomy, target_path=target_path)

        if not target_path:
            target_path = f'{taxonomy.code}/'

        try:
            term.move_to(target_path)
        except NoResultFound:
            abort(400, "Target path not found.")
        after_taxonomy_term_moved.send(term, taxonomy=taxonomy)

        moved = jsonify_taxonomy_term(taxonomy.code,
                                      term,
                                      term.parent.tree_path)
        response = jsonify(moved)
        response.headers['Location'] = moved['links']['self']
        return response

    try:
        slug = slugify(slug)
        before_taxonomy_term_created.send(taxonomy, slug=slug, extra_data=extra_data)
        created = TaxonomyTerm(slug=slug, extra_data=extra_data)
        term.append(created)
        session = mptt_sessionmaker(db.session)
        session.add(created)
        session.commit()
        after_taxonomy_term_created.send(term, taxonomy=taxonomy)

        created_dict = \
            jsonify_taxonomy_term(taxonomy.code,
                                  created,
                                  created.parent.tree_path)

        response = jsonify(created_dict)
        response.headers['Location'] = created_dict['links']['self']
        response.status_code = 201
        return response
    except IntegrityError:
        db.session.rollback()
        abort(400, 'Term with this slug already exists on this path.')


@blueprint.route("/<string:taxonomy_code>/", methods=("DELETE",))
@pass_taxonomy
@need_permissions(
    lambda taxonomy: taxonomy,
    'taxonomy-delete'
)
def taxonomy_delete(taxonomy):
    """Delete whole taxonomy tree."""
    session = mptt_sessionmaker(db.session)
    before_taxonomy_deleted.send(taxonomy)
    session.delete(taxonomy)
    session.commit()
    after_taxonomy_deleted.send(taxonomy)
    response = make_response()
    response.status_code = 204
    return response


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("DELETE",))  # noqa
@pass_term
@need_permissions(
    lambda taxonomy, term: term,
    'taxonomy-term-delete'
)
def taxonomy_delete_term(taxonomy, term):
    """Delete a Term subtree in a Taxonomy."""
    session = mptt_sessionmaker(db.session)
    before_taxonomy_term_deleted.send(term, taxonomy=taxonomy)
    session.delete(term)
    session.commit()
    after_taxonomy_term_deleted.send(term, taxonomy=taxonomy)
    response = make_response()
    response.status_code = 204
    return response


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
    before_taxonomy_updated.send(taxonomy, extra_data=extra_data)
    taxonomy.update(extra_data)
    after_taxonomy_updated.send(taxonomy)

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

    before_taxonomy_term_updated.send(term, taxonomy=taxonomy, extra_data=extra_data)
    term.update(**changes)
    after_taxonomy_term_updated.send(term, taxonomy=taxonomy)

    return jsonify(
        jsonify_taxonomy_term(taxonomy.code, term, term.parent.tree_path))
