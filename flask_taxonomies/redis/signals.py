from flask_taxonomies.models import (
    after_taxonomy_deleted,
    after_taxonomy_jsonresolve,
    after_taxonomy_term_deleted,
    after_taxonomy_term_moved,
    after_taxonomy_term_updated,
    before_taxonomy_jsonresolve,
)
from flask_taxonomies.proxies import current_flask_taxonomies_redis


def cache_after_taxonomy_deleted(taxonomy, **kwargs):
    current_flask_taxonomies_redis.cache.delete_taxonomy(taxonomy.slug)


def cache_after_taxonomy_term_updated(sender, term=None, taxonomy=None, **kwargs):
    current_flask_taxonomies_redis.cache.delete(term.slug)


def cache_after_taxonomy_term_deleted(sender, term=None, taxonomy=None, **kwargs):
    current_flask_taxonomies_redis.cache.delete(term.slug)


def cache_after_taxonomy_term_moved(sender, term=None, taxonomy=None, **kwargs):
    current_flask_taxonomies_redis.cache.delete(term.slug)


def cache_before_taxonomy_jsonresolve(sender, code=None, slug=None, **kwargs):
    return current_flask_taxonomies_redis.cache.get(code + '/' + slug)


def cache_after_taxonomy_jsonresolve(sender, code=None, slug=None, taxonomy_term=None, **kwargs):
    return current_flask_taxonomies_redis.cache.set(code + '/' + slug, taxonomy_term)


# TODO:
# before_taxonomy_marshmallow = taxonomy_signals.signal('before_taxonomy_marshmallow')
# after_taxonomy_marshmallow = taxonomy_signals.signal('after_taxonomy_marshmallow')

def connect_signals():
    after_taxonomy_deleted.connect(cache_after_taxonomy_deleted)
    after_taxonomy_term_updated.connect(cache_after_taxonomy_term_updated)
    after_taxonomy_term_deleted.connect(cache_after_taxonomy_term_deleted)
    after_taxonomy_term_moved.connect(cache_after_taxonomy_term_moved)
    before_taxonomy_jsonresolve.connect(cache_before_taxonomy_jsonresolve)
    after_taxonomy_jsonresolve.connect(cache_after_taxonomy_jsonresolve)


__all__ = ('connect_signals',)
