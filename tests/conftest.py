import os

import pytest
from flask import Flask
from flask_sqlalchemy import SQLAlchemy

from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.proxies import current_flask_taxonomies


@pytest.fixture
def app():
    app = Flask('__test__')
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    from flask_taxonomies.models import Base
    with app.app_context():
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('TEST_DATABASE_URI', 'sqlite:///test.sqlite3')
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config["SQLALCHEMY_ECHO"] = True
        db = SQLAlchemy(app)
        Base.metadata.create_all(db.engine)
        try:
            yield db
        finally:
            try:
                db.session.commit()
            except:
                pass
            Base.metadata.drop_all(db.engine)
            db.session.commit()


@pytest.fixture
def api(app, db):
    FlaskTaxonomies(app)
    yield current_flask_taxonomies


@pytest.fixture
def test_taxonomy(api):
    return api.create_taxonomy('test')
