import pytest
from flask_principal import Permission, UserNeed
from sqlalchemy_utils.types.json import json


@pytest.mark.parametrize('app', [
    {
        'FLASK_TAXONOMIES_PERMISSION_FACTORIES': {
            'taxonomy_list': [Permission(UserNeed('admin'))]
        }
    }
], indirect=['app'])
def taxonomy_list_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/2.0/taxonomies/')
    assert taxonomies.status_code == 403

    client.post('/login', json={'username': 'admin'})

    taxonomies = client.get('/api/2.0/taxonomies/')
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test',
            'title': 'Test taxonomy',
            'links': {
                'self': 'http://localhost/api/2.0/taxonomies/test/'
            }
        }
    ]


@pytest.mark.parametrize('app', [
    {
        'FLASK_TAXONOMIES_PERMISSION_FACTORIES': {
            'taxonomy_term_delete': [Permission(UserNeed('admin'))]
        }
    }
], indirect=['app'])
def taxonomy_term_delete_test(api, client, sample_taxonomy):
    taxonomies = client.delete('/api/2.0/taxonomies/test/a')
    assert taxonomies.status_code == 403

    client.post('/login', json={'username': 'admin'})

    taxonomies = client.delete('/api/2.0/taxonomies/test/a')
    assert taxonomies.status_code == 200


def factory(**kwargs):
    if kwargs['term'].slug == 'a':
        return []
    return [Permission(UserNeed('admin'))]


@pytest.mark.parametrize('app', [
    {
        'FLASK_TAXONOMIES_PERMISSION_FACTORIES': {
            'taxonomy_term_delete': 'tests.test_rest_permissions.factory'
        }
    }
], indirect=['app'])
def taxonomy_term_delete_test(api, client, sample_taxonomy):
    taxonomies = client.delete('/api/2.0/taxonomies/test/a')
    assert taxonomies.status_code == 200

    taxonomies = client.delete('/api/2.0/taxonomies/test/b')
    assert taxonomies.status_code == 403

    client.post('/login', json={'username': 'admin'})

    taxonomies = client.delete('/api/2.0/taxonomies/test/b')
    assert taxonomies.status_code == 200
