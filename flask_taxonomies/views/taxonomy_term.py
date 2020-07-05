import json
import traceback
from urllib.parse import urljoin, urlparse

import sqlalchemy
from flask import jsonify, abort, request, Response, current_app
from sqlalchemy.orm.exc import NoResultFound
from webargs.flaskparser import use_kwargs

from flask_taxonomies.api import TermIdentification
from flask_taxonomies.constants import INCLUDE_DESCENDANTS, INCLUDE_DELETED, INCLUDE_SELF
from flask_taxonomies.marshmallow import HeaderSchema, PaginatedQuerySchema, MoveHeaderSchema
from flask_taxonomies.models import TaxonomyTerm, TermStatusEnum
from flask_taxonomies.proxies import current_flask_taxonomies
from flask_taxonomies.routing import accept_fallback
from .common import blueprint, with_prefer, build_descendants, json_abort
from .paginator import Paginator


@blueprint.route('/<code>/<path:slug>', strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def get_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None, status_code=200):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        prefer = taxonomy.merge_select(prefer)

        if INCLUDE_DELETED in prefer:
            status_cond = sqlalchemy.sql.true()
        else:
            status_cond = TaxonomyTerm.status == TermStatusEnum.alive

        return_descendants = INCLUDE_DESCENDANTS in prefer

        if return_descendants:
            query = current_flask_taxonomies.descendants_or_self(
                TermIdentification(taxonomy=code, slug=slug),
                levels=prefer.options.get('levels', None),
                status_cond=status_cond
            )
        else:
            query = current_flask_taxonomies.filter_term(
                TermIdentification(taxonomy=code, slug=slug),
                status_cond=status_cond
            )

        paginator = Paginator(
            prefer,
            query, page if return_descendants else None,
            size if return_descendants else None,
            json_converter=lambda data:
            build_descendants(data, prefer, root_slug=None),
            allow_empty=INCLUDE_SELF not in prefer, single_result=INCLUDE_SELF in prefer
        )

        return paginator.jsonify(status_code=status_code)

    except NoResultFound:
        term = current_flask_taxonomies.filter_term(
            TermIdentification(taxonomy=code, slug=slug),
            status_cond=sqlalchemy.sql.true()
        ).one_or_none()
        if not term:
            json_abort(404, {
                "message": "%s was not found on the server" % request.url,
                "reason": "does-not-exist"
            })
        elif term.obsoleted_by_id:
            obsoleted_by = term.obsoleted_by
            obsoleted_by_links = obsoleted_by.links()
            return Response(json.dumps({
                'links': obsoleted_by_links.envelope,
                'status': term.status.name
            }), status=301, headers={
                'Location': obsoleted_by_links.headers['self']
            }, content_type='application/json')
        else:
            json_abort(410, {
                "message": "%s was not found on the server" % request.url,
                "reason": "deleted"
            })
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>/<path:slug>', methods=['PUT'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_update_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None):
    return _create_update_taxonomy_term_internal(code, slug, prefer, page, size, request.json)


def _create_update_taxonomy_term_internal(code, slug, prefer, page, size, extra_data):
    try:
        taxonomy = current_flask_taxonomies.get_taxonomy(code)
        prefer = taxonomy.merge_select(prefer)

        if INCLUDE_DELETED in prefer:
            status_cond = sqlalchemy.sql.true()
        else:
            status_cond = TaxonomyTerm.status == TermStatusEnum.alive

        ti = TermIdentification(taxonomy=code, slug=slug)
        term = current_flask_taxonomies.filter_term(ti, status_cond=status_cond).one_or_none()

        if term:
            current_flask_taxonomies.update_term(
                term,
                status_cond=status_cond,
                extra_data=extra_data
            )
            status_code = 200
        else:
            current_flask_taxonomies.create_term(
                ti,
                extra_data=extra_data
            )
            status_code = 201

        return get_taxonomy_term(code=code, slug=slug, prefer=prefer, page=page, size=size, status_code=status_code)

    except NoResultFound:
        abort(404)
    except:
        traceback.print_exc()
        raise


