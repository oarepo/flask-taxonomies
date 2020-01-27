import pytest
from jsonresolver import JSONResolver

from flask_taxonomies import jsonresolver
from flask_taxonomies.models import before_taxonomy_jsonresolve


def test_jsonresolver_no_taxonomy_term(app):
    assert app.config.get('TAXONOMY_SERVER_NAME') == 'taxonomy-server.com'
    resolver = JSONResolver()
    resolver.pm.register(jsonresolver, 'taxonomies-resolver')
    with pytest.raises(ValueError, match='The taxonomy term does not exist.'):
        resolver.resolve('https://taxonomy-server.com/api/taxonomies/code/slug')


def test_jsonresolver_before_signal(app):
    assert app.config.get('TAXONOMY_SERVER_NAME') == 'taxonomy-server.com'

    def before(source, code=None, slug=None, **kwargs):
        return {
            'code': code,
            'slug': slug
        }

    before_taxonomy_jsonresolve.connect(before)
    resolver = JSONResolver()
    resolver.pm.register(jsonresolver, 'taxonomies-resolver')
    assert resolver.resolve('https://taxonomy-server.com/api/taxonomies/code/slug') == {
        'code': 'code',
        'slug': 'slug'
    }
