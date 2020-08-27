class FlaskTaxonomies:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        from flask_taxonomies import api, config
        for k in dir(config):
            if k.startswith('FLASK_TAXONOMIES_'):
                app.config.setdefault(k, getattr(config, k))
        app.extensions['flask-taxonomies'] = api.Api(app)
