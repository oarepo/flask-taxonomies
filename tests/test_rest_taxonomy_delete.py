from sqlalchemy_utils.types.json import json


def taxonomy_delete_test(api, client, test_taxonomy):
    resp = client.delete('/api/2.0/taxonomies/test')
    assert resp.status_code == 204
    exp = {
        'code': 'test',
        'links': {
            'self': 'https://localhost/api/2.0/taxonomies/test/',
            'tree': 'https://localhost/api/2.0/taxonomies/test/?representation:include=dsc'
        },
        'title': 'test title updated'
    }
    resp = client.get('/api/2.0/taxonomies/test')
    assert resp.status_code == 404
