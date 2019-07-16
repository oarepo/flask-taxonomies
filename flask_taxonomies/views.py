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
from sqlalchemy_mptt import mptt_sessionmaker
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import BadRequest
from werkzeug.http import parse_accept_header

from .managers import TaxonomyManager
from .models import Taxonomy, TaxonomyTerm

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
        taxonomy = TaxonomyManager.get_taxonomy(code=code)
        if not taxonomy:
            abort(404, "Taxonomy does not exist.")
        return f(taxonomy=taxonomy, *args, **kwargs)

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
            extra.pop('title')
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
            taxonomy, term = TaxonomyManager.get_from_path("/{}/{}".format(code, path))  # noqa
        except AttributeError:
            term = None
            taxonomy = None

        if not term:
            abort(404, "Taxonomy Term does not exist on a specified path.")
        return f(taxonomy=taxonomy, term=term, *args, **kwargs)

    return decorate


def target_path_validator(value):
    """Validate target path."""
    path = url_to_path(value)
    try:
        TaxonomyManager.get_from_path(path)
    except AttributeError:
        abort(400, "Target Path is invalid.")


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
                          drilldown: bool = False) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    result = {
        **(t.extra_data or {}),
        "id": t.id,
        "slug": t.slug,
        "title": t.title,
        "path": t.tree_path,
        "links": {
            # TODO: replace with Term detail route
            "self": url_for(
                "taxonomies.taxonomy_get_term",
                taxonomy_code=taxonomy_code,
                term_path=("".join(t.tree_path.split("/", 2)[2:])),
                _external=True,
            )
        },
    }
    if drilldown:
        def _term_fields(term: TaxonomyTerm):
            # no drilldown here
            return jsonify_taxonomy_term(taxonomy_code, term)

        # First drilldown tree element is always reference to self -> strip it
        try:
            children = t.drilldown_tree(
                json=True, json_fields=_term_fields)[0]['children']  # noqa
        except KeyError:
            children = []

        result.update({"children": children})
    else:
        descendants_count = (t.right - t.left - 1) / 2
        if descendants_count:
            result["descendants_count"] = descendants_count

    return result


@blueprint.route("/", methods=("GET",))
def taxonomy_list():
    """List all available taxonomies."""
    taxonomies = Taxonomy.query.all()
    return jsonify([jsonify_taxonomy(t) for t in taxonomies])


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
    if TaxonomyManager.get_taxonomy(code):
        raise BadRequest("Taxonomy with this code already exists.")
    else:
        session = mptt_sessionmaker(db.session)
        created = Taxonomy.create(session, code=code, extra_data=extra_data)
        session.commit()

        created_dict = jsonify_taxonomy(created)

        response = jsonify(created_dict)
        response.status_code = 201
        response.headers['Location'] = created_dict['links']['self']
        return response


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
    roots = TaxonomyManager.get_taxonomy_roots(taxonomy)
    do_drilldown = drilldown in {'true', '1'}
    return jsonify([
        jsonify_taxonomy_term(taxonomy.code, t,
                              drilldown=do_drilldown) for t in roots])


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
    return jsonify(
        jsonify_taxonomy_term(taxonomy.code, term, drilldown=do_drilldown))


@blueprint.route("/<string:taxonomy_code>/", methods=("POST",))
@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("POST",))  # noqa
@pass_taxonomy
@pass_term_extra_data
@use_kwargs(
    {
        "title": fields.Dict(required=True),
        "slug": fields.Str(required=True),
        "extra_data": fields.Dict(),
        "move_target": fields.URL(required=False,
                                  empty_value=None,
                                  validate=target_path_validator),
    }
)
def taxonomy_create_term(taxonomy, title, slug,
                         term_path='', extra_data=None, move_target=None):
    """Create a Term inside a Taxonomy tree."""
    term = None
    try:
        _, term = TaxonomyManager.get_from_path(
            "/{}/{}".format(taxonomy.code, term_path))
    except AttributeError:
        abort(400, "Invalid Term path given.")

    full_path = "/{}/{}".format(taxonomy.code, term_path)

    if taxonomy and term and move_target:
        target_path = url_to_path(move_target)
        TaxonomyManager.move_tree(term.tree_path, target_path)
        moved = jsonify_taxonomy_term(taxonomy.code, term, drilldown=True)
        response = jsonify(moved)
        response.headers['Location'] = moved['links']['self']
        return response

    try:
        created = TaxonomyManager.create(slug=slugify(slug),
                                         title=title,
                                         extra_data=extra_data,
                                         path=full_path)

        created_dict = \
            jsonify_taxonomy_term(taxonomy.code, created, drilldown=True)

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
    TaxonomyManager.delete_tree(term.tree_path)
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
        "title": fields.Dict(required=False, empty_value=None),
        "extra_data": fields.Dict(empty_value={}),
    }
)
@pass_term
def taxonomy_update_term(taxonomy, term, title=None, extra_data=None):
    """Update Term in Taxonomy."""
    changes = {}
    if title:
        changes["title"] = title
    if extra_data:
        changes["extra_data"] = extra_data

    term.update(**changes)

    return jsonify(
        jsonify_taxonomy_term(taxonomy.code, term, drilldown=True))
