from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from example.import_countries import import_countries
from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.models import Base
from flask_taxonomies.views import blueprint

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.sqlite3'

db = SQLAlchemy(app, model_class=Base)
api = FlaskTaxonomies(app)
migrate = Migrate(app, db)

app.register_blueprint(blueprint, url_prefix=app.config['FLASK_TAXONOMIES_URL_PREFIX'])

with app.app_context():
    import_countries(db)
