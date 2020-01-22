import base64
import json

from redis import StrictRedis
from werkzeug.contrib.cache import RedisCache


class TaxonomyRedisCache:
    def __init__(self, redis_url, prefix):
        self.cache = RedisCache(
            host=StrictRedis.from_url(redis_url),
            key_prefix=prefix
        )

    def get(self, slug):
        ret = self.cache.get(self.slug_to_key(slug))
        if ret:
            return json.loads(ret.decode('utf-8'))
        return None

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
        self.cache.set(self.slug_to_key(slug),
                       json.dumps(taxonomy_term_json).encode('utf-8'))

    def delete(self, slug):
        self.delete_key(self.slug_to_key(slug))

    def delete_key(self, key):
        self.cache.delete(key)

    def delete_taxonomy(self, taxonomy):
        for key in self.cache._client.scan_iter(
                match=self.taxonomy_key(taxonomy) + "*"
        ):
            self.delete_key(key)
