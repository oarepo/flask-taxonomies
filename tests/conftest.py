# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""
import os

import pytest
from flask import Flask
from invenio_access import ActionUsers, InvenioAccess
from invenio_accounts import InvenioAccounts
from invenio_accounts.testutils import create_test_user
from invenio_db import InvenioDB
from invenio_db import db as _db
from sqlalchemy_mptt import mptt_sessionmaker
from sqlalchemy_utils import create_database, database_exists

from flask_taxonomies.ext import FlaskTaxonomies
from flask_taxonomies.permissions import (
    taxonomy_create_all,
    taxonomy_delete_all,
    taxonomy_read_all,
    taxonomy_term_create_all,
    taxonomy_term_delete_all,
    taxonomy_term_move_all,
    taxonomy_term_read_all,
    taxonomy_term_update_all,
    taxonomy_update_all,
)
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
    InvenioAccounts(app_)
    InvenioAccess(app_)

    return app_


@pytest.fixture()
def app(base_app):
    """Flask application fixture."""
    FlaskTaxonomies(base_app)
    base_app.register_blueprint(blueprint)

    with base_app.app_context():
        return base_app


@pytest.fixture()
def users_data(db):
    """User data fixture."""
    return [
        dict(email='user1@inveniosoftware.org', password='pass1'),
        dict(email='user2@inveniosoftware.org', password='pass1'),
    ]


@pytest.fixture()
def users(db, users_data):
    """Create test users."""
    return [
        create_test_user(active=True, **users_data[0]),
        create_test_user(active=True, **users_data[1]),
    ]


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
    from flask_taxonomies.models import Taxonomy
    root = Taxonomy(code="root")

    session = mptt_sessionmaker(db.session)
    session.add(root)
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


@pytest.yield_fixture()
def permissions(db, root_taxonomy):
    """Permission for users."""
    users = {
        None: None,
    }

    for user in ['taxonomies', 'terms', 'noperms', 'root-taxo']:
        users[user] = create_test_user(
            email='{0}@invenio-software.org'.format(user),
            password='pass1',
            active=True
        )

    taxonomy_perms = [
        taxonomy_create_all,
        taxonomy_update_all,
        taxonomy_read_all,
        taxonomy_delete_all
    ]

    taxonomy_term_perms = [
        taxonomy_term_create_all,
        taxonomy_term_update_all,
        taxonomy_term_read_all,
        taxonomy_term_delete_all,
        taxonomy_term_move_all
    ]

    for perm in taxonomy_perms:
        db.session.add(ActionUsers(
            action=perm.value,
            user=users['taxonomies']))
        db.session.add(ActionUsers(
            action=perm.value,
            argument=str(root_taxonomy.code),
            user=users['root-taxo']))
    for perm in taxonomy_term_perms:
        db.session.add(ActionUsers(
            action=perm.value,
            user=users['terms']))

    db.session.commit()

    yield users
