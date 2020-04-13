from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

from flask_taxonomies.models import Base

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.sqlite3'

db = SQLAlchemy(app, model_class=Base)
migrate = Migrate(app, db)
