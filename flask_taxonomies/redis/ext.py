from six import string_types
from werkzeug.utils import import_string


class FlaskTaxonomiesRedisState:
    def __init__(self, app):
        self.app = app
        self.redis_enabled = not not app.config['TAXONOMY_REDIS_URL']
        if self.redis_enabled:
            handler = app.config['TAXONOMY_REDIS_CACHE_HANDLER']
            if isinstance(handler, string_types):
                self.cache = import_string(handler)(
                    app.config['TAXONOMY_REDIS_URL'],
                    app.config['TAXONOMY_REDIS_PREFIX']
                )
            else:
                self.cache = handler
            from .signals import connect_signals
            connect_signals()

    def clear(self):
        self.cache.clear()


class FlaskTaxonomiesRedis:

    def __init__(self, app=None, db=None):
        """Extension initialization."""
        if app:
            self.init_app(app, db)

    def init_app(self, app, db=None):
        """Flask application initialization."""
        self.init_config(app)

        # Connect signals

        app.extensions['flask-taxonomies-redis'] = FlaskTaxonomiesRedisState(app)

    def init_config(self, app):
        app.config.setdefault('TAXONOMY_REDIS_URL', None)
        app.config.setdefault('TAXONOMY_REDIS_PREFIX', 'taxonomies')
        app.config.setdefault(
            'TAXONOMY_REDIS_CACHE_HANDLER',
            'flask_taxonomies.redis.cache:TaxonomyRedisCache'
        )
