# -*- coding: utf-8 -*-
"""TaxonomyTerm views."""
import json
from functools import wraps
from json import JSONDecodeError

from flask import Blueprint, abort, jsonify, url_for
from webargs import fields
from webargs.flaskparser import use_kwargs
from werkzeug.exceptions import BadRequest

from flask_taxonomies.extensions import db
from flask_taxonomies.managers import TaxonomyManager
from flask_taxonomies.models import TaxonomyTerm, Taxonomy

blueprint = Blueprint('taxonomies', __name__, url_prefix='/taxonomies')


def pass_taxonomy(f):
    """Decorate to retrieve a bucket."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop('taxonomy_code')
        taxonomy = TaxonomyManager.get_taxonomy(code=code)
        if not taxonomy:
            abort(404, 'Taxonomy does not exist.')
        return f(taxonomy=taxonomy, *args, **kwargs)

    return decorate


def pass_term(f):
    """Decorate to retrieve a bucket."""

    @wraps(f)
    def decorate(*args, **kwargs):
        code = kwargs.pop('taxonomy_code')
        path = kwargs.pop('term_path')
        try:
            _, term = TaxonomyManager.get_from_path('/{}/{}'.format(code, path))
        except AttributeError:
            term = None

        if not term:
            abort(404, 'Taxonomy Term does not exist on a specified path.')
        return f(term=term, *args, **kwargs)

    return decorate


def json_validator(value: str):
    try:
        json.loads(value)
    except JSONDecodeError as e:
        return abort(400, 'Invalid JSON: {}'.format(e))


def slug_validator(value: str):
    """Validate if slug exists."""
    tax = TaxonomyTerm.get_by_slug(value)
    if not tax:
        abort(400, 'Invalid slug passed: {}'.format(value))


def jsonify_taxonomy(t: Taxonomy) -> dict:
    """Prepare Taxonomy to be easily jsonified."""
    return {
        'id': t.id,
        'code': t.code,
        'extra_data': t.extra_data,
    }


def jsonify_taxonomy_term(t: TaxonomyTerm, drilldown: bool = False) -> dict:
    """Prepare TaxonomyTerm to be easily jsonified."""
    result = {
        'id': t.id,
        'slug': t.slug,
        'title': t.title,
        'extra_data': t.extra_data,
        'path': t.tree_path,
        'links': {
            # TODO: replace with Term detail route
            'self': url_for('taxonomies.taxonomy_get_term',
                            taxonomy_code=t.taxonomy.code,
                            term_path=(''.join(t.tree_path.split('/', 2)[2:])),
                            _external=True)
        }
    }
    if drilldown:
        def _term_fields(term: TaxonomyTerm):
            return dict(slug=term.slug, path=term.tree_path)

        result.update({'children': t.drilldown_tree(json=True, json_fields=_term_fields)})

    return result


@blueprint.route('/', methods=('GET',))
def taxonomy_list():
    taxonomies = Taxonomy.query.all()
    return jsonify([jsonify_taxonomy(t) for t in taxonomies])


@blueprint.route('/', methods=('POST',))
@use_kwargs(
    {
        'code': fields.Str(required=True),
        'extra_data': fields.Str(required=False, empty_value='', validate=json_validator),
    }
)
def taxonomy_create(code: str, extra_data: dict = None):
    if TaxonomyManager.get_taxonomy(code):
        raise BadRequest('Taxonomy with this code already exists.')
    else:
        t = Taxonomy(code=code, extra_data=json.loads(extra_data))
        db.session.add(t)
        db.session.commit()
        response = jsonify(jsonify_taxonomy(t))
        response.status_code = 201
        return response


@blueprint.route("/<string:taxonomy_code>/", methods=("GET",))
@pass_taxonomy
def taxonomy_get_roots(taxonomy):
    roots = TaxonomyManager.get_taxonomy_roots(taxonomy)
    return jsonify([jsonify_taxonomy_term(t) for t in roots])


@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("GET",))
@pass_term
def taxonomy_get_term(term):
    return jsonify(jsonify_taxonomy_term(term, drilldown=True))

@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("POST",))
@use_kwargs(
    {
        'title': fields.Str(required=True, validate=json_validator),
        'extra_data': fields.Str(required=False, empty_value='', validate=json_validator),
    }
)
def taxonomy_create_term(taxonomy_code, term_path, title, extra_data = None):
    taxonomy = None
    term = None
    try:
        taxonomy, term = TaxonomyManager.get_from_path('/{}/{}'.format(taxonomy_code, term_path))
    except AttributeError:
        taxonomy = TaxonomyManager.get_taxonomy(taxonomy_code)

    if not taxonomy:
        abort(404, 'Taxonomy does not exist, create it first.')
    if term:
        abort(400, 'Term already exists on a path specified.')

    path, slug = '/{}'.format(term_path).rstrip('/').rsplit('/', 1)
    full_path = '/{}{}'.format(taxonomy.code, path)

    try:
        title = json.loads(title)
        created = TaxonomyManager.create(slug=slug, title=title, extra_data=extra_data, path='{}'.format(full_path))
        response = jsonify(jsonify_taxonomy_term(created, drilldown=True))
        response.status_code = 201
        return response
    except AttributeError:
        abort(400, 'Invalid Taxonomy Term path provided.')

@blueprint.route("/<string:taxonomy_code>/", methods=("DELETE",))
@pass_taxonomy
def taxonomy_delete(taxonomy):
    db.session.delete(taxonomy)
    db.session.commit()
    response = jsonify()
    response.status_code = 204
    response.headers = []
    return response

@blueprint.route("/<string:taxonomy_code>/<path:term_path>/", methods=("DELETE",))
@pass_term
def taxonomy_delete_term(term):
    TaxonomyManager.delete_tree(term.tree_path)
    response = jsonify()
    response.status_code = 204
    response.headers = []
    return response
#
# @blueprint.route("/<string:slug>/", methods=("PATCH",))
# @blueprint.route("/<path:taxonomy_path>/<string:slug>/", methods=("PATCH",))
# @use_kwargs(
#     {"title": fields.Str(required=False), "description": fields.Str(required=False)}
# )
# def taxonomy_patch(slug, title=False, description=False, taxonomy_path=None):
#     """Update TaxonomyTerm entry on a given path."""
#     slug_validator(slug)
#     if taxonomy_path:
#         slug_path_validator(taxonomy_path)
#
#     taxonomy = TaxonomyTerm.get_by_slug(slug)
#     if title:
#         taxonomy.title = title
#     if description:
#         taxonomy.description = description
#
#     db.session.add(taxonomy)
#     db.session.commit()
#
#     return jsonify(jsonify_taxonomy(taxonomy))
#
#
# @blueprint.route("/<string:slug>/move", methods=("POST",))
# @blueprint.route("/<path:taxonomy_path>/<string:slug>/move", methods=("POST",))
# @use_kwargs({"destination": fields.Str(required=True, validate=slug_validator)})
# def taxonomy_move(slug, destination, taxonomy_path=None):
#     """Move TaxonomyTerm tree to another tree."""
#     slug_validator(slug)
#     if taxonomy_path:
#         slug_path_validator(taxonomy_path)
#
#     source: TaxonomyTerm = TaxonomyTerm.get_by_slug(slug)
#     dest: TaxonomyTerm = TaxonomyTerm.get_by_slug(destination)
#
#     source.move_inside(dest.id)
#
#     db.session.add(source)
#     db.session.commit()
#
#     return jsonify(jsonify_taxonomy(source))
