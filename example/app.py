import os

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from example.import_countries import import_countries
from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.models import Base
from flask_taxonomies.views import blueprint

app = Flask(__name__)

# app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql+psycopg2://flask_taxonomies:flask_taxonomies@localhost:5433/flask-taxonomies-test'
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', None)
app.config['SERVER_NAME'] = os.environ.get('SERVER_NAME', '127.0.0.1:5000')
app.config['PREFERRED_URL_SCHEME'] = 'http'
app.config["SQLALCHEMY_ECHO"] = True

db = SQLAlchemy(app, model_class=Base)
api = FlaskTaxonomies(app)
migrate = Migrate(app, db)

app.register_blueprint(blueprint, url_prefix=app.config['FLASK_TAXONOMIES_URL_PREFIX'])

with app.app_context():
    import_countries(db)
    print("Import done")
