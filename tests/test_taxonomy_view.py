from sqlalchemy_utils.types.json import json


def taxonomy_list_empty_test(api, client):
    taxonomies = client.get('/api/1.0/taxonomies/')
    assert json.loads(taxonomies.data) == []


def taxonomy_list_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/1.0/taxonomies/')
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test',
            'title': 'Test taxonomy',
            'links': {
                'self': 'https://localhost/api/1.0/taxonomies/test/',
                'tree': 'https://localhost/api/1.0/taxonomies/test/?representation:include=dsc'
            }
        }
    ]


def taxonomy_list_no_urls_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/1.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test',
            'title': 'Test taxonomy'
        }
    ]


def taxonomy_list_no_urls_but_id_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/1.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; exclude=url drl; include=id'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test',
            'title': 'Test taxonomy',
            'id': 1
        }
    ]


def taxonomy_list_no_urls_in_query_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/1.0/taxonomies/?representation:exclude=url,drl&representation:include=id')
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test',
            'title': 'Test taxonomy',
            'id': 1
        }
    ]


def taxonomy_list_selector_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/1.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; selectors=; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test'
        }
    ]
