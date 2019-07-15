# -*- coding: utf-8 -*-
"""Taxonomy proxies."""

from flask import current_app
from werkzeug.local import LocalProxy

current_flask_taxonomies = LocalProxy(
    lambda: current_app.extensions['flask-taxonomies'])
"""Helper proxy to access flask taxonomies state object."""

current_permission_factory = LocalProxy(
    lambda: current_flask_taxonomies.permission_factory)
"""Helper proxy to access to the configured permission factory."""
