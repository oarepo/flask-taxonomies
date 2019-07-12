# -*- coding: utf-8 -*-
"""Extensions module. Each extension is initialized in the app factory located in app.py."""
from flask_alembic import Alembic
from flask_caching import Cache
from flask_debugtoolbar import DebugToolbarExtension
from flask_sqlalchemy import SQLAlchemy

from flask_taxonomies.ext import FlaskTaxonomies

db = SQLAlchemy()
alembic = Alembic()
cache = Cache()
debug_toolbar = DebugToolbarExtension()
taxonomies = FlaskTaxonomies()
