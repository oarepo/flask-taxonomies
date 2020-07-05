from sqlalchemy_utils.types.json import json


def taxonomy_create_test(api, client):
    taxonomy = client.put('/api/2.0/taxonomies/test',
                          data=json.dumps({
                              'title': 'test title'
                          }),
                          content_type='application/json')
    exp = {
        'code': 'test',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'test title'
    }
    assert json.loads(taxonomy.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test')
    assert json.loads(taxonomies.data) == exp


def taxonomy_post_create_test(api, client):
    taxonomy = client.post('/api/2.0/taxonomies/',
                           data=json.dumps({
                               'title': 'test title',
                               'code': 'test'
                           }),
                           content_type='application/json')
    exp = {
        'code': 'test',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'test title'
    }
    assert json.loads(taxonomy.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/')
    assert json.loads(taxonomies.data) == [exp]
