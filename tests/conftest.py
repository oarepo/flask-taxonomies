# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""

import pytest
from sqlalchemy_mptt import mptt_sessionmaker
from webtest import TestApp

from examples.app import create_app


@pytest.fixture
def app():
    """Create application for the tests."""
    _app = create_app("tests.settings")
    ctx = _app.test_request_context()
    ctx.push()

    yield _app

    ctx.pop()


@pytest.fixture
def manager(app):
    """Taxonomy Manager fixture."""
    from flask_taxonomies.managers import TaxonomyManager
    return TaxonomyManager


@pytest.fixture
def testapp(app):
    """Create Webtest app."""
    return TestApp(app)


@pytest.fixture
def db(app):
    """Create database for the tests."""
    from flask_taxonomies.db import db as _db
    _db.app = app
    with app.app_context():
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
    from flask_taxonomies.models import Taxonomy as _Taxonomy
    return _Taxonomy


@pytest.fixture
def TaxonomyTerm(db):
    from flask_taxonomies.models import TaxonomyTerm as _TaxonomyTerm
    return _TaxonomyTerm
