from functools import lru_cache

from werkzeug.utils import import_string

from flask_taxonomies.views.common import json_abort


class OperationPermsEnforcer:
    def __init__(self, factory):
        self.factory = factory

    def enforce(self, status_code=403, **kwargs):
        if not self.factory:
            return True
        permissions = self.factory(**kwargs)
        if not permissions:
            return True
        for perm in permissions:
            if perm.can():
                return True
        json_abort(status_code, {})


class PermsEnforcer:
    def __init__(self, app):
        self.app = app

    @lru_cache(maxsize=23)
    def get_factory(self, operation):
        factories = self.app.config.get('FLASK_TAXONOMIES_PERMISSION_FACTORIES', {})
        ret = factories.get(operation, None)
        if not ret:
            return None
        if isinstance(ret, str):
            ret = import_string(ret)
        if not callable(ret):
            return lambda **kwargs: ret
        return ret

    def __getattr__(self, operation):
        return OperationPermsEnforcer(self.get_factory(operation))