@blueprint.route('/<code>/<path:slug>', methods=['POST'], strict_slashes=False)
@accept_fallback('content_type')
@use_kwargs(MoveHeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_taxonomy_term_post(code=None, slug=None, prefer=None, page=None, size=None):
    extra_data = {**request.json}
    if 'slug' not in extra_data:
        return Response('slug missing in payload', status=400)
    _slug = extra_data.pop('slug')
    return _create_update_taxonomy_term_internal(code, slug + '/' + _slug, prefer, page, size, extra_data)


@blueprint.route('/<code>', methods=['POST'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def create_taxonomy_term_post_on_root(code=None, slug=None, prefer=None, page=None, size=None):
    extra_data = {**request.json}
    if 'slug' not in extra_data:
        return Response('slug missing in payload', status=400)
    _slug = extra_data.pop('slug')
    return _create_update_taxonomy_term_internal(code, urljoin(slug, _slug), prefer, page, size, extra_data)


@blueprint.route('/<code>/<path:slug>', methods=['PATCH'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def patch_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None):
    taxonomy = current_flask_taxonomies.get_taxonomy(code)
    if not taxonomy:
        abort(404)
    prefer = taxonomy.merge_select(prefer)

    if INCLUDE_DELETED in prefer:
        status_cond = sqlalchemy.sql.true()
    else:
        status_cond = TaxonomyTerm.status == TermStatusEnum.alive

    ti = TermIdentification(taxonomy=code, slug=slug)
    term = current_flask_taxonomies.filter_term(ti, status_cond=status_cond).one_or_none()

    if not term:
        abort(404)

    current_flask_taxonomies.update_term(
        term,
        status_cond=status_cond,
        extra_data=request.json,
        patch=True,
        status=TermStatusEnum.alive  # make it alive if it  was deleted
    )

    return get_taxonomy_term(code=code, slug=slug, prefer=prefer, page=page, size=size)


@blueprint.route('/<code>/<path:slug>', methods=['DELETE'], strict_slashes=False)
@use_kwargs(HeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def delete_taxonomy_term(code=None, slug=None, prefer=None, page=None, size=None):
    try:
        term = current_flask_taxonomies.delete_term(TermIdentification(taxonomy=code, slug=slug),
                                                    remove_after_delete=False)
    except NoResultFound as e:
        return Response(str(e), status=404)
    return jsonify(term.json(representation=prefer))


@create_taxonomy_term_post.support('application/vnd.move')
@use_kwargs(MoveHeaderSchema, location="headers")
@use_kwargs(PaginatedQuerySchema, location="query")
@with_prefer
def taxonomy_move_term(code=None, slug=None, prefer=None, page=None, size=None, destination='', rename=''):
    """Move term into a new parent or rename it."""

    if destination:
        if destination.startswith('http'):
            destination_path = urlparse(destination).path
            url_prefix = current_app.config['FLASK_TAXONOMIES_URL_PREFIX']
            if not destination_path.startswith(url_prefix):
                abort(400,
                      'Destination not part of this server as it '
                      'does not start with config.FLASK_TAXONOMIES_URL_PREFIX')
            destination_path = destination_path[len(url_prefix):]
            destination_path = destination_path.split('/', maxsplit=1)
            if len(destination_path) > 1:
                destination_taxonomy, destination_slug = destination_path
            else:
                destination_taxonomy = destination_path[0]
                destination_slug = None
        else:
            destination_taxonomy = code
            destination_slug = destination
            if destination_slug.startswith('/'):
                destination_slug = destination_slug[1:]
        if not current_flask_taxonomies.filter_term(TermIdentification(taxonomy=code, slug=slug)).count():
            abort(404, 'Term %s/%s does not exist' % (code, slug))

        old_term, new_term = current_flask_taxonomies.move_term(
            TermIdentification(taxonomy=code, slug=slug),
            new_parent=TermIdentification(taxonomy=destination_taxonomy,
                                          slug=destination_slug) if destination_slug else '',
            remove_after_delete=False)  # do not remove the original node from the database, just mark it as deleted
    elif rename:
        new_slug = slug
        if new_slug.endswith('/'):
            new_slug = new_slug[:-1]
        if '/' in new_slug:
            new_slug = new_slug.rsplit('/')[0]
            new_slug = new_slug + '/' + rename
        else:
            new_slug = rename
        old_term, new_term = current_flask_taxonomies.rename_term(
            TermIdentification(taxonomy=code, slug=slug),
            new_slug=new_slug,
            remove_after_delete=True)
        destination_taxonomy = code
    else:
        abort(400, 'Pass either `destination` or `rename` parameters ')
        return  # just to make pycharm happy

    return get_taxonomy_term(code=destination_taxonomy, slug=new_term.slug,
                             prefer=prefer, page=page, size=size)
