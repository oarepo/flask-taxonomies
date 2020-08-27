import os

import sqlalchemy
from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from example.import_countries import import_countries
from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.models import Base, TaxonomyTerm
from flask_taxonomies.proxies import current_flask_taxonomies
from flask_taxonomies.signals import before_taxonomy_term_deleted, before_taxonomy_term_moved, after_taxonomy_term_moved
from flask_taxonomies.views import blueprint

app = Flask(__name__)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://flask_taxonomies:flask_taxonomies@localhost:5433/flask-taxonomies-test'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', "sqlite:///:memory:")
app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', '127.0.0.1:5000')
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config["SQLALCHEMY_ECHO"] = True

db = SQLAlchemy(app, model_class=Base)
api = FlaskTaxonomies(app)
migrate = Migrate(app, db)

app.register_blueprint(blueprint, url_prefix=app.config['FLASK_TAXONOMIES_URL_PREFIX'])


def long_running_delete_action(sender, term=None, **kwargs):
    # increase the busy count, thus preventing deletion. Later, an asynchronous process would
    # call unmark_busy ...
    current_flask_taxonomies.mark_busy([term.id])


def long_running_move_action(sender, term=None, new_term=None, **kwargs):
    # lock both the old and new terms so that they can not be manipulated.
    # start a background process to replace the term in referencing documents.
    current_flask_taxonomies.mark_busy([
        x[0] for x in current_flask_taxonomies.descendants_or_self(term, status_cond=sqlalchemy.sql.true()).values(TaxonomyTerm.id)
    ])
    current_flask_taxonomies.mark_busy([
        x[0] for x in current_flask_taxonomies.descendants_or_self(new_term, status_cond=sqlalchemy.sql.true()).values(TaxonomyTerm.id)
    ])


before_taxonomy_term_deleted.connect(long_running_delete_action)
after_taxonomy_term_moved.connect(long_running_move_action)

with app.app_context():
    import_countries(db)
    print("Import done")
