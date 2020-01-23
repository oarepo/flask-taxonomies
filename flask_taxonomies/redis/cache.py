import base64
import json

from redis import StrictRedis
from werkzeug.contrib.cache import RedisCache


class JSONRedisCache(RedisCache):

    def dump_object(self, value):
        return json.dumps(value).encode('utf-8')

    def load_object(self, value):
        if value is None:
            return None
        if value.startswith(b'!'):
            return json.loads(super().load_object(value).decode('utf-8'))
        return json.loads(value.decode('utf-8'))


class TaxonomyRedisCache:
    def __init__(self, redis_url, prefix):
        self.cache = JSONRedisCache(
            host=StrictRedis.from_url(redis_url),
            key_prefix=prefix
        )

    def get(self, slug):
        return self.cache.get(self.slug_to_key(slug))

    @staticmethod
    def slug_to_key(slug):
        slug = slug.split('/')
        key = (
                base64.urlsafe_b64encode(slug[0].encode('utf-8')) + b'/' +
                base64.urlsafe_b64encode(slug[-1].encode('utf-8'))
        ).decode('utf-8')
        return key

    @staticmethod
    def taxonomy_key(slug):
        slug = slug.split('/')
        key = (
                base64.urlsafe_b64encode(slug[0].encode('utf-8')) + b'/'
        ).decode('utf-8')
        return key

    def set(self, slug, taxonomy_term_json):
        self.cache.set(self.slug_to_key(slug), taxonomy_term_json)

    def delete(self, slug):
        self.delete_key(self.slug_to_key(slug))

    def delete_key(self, key):
        self.cache.delete(key)

    def delete_taxonomy(self, taxonomy):
        for key in self.cache._client.scan_iter(
                match=self.taxonomy_key(taxonomy) + "*"
        ):
            self.delete_key(key)

    def clear(self):
        self.cache.clear()
