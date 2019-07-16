# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
import os

import pytest
from flask import Flask
from invenio_db import InvenioDB
from invenio_db import db as _db
from sqlalchemy_mptt import mptt_sessionmaker
from sqlalchemy_utils import create_database, database_exists

from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.views import blueprint


@pytest.fixture()
def base_app():
    """Flask application fixture."""
    app_ = Flask('testapp')
    app_.config.update(
        TESTING=True,
        SQLALCHEMY_TRACK_MODIFICATIONS=True,
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            'SQLALCHEMY_DATABASE_URI',
            'sqlite:///:memory:'),
        SERVER_NAME='localhost',
        SECURITY_PASSWORD_SALT='TEST_SECURITY_PASSWORD_SALT',
        SECRET_KEY='TEST_SECRET_KEY',
        FILES_REST_MULTIPART_CHUNKSIZE_MIN=2,
        FILES_REST_MULTIPART_CHUNKSIZE_MAX=20,
        FILES_REST_MULTIPART_MAX_PARTS=100,
        FILES_REST_TASK_WAIT_INTERVAL=0.1,
        FILES_REST_TASK_WAIT_MAX_SECONDS=1,
    )

    InvenioDB(app_)

    return app_


@pytest.fixture()
def app(base_app):
    """Flask application fixture."""
    FlaskTaxonomies(base_app)
    base_app.register_blueprint(blueprint)

    with base_app.app_context():
        return base_app


@pytest.fixture
def manager(app):
    """Taxonomy Manager fixture."""
    from flask_taxonomies.managers import TaxonomyManager
    return TaxonomyManager


@pytest.yield_fixture()
def client(app):
    """Get test client."""
    with app.test_client() as client:
        yield client


@pytest.fixture
def db(app):
    """Create database for the tests."""
    with app.app_context():
        if not database_exists(str(_db.engine.url)) and \
                app.config['SQLALCHEMY_DATABASE_URI'] != 'sqlite://':
            create_database(_db.engine.url)
        _db.create_all()

    yield _db

    # Explicitly close DB connection
    _db.session.close()
    _db.drop_all()


@pytest.fixture
def root_taxonomy(db):
    """Create root taxonomy element."""
    from flask_taxonomies.models import Taxonomy, TaxonomyTerm
    session = mptt_sessionmaker(db.session)
    root = Taxonomy.create(session, code="root")
    session.commit()
    return root


@pytest.fixture
def Taxonomy(db):
    """Taxonomy fixture."""
    from flask_taxonomies.models import Taxonomy as _Taxonomy
    return _Taxonomy


@pytest.fixture
def TaxonomyTerm(db):
    """Taxonomy Term fixture."""
    from flask_taxonomies.models import TaxonomyTerm as _TaxonomyTerm
    return _TaxonomyTerm


@pytest.fixture
def filled_taxonomy(request, db, root_taxonomy, TaxonomyTerm):
    def _generate(parent, lengths, prefix, separator):
        if not lengths:
            return
        session = mptt_sessionmaker(db.session)
        for i in range(1, 1 + lengths[0]):
            title = f'{prefix}{i}'
            t = TaxonomyTerm(slug=title, title={'en': title}, parent=parent)
            session.add(t)
            session.commit()
            _generate(t, lengths[1:], prefix + separator, separator)

    _generate(root_taxonomy.root, request.param, 'node-', '-')
    return root_taxonomy
