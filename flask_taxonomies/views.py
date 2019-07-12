# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
from functools import wraps

from flask import Blueprint, abort, jsonify, url_for
from invenio_db import db
from slugify import slugify
from sqlalchemy_mptt import mptt_sessionmaker
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import BadRequest

from .managers import TaxonomyManager
from .models import Taxonomy, TaxonomyTerm

blueprint = Blueprint("taxonomies", __name__, url_prefix="/taxonomies")


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


def pass_term(f):
    """Decorate to retrieve a bucket."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop("taxonomy_code")
        path = kwargs.pop("term_path")
        try:
            _, term = TaxonomyManager.get_from_path("/{}/{}".format(code, path))  # noqa
        except AttributeError:
            term = None

        if not term:
            abort(404, "Taxonomy Term does not exist on a specified path.")
        return f(term=term, *args, **kwargs)

    return decorate


def target_path_validator(value: str):
    """Validate target path."""
    tax = None
    try:
        tax, term = TaxonomyManager.get_from_path(value)
    except AttributeError:
        abort(400, "Target Path is invalid.")


def jsonify_taxonomy(t: Taxonomy) -> dict:
    """Prepare Taxonomy to be easily jsonified."""
    return {
        "id": t.id,
        "code": t.code,
        "extra_data": t.extra_data,
        "links": {
            "self": url_for(
                "taxonomies.taxonomy_get_roots",
                taxonomy_code=t.code,
                _external=True
            )
        },
    }


def jsonify_taxonomy_term(t: TaxonomyTerm, drilldown: bool = False) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    result = {
        "id": t.id,
        "slug": t.slug,
        "title": t.title,
        "extra_data": t.extra_data,
        "path": t.tree_path,
        "links": {
            # TODO: replace with Term detail route
            "self": url_for(
                "taxonomies.taxonomy_get_term",
                taxonomy_code=t.taxonomy.code,
                term_path=("".join(t.tree_path.split("/", 2)[2:])),
                _external=True,
            )
        },
    }
    if drilldown:
        def _term_fields(term: TaxonomyTerm):
            return dict(slug=term.slug, path=term.tree_path)

        result.update(
            {"children": t.drilldown_tree(json=True, json_fields=_term_fields)}
        )

    return result


@blueprint.route("/", methods=("GET",))
def taxonomy_list():
    """List all available taxonomies."""
    taxonomies = Taxonomy.query.all()
    return jsonify([jsonify_taxonomy(t) for t in taxonomies])


@blueprint.route("/", methods=("POST",))
@use_kwargs(
    {
        "code": fields.Str(required=True),
        "extra_data": fields.Dict(required=False, empty_value=None),
    }
)
def taxonomy_create(code: str, extra_data: dict = None):
    """Create a new Taxonomy."""
    if TaxonomyManager.get_taxonomy(code):
        raise BadRequest("Taxonomy with this code already exists.")
    else:
        created = Taxonomy(code=code, extra_data=extra_data)

        session = mptt_sessionmaker(db.session)
        session.add(created)
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
    roots = TaxonomyManager.get_taxonomy_roots(taxonomy)
    return jsonify([jsonify_taxonomy_term(t) for t in roots])


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("GET",))
@pass_term
def taxonomy_get_term(term):
    """Get Taxonomy Term detail."""
    return jsonify(jsonify_taxonomy_term(term, drilldown=True))


@blueprint.route("/<string:taxonomy_code>/", methods=("POST",))
@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("POST",))  # noqa
@pass_taxonomy
@use_kwargs(
    {
        "title": fields.Dict(required=True),
        "slug": fields.Str(required=True),
        "extra_data": fields.Dict(required=False, empty_value=None),
        "move_target": fields.Str(required=False,
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
        TaxonomyManager.move_tree(term.tree_path, move_target)
        moved = jsonify_taxonomy_term(term, drilldown=True)
        response = jsonify(moved)
        response.headers['Location'] = moved['links']['self']
        return response

    try:
        created = TaxonomyManager.create(slug=slugify(slug),
                                         title=title,
                                         extra_data=extra_data,
                                         path=full_path)
    except ValueError:
        abort(400, 'Term with this slug already exists on this path.')

    created_dict = jsonify_taxonomy_term(created, drilldown=True)

    response = jsonify(created_dict)
    response.headers['Location'] = created_dict['links']['self']
    response.status_code = 201
    return response


@blueprint.route("/<string:taxonomy_code>/", methods=("DELETE",))
@pass_taxonomy
def taxonomy_delete(taxonomy):
    """Delete whole taxonomy tree."""
    session = mptt_sessionmaker(db.session)
    session.delete(taxonomy)
    session.commit()
    response = jsonify()
    response.status_code = 204
    response.headers = []
    return response


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("DELETE",))  # noqa
@pass_term
def taxonomy_delete_term(term):
    """Delete a Term subtree in a Taxonomy."""
    TaxonomyManager.delete_tree(term.tree_path)
    response = jsonify()
    response.status_code = 204
    response.headers = []
    return response


@blueprint.route("/<string:taxonomy_code>/", methods=("PATCH",))
@use_kwargs(
    {"extra_data": fields.Dict(required=True, empty_value=None)}
)
@pass_taxonomy
def taxonomy_update(taxonomy, extra_data):
    """Update Taxonomy."""
    taxonomy.update(extra_data)

    return jsonify(jsonify_taxonomy(taxonomy))


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("PATCH",))  # noqa
@use_kwargs(
    {
        "title": fields.Dict(required=False, empty_value=None),
        "extra_data": fields.Dict(required=False, empty_value=None),
    }
)
@pass_term
def taxonomy_update_term(term, title=None, extra_data=None):
    """Update Term in Taxonomy."""
    changes = {}
    if title:
        changes.update({"title": title})
    if extra_data:
        changes.update({"extra_data": extra_data})

    term.update(**changes)

    return jsonify(jsonify_taxonomy_term(term, drilldown=True))
