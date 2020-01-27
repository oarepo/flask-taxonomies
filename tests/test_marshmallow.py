from flask import url_for

from flask_taxonomies.marshmallow import TaxonomySchemaV1
from tests.helpers import marshmallow_load


def test_empty():
    assert marshmallow_load(TaxonomySchemaV1(), {}) == {}


def test_simple():
    value = dict(
        id=1,
        slug='/test',
        path='/abc/def',
        title=[dict(lang='cs', value='titul')],
        tooltip='blah',
        level=1,
        ancestors=[dict(slug='/parent', level=0)]
    )
    assert marshmallow_load(TaxonomySchemaV1(), value) == value


def test_ref(app, db, root_taxonomy):
    t1 = root_taxonomy.create_term(slug="leaf1")
    value = {
        '$ref': "http://localhost/taxonomies/root/leaf1"
    }
    assert marshmallow_load(TaxonomySchemaV1(), value) == value
