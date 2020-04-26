from flask import Blueprint, jsonify
from webargs.flaskparser import use_kwargs

from flask_taxonomies.marshmallow import HeaderSchema, QuerySchema
from flask_taxonomies.proxies import current_flask_taxonomies

blueprint = Blueprint('flask_taxonomies', __name__, url_prefix='/api/1.0/taxonomies')


# @parser.location_handler("extra_data")
# def parse_extra_data(request, name, field):
#     if name == 'extra_data':
#         extra = {**request.json}
#         extra.pop('code', None)
#         extra.pop('slug', None)
#         return extra


@blueprint.route('/')
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(QuerySchema, location="query")
def list_taxonomies(prefer=None, include=None, exclude=None, selectors=None):
    prefer = prefer.overwrite(include, exclude, selectors)
    taxonomies = [
        x.json(representation=prefer) for x in current_flask_taxonomies.list_taxonomies()
    ]
    return jsonify(taxonomies)
