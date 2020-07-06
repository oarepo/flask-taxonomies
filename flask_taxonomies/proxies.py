from flask import current_app
from werkzeug.local import LocalProxy

if False:
    import flask_taxonomies.api

current_flask_taxonomies = LocalProxy(  # type: flask_taxonomies.api.Api
    lambda: current_app.extensions['flask-taxonomies'])
