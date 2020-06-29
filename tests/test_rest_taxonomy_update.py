from sqlalchemy_utils.types.json import json


def taxonomy_update_test(api, client, test_taxonomy):
    taxonomy = client.put('/api/2.0/taxonomies/test',
                          data=json.dumps({
                              'title': 'test title updated'
                          }),
                          content_type='application/json')
    exp = {
        'code': 'test',
        'links': {
            'self': 'https://localhost/api/2.0/taxonomies/test/',
            'tree': 'https://localhost/api/2.0/taxonomies/test/?representation:include=dsc'
        },
        'title': 'test title updated'
    }
    assert json.loads(taxonomy.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test')
    assert json.loads(taxonomies.data) == exp
