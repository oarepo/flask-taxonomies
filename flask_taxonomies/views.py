# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
from functools import wraps
from urllib.parse import urlsplit

import accept
from flask import Blueprint, abort, jsonify, url_for, make_response
from flask import request
from invenio_db import db
from slugify import slugify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy_mptt import mptt_sessionmaker
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import BadRequest

from flask_taxonomies.models import Taxonomy
from .models import TaxonomyTerm

blueprint = Blueprint("taxonomies", __name__, url_prefix="/taxonomies")


def url_to_path(url):
    """
    Convert schema URL to path.
    :param url: The target URL.
    :returns: The target path
    """
    parts = urlsplit(url)
    path = parts.path
    if parts.path.startswith(blueprint.url_prefix):
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


def pass_taxonomy_extra_data(f):
    """Decorate to retrieve extra data for a taxonomy."""

    @wraps(f)
    def decorate(*args, **kwargs):
        extra = {**request.json}
        try:
            extra.pop('code')
        except KeyError:
            pass
        request.json['extra_data'] = extra
        return f(extra_data=extra, *args, **kwargs)

    return decorate


def pass_term_extra_data(f):
    """Decorate to retrieve extra data for a term."""

    @wraps(f)
    def decorate(*args, **kwargs):
        extra = {**request.json}
        try:
            extra.pop('slug')
            extra.pop('move_target')
        except KeyError:
            pass
        request.json['extra_data'] = extra
        return f(extra_data=extra, *args, **kwargs)

    return decorate


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


def jsonify_taxonomy(t: TaxonomyTerm) -> dict:
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
            # TODO: replace with Term detail route
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
def taxonomy_list():
    """List all available taxonomies."""
    return jsonify([jsonify_taxonomy(t) for t in Taxonomy.taxonomies()])


@blueprint.route("/", methods=("POST",))
@pass_taxonomy_extra_data
@use_kwargs(
    {
        "code": fields.Str(required=True),
        "extra_data": fields.Dict()
    }
)
def taxonomy_create(code: str, extra_data: dict = None):
    """Create a new Taxonomy."""
    try:
        session = mptt_sessionmaker(db.session)
        created = Taxonomy.create_taxonomy(code=code, extra_data=extra_data)
        session.add(created)
        session.commit()
        for tax in Taxonomy.taxonomies():
            print(tax.code, tax.parent, tax.tree_id)
        created_dict = jsonify_taxonomy(created)

        response = jsonify(created_dict)
        response.status_code = 201
        response.headers['Location'] = created_dict['links']['self']
        return response
    except IntegrityError:
        raise BadRequest("Taxonomy with this code already exists.")


@blueprint.route("/<string:taxonomy_code>/", methods=("GET",))
@pass_taxonomy
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
@pass_term_extra_data
@use_kwargs(
    {
        "slug": fields.Str(required=False),
        "extra_data": fields.Dict(),
        "move_target": fields.URL(required=False,
                                  empty_value=None),
    }
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

    if taxonomy and term and move_target:
        target_path = url_to_path(move_target)
        try:
            term.move_to(target_path)
        except NoResultFound:
            abort(400, "Target path not found.")

        moved = jsonify_taxonomy_term(taxonomy.code,
                                      term,
                                      term.parent.tree_path)
        response = jsonify(moved)
        response.headers['Location'] = moved['links']['self']
        return response

    try:
        created = TaxonomyTerm(slug=slugify(slug), extra_data=extra_data)
        term.append(created)
        session = mptt_sessionmaker(db.session)
        session.add(created)
        session.commit()

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
def taxonomy_delete(taxonomy):
    """Delete whole taxonomy tree."""
    session = mptt_sessionmaker(db.session)
    session.delete(taxonomy)
    session.commit()
    response = make_response()
    response.status_code = 204
    return response


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("DELETE",))  # noqa
@pass_term
def taxonomy_delete_term(taxonomy, term):
    """Delete a Term subtree in a Taxonomy."""
    session = mptt_sessionmaker(db.session)
    session.delete(term)
    session.commit()
    response = make_response()
    response.status_code = 204
    return response


@blueprint.route("/<string:taxonomy_code>/", methods=("PATCH",))
@pass_taxonomy_extra_data
@use_kwargs(
    {"extra_data": fields.Dict(empty_value={})}
)
@pass_taxonomy
def taxonomy_update(taxonomy, extra_data):
    """Update Taxonomy."""
    taxonomy.update(extra_data)

    return jsonify(jsonify_taxonomy(taxonomy))


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("PATCH",))  # noqa
@pass_term_extra_data
@use_kwargs(
    {
        "extra_data": fields.Dict(empty_value={}),
    }
)
@pass_term
def taxonomy_update_term(taxonomy, term, extra_data=None):
    """Update Term in Taxonomy."""
    changes = {}
    if extra_data:
        changes["extra_data"] = extra_data

    term.update(**changes)

    return jsonify(
        jsonify_taxonomy_term(taxonomy.code, term, term.parent.tree_path))
