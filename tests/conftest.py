import os

import pytest
from flask import Flask, current_app, g
from flask import request as flask_request
from flask_principal import (
    Identity,
    Principal,
    UserNeed,
    identity_changed,
    identity_loaded,
)
from flask_sqlalchemy import SQLAlchemy

from example.import_countries import import_countries
from flask_taxonomies.api import TermIdentification
from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.proxies import current_flask_taxonomies
from flask_taxonomies.views.common import blueprint


class User:
    def __init__(self, username):
        self.username = username


@identity_loaded.connect
def on_identity_loaded(sender, identity):
    g.identity.provides.add(UserNeed(identity.id))


@pytest.fixture(params=[{}])
def app(request):
    app = Flask('__test__')
    app.config.update({
        'PREFERRED_URL_SCHEME': 'http',
        'SERVER_NAME': 'localhost',
        'FLASK_TAXONOMIES_SERVER_SCHEME': 'http',
        'SECRET_KEY': 'test',
        **request.param
    })
    Principal(app)

    # login
    @app.route('/login', methods=['POST'])
    def login():
        username = flask_request.json['username']
        identity_changed.send(app, identity=Identity(username))
        return ''

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
    app.register_blueprint(blueprint, url_prefix=app.config['FLASK_TAXONOMIES_URL_PREFIX'])
    yield current_flask_taxonomies


@pytest.fixture
def test_taxonomy(api):
    return api.create_taxonomy('test')


@pytest.fixture
def client(app, api):
    with app.test_client() as client:
        yield client


@pytest.fixture
def sample_taxonomy(api):
    tax = api.create_taxonomy(code='test', extra_data={
        'title': 'Test taxonomy'
    })
    api.create_term(TermIdentification(taxonomy=tax, slug='b'), extra_data={
        'title': 'B'
    })
    api.create_term(TermIdentification(taxonomy=tax, slug='a'), extra_data={
        'title': 'A'
    })
    api.create_term(TermIdentification(taxonomy=tax, slug='a/aa'), extra_data={
        'title': 'AA'
    })

    return tax


@pytest.fixture
def excluded_title_sample_taxonomy(api):
    tax = api.create_taxonomy(code='test', extra_data={
        'title': 'Test taxonomy'
    }, select=[
    ])
    api.create_term(TermIdentification(taxonomy=tax, slug='b'), extra_data={
        'title': 'B'
    })
    api.create_term(TermIdentification(taxonomy=tax, slug='a'), extra_data={
        'title': 'A'
    })
    api.create_term(TermIdentification(taxonomy=tax, slug='a/aa'), extra_data={
        'title': 'AA'
    })

    return tax


@pytest.fixture
def many_taxonomies(api):
    for t in range(100):
        tax = api.create_taxonomy(code=f'test-{t + 1}', extra_data={
            'title': f'Test taxonomy #{t + 1}'
        })


@pytest.fixture
def country_taxonomy(api, app, db):
    with app.app_context():
        import_countries(db)
