from flask import current_app
from werkzeug.local import LocalProxy

current_flask_taxonomies = LocalProxy(  # type: flask_taxonomies.api.Api
    lambda: current_app.extensions['flask-taxonomies'])
