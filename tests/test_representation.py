from flask import current_app

from flask_taxonomies.constants import INCLUDE_ID
from flask_taxonomies.models import Representation
from flask_taxonomies.marshmallow import PreferHeaderField


def representation_model_test(api):
    repr = Representation('representation')
    default_includes = current_app.config['FLASK_TAXONOMIES_REPRESENTATION']['representation']['include']
    assert repr.include == set(default_includes)
    assert repr.exclude == set()
    assert repr.selectors is None

    repr1 = repr.copy()
    assert repr1 is not repr
    assert repr1.include is not repr.include
    assert repr1.exclude is not repr.exclude

    repr1 = repr.extend(include={INCLUDE_ID})
    assert repr != repr1

    assert repr1.include == repr.include | {INCLUDE_ID}
    assert INCLUDE_ID in repr1
    assert INCLUDE_ID not in repr

    repr1 = repr.extend(exclude = default_includes, selectors=['/a', '/b'])
    for i in default_includes:
        assert i in repr1.include
        assert i not in repr1

    assert repr1.selectors == {'/a', '/b'}
    repr2 = repr1.extend(selectors=['/a', '/c'])
    assert repr1.selectors is not repr2.selectors
    assert len(repr2.selectors) == 3
    assert set(repr2.selectors) == {'/a', '/b', '/c'}


def prefer_header_test(api):
    default_includes = set(current_app.config['FLASK_TAXONOMIES_REPRESENTATION']['representation']['include'])

    rep = PreferHeaderField().deserialize('return=representation')
    assert rep.representation == 'representation'
    assert rep.include == default_includes
    assert rep.exclude == set()

    rep = PreferHeaderField().deserialize('return=representation; include=a b c; exclude=d e f; selectors = /a /b')
    assert rep.include == default_includes | {'a', 'b', 'c'}
    assert rep.exclude == {'d', 'e', 'f'}
    assert rep.selectors == {'/a', '/b'}

