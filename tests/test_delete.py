import pytest

from flask_taxonomies.models import TaxonomyError


def delete_locked_test(api):
    tax = api.create_taxonomy(code='test')
    t1 = api.create_term('test/a')
    api.mark_busy([t1.id])
    with pytest.raises(TaxonomyError):
        api.delete_term(t1)


def delete_locked_ancestors_test(api):
    tax = api.create_taxonomy(code='test')
    t1 = api.create_term('test/a')
    api.mark_busy([t1.id])
    t2 = api.create_term('test/a/b')

    with pytest.raises(TaxonomyError):
        api.delete_term(t2)


def delete_locked_descendants_test(api):
    tax = api.create_taxonomy(code='test')
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    api.mark_busy([t2.id])

    with pytest.raises(TaxonomyError):
        api.delete_term(t1)


def delete_locked_rest_test(api, client):
    tax = api.create_taxonomy(code='test')
    t1 = api.create_term('test/a')
    api.mark_busy([t1.id])
    assert client.delete('/api/2.0/taxonomies/test/a').status_code == 412
