from sqlalchemy_utils.types.json import json


def term_create_test(api, client, sample_taxonomy):
    term = client.put('/api/2.0/taxonomies/test/aaa',
                          data=json.dumps({
                              'title': 'test aaa title'
                          }),
                          content_type='application/json')
    exp = {
        'links': {
            'self': 'https://localhost/api/2.0/taxonomies/test/aaa',
            'tree': 'https://localhost/api/2.0/taxonomies/test/aaa?representation:include=dsc'
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
        'links': {
            'self': 'https://localhost/api/2.0/taxonomies/test/aaa/bbb',
            'tree': 'https://localhost/api/2.0/taxonomies/test/aaa/bbb?representation:include=dsc'
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
            'self': 'https://localhost/api/2.0/taxonomies/test/aaa',
            'tree': 'https://localhost/api/2.0/taxonomies/test/aaa?representation:include=dsc'
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
        'links': {
            'self': 'https://localhost/api/2.0/taxonomies/test/aaa/bbb',
            'tree': 'https://localhost/api/2.0/taxonomies/test/aaa/bbb?representation:include=dsc'
        },
        'title': 'test bbb title'
    }
    assert json.loads(term.data) == exp
    taxonomies = client.get('/api/2.0/taxonomies/test/aaa/bbb')
    assert json.loads(taxonomies.data) == exp
