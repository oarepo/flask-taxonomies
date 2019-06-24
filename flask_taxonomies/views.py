# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
from flask import Blueprint, abort, jsonify
from sqlalchemy import asc
from webargs import fields
from webargs.flaskparser import use_kwargs

from flask_taxonomies.extensions import db
from flask_taxonomies.models import TaxonomyTerm

blueprint = Blueprint("taxonomies", __name__, url_prefix="/taxonomies")


def slug_validator(value: str):
    """Validate if slug exists."""
    tax = TaxonomyTerm.get_by_slug(value)
    if not tax:
        abort(400, "Invalid slug passed: {}".format(value))


def slug_path_validator(value: str):
    """Validate if slug path exists in a tree."""
    slugs = value.split("/")
    for i, slug in enumerate(slugs):
        slug_validator(slug)
        if i > 0:
            parent = TaxonomyTerm.get_by_slug(slugs[i - 1])
            current: TaxonomyTerm = TaxonomyTerm.get_by_slug(slug)
            if not current.parent_id == parent.id:
                abort(400, "Invalid slug path passed: {}".format(value))


def slug_path_parent(value: str) -> TaxonomyTerm:
    """Get TaxonomyTerm instance for last component of slug path."""
    return TaxonomyTerm.get_by_slug(value.split("/")[-1])


def jsonify_taxonomy(t: TaxonomyTerm) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    return {
        "id": t.id,
        "label": str(t),
        "slug": t.slug,
        "title": t.title,
        "description": t.extra_data,
        "path": "/".join([tx.slug for tx in t.path_to_root(order=asc).all()]),
    }


@blueprint.route("/", methods=("GET",))
@blueprint.route("/<string:taxonomy_slug>/", methods=("GET",))
@blueprint.route("/<path:taxonomy_path>/<string:taxonomy_slug>/", methods=("GET",))
def taxonomy_list(taxonomy_id=None, taxonomy_path=None, taxonomy_slug=None):
    """List all available taxonomy trees with a given optional parent slug."""
    tax = None
    result = None

    if taxonomy_slug:
        tax = TaxonomyTerm.get_by_slug(taxonomy_slug)
        if not tax:
            abort(404, "TaxonomyTerm not found.")
        result = []
        tax_tree = tax.drilldown_tree(json=True, json_fields=jsonify_taxonomy)
        return jsonify(tax_tree)
    else:
        result = TaxonomyTerm.query.filter(TaxonomyTerm.parent_id == None).all()  # noqa E711

    return jsonify([jsonify_taxonomy(t) for t in result])


@blueprint.route("/<string:slug>/", methods=("POST",))
@blueprint.route("/<path:attach_to_path>/<string:slug>/", methods=("POST",))
@use_kwargs(
    {
        "title": fields.Str(required=True),
        "description": fields.Str(required=False, empty=""),
        "attach_to": fields.Str(required=False, validate=slug_validator),
    }
)
def taxonomy_create(slug, title, description="", attach_to=None, attach_to_path=None):
    """Create new TaxonomyTerm entry on a specified path, or attach it to a tree."""
    if slug == "move":
        abort(400, "Move is a reserved keyword")

    if TaxonomyTerm.get_by_slug(slug):
        abort(400, "TaxonomyTerm with this slug already exists.")

    taxonomy = TaxonomyTerm(slug=slug, description=description, title=title)

    if attach_to and attach_to_path:
        abort(400, "You cannot use `attach_to` and `slug path` at the same time.")

    if attach_to:
        taxonomy.parent_id = slug_path_parent(attach_to).id
    elif attach_to_path:
        slug_path_validator(attach_to_path)
        taxonomy.parent_id = slug_path_parent(attach_to_path).id

    db.session.add(taxonomy)
    db.session.commit()

    response = jsonify(jsonify_taxonomy(taxonomy))
    response.status_code = 201
    return response


@blueprint.route("/<string:slug>/", methods=("DELETE",))
@blueprint.route("/<path:taxonomy_path>/<string:slug>/", methods=("DELETE",))
def taxonomy_delete(slug, taxonomy_path=None):
    """Delete a TaxonomyTerm entry on a given path."""
    slug_validator(slug)
    if taxonomy_path:
        slug_path_validator(taxonomy_path)

    taxonomy = TaxonomyTerm.get_by_slug(slug)
    db.session.delete(taxonomy)
    db.session.commit()

    response = jsonify()
    response.status_code = 204
    response.headers = []
    return response


@blueprint.route("/<string:slug>/", methods=("PATCH",))
@blueprint.route("/<path:taxonomy_path>/<string:slug>/", methods=("PATCH",))
@use_kwargs(
    {"title": fields.Str(required=False), "description": fields.Str(required=False)}
)
def taxonomy_patch(slug, title=False, description=False, taxonomy_path=None):
    """Update TaxonomyTerm entry on a given path."""
    slug_validator(slug)
    if taxonomy_path:
        slug_path_validator(taxonomy_path)

    taxonomy = TaxonomyTerm.get_by_slug(slug)
    if title:
        taxonomy.title = title
    if description:
        taxonomy.description = description

    db.session.add(taxonomy)
    db.session.commit()

    return jsonify(jsonify_taxonomy(taxonomy))


@blueprint.route("/<string:slug>/move", methods=("POST",))
@blueprint.route("/<path:taxonomy_path>/<string:slug>/move", methods=("POST",))
@use_kwargs({"destination": fields.Str(required=True, validate=slug_validator)})
def taxonomy_move(slug, destination, taxonomy_path=None):
    """Move TaxonomyTerm tree to another tree."""
    slug_validator(slug)
    if taxonomy_path:
        slug_path_validator(taxonomy_path)

    source: TaxonomyTerm = TaxonomyTerm.get_by_slug(slug)
    dest: TaxonomyTerm = TaxonomyTerm.get_by_slug(destination)

    source.move_inside(dest.id)

    db.session.add(source)
    db.session.commit()

    return jsonify(jsonify_taxonomy(source))
