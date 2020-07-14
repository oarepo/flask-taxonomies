from sqlalchemy_utils.types.json import json


def term_create_test(api, client, sample_taxonomy):
    term = client.put('/api/2.0/taxonomies/test/aaa',
                      data=json.dumps({
                          'title': 'test aaa title'
                      }),
                      content_type='application/json')
    exp = {
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/aaa',
        },
        'title': 'test aaa title'
    }
    assert json.loads(term.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test/aaa')
    assert json.loads(taxonomies.data) == exp

    term = client.put('/api/2.0/taxonomies/test/aaa/bbb',
                      data=json.dumps({
                          'title': 'test bbb title'
                      }),
                      content_type='application/json')
    exp = {
        'ancestors': [
            {
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/aaa'
                },
                'title': 'test aaa title'
            }
        ],
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/aaa/bbb'
        },
        'title': 'test bbb title'
    }

    assert json.loads(term.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test/aaa/bbb')
    assert json.loads(taxonomies.data) == exp


def term_create_post_test(api, client, sample_taxonomy):
    term = client.post('/api/2.0/taxonomies/test',
                       data=json.dumps({
                           'title': 'test aaa title',
                           'slug': 'aaa'
                       }),
                       content_type='application/json')
    exp = {
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/aaa',
        },
        'title': 'test aaa title'
    }
    assert json.loads(term.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test/aaa')
    assert json.loads(taxonomies.data) == exp

    term = client.post('/api/2.0/taxonomies/test/aaa',
                       data=json.dumps({
                           'title': 'test bbb title',
                           'slug': 'bbb'
                       }),
                       content_type='application/json')
    exp = {
        'ancestors': [
            {
                'links': {'self': 'http://localhost/api/2.0/taxonomies/test/aaa'},
                'title': 'test aaa title'
            }
        ],
        'links': {'self': 'http://localhost/api/2.0/taxonomies/test/aaa/bbb'},
        'title': 'test bbb title'
    }
    assert json.loads(term.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test/aaa/bbb')
    assert json.loads(taxonomies.data) == exp


def term_create_on_deleted_test(api, client, sample_taxonomy):
    client.delete('/api/2.0/taxonomies/test/b')
    resp = client.put('/api/2.0/taxonomies/test/b', data='{}', content_type='application/json')
    assert resp.status_code == 409
    assert resp.json['reason'] == 'deleted-term-exists'

    resp = client.put('/api/2.0/taxonomies/test/b?representation:include=del', data='{}',
                      content_type='application/json')
    assert resp.status_code == 200


def term_create_term_only_test(api, client, sample_taxonomy):
    resp = client.put('/api/2.0/taxonomies/test/b', data='{}',
                      content_type='application/json', headers={'If-None-Match': '*'})
    assert resp.status_code == 412
    assert resp.json['reason'] == 'term-exists'

    resp = client.put('/api/2.0/taxonomies/test/c', data='{}',
                      content_type='application/json', headers={'If-None-Match': '*'})
    assert resp.status_code == 201


def term_update_term_only_test(api, client, sample_taxonomy):
    resp = client.put('/api/2.0/taxonomies/test/c', data='{}',
                      content_type='application/json', headers={'If-Match': '*'})
    assert resp.status_code == 412
    assert resp.json['reason'] == 'term-does-not-exist'

    resp = client.put('/api/2.0/taxonomies/test/b', data='{}',
                      content_type='application/json', headers={'If-Match': '*'})
    assert resp.status_code == 200  # updated existing term
