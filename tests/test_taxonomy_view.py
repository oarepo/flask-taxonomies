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


def taxonomy_list_pagination_test(api, client, many_taxonomies):
    taxonomies = client.get('/api/1.0/taxonomies/?page=2&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == {
        'page': 2,
        'size': 10,
        'total': 100,
        'data': [
            {'code': 'test-11', 'title': 'Test taxonomy #11'},
            {'code': 'test-12', 'title': 'Test taxonomy #12'},
            {'code': 'test-13', 'title': 'Test taxonomy #13'},
            {'code': 'test-14', 'title': 'Test taxonomy #14'},
            {'code': 'test-15', 'title': 'Test taxonomy #15'},
            {'code': 'test-16', 'title': 'Test taxonomy #16'},
            {'code': 'test-17', 'title': 'Test taxonomy #17'},
            {'code': 'test-18', 'title': 'Test taxonomy #18'},
            {'code': 'test-19', 'title': 'Test taxonomy #19'},
            {'code': 'test-20', 'title': 'Test taxonomy #20'}
        ]
    }

    # out of pages
    taxonomies = client.get('/api/1.0/taxonomies/?page=11&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == {
        'page': 11,
        'size': 10,
        'total': 100,
        'data': []
    }


def get_taxonomy_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/1.0/taxonomies/test')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'title': 'Test taxonomy',
        'links': {
            'self': 'https://localhost/api/1.0/taxonomies/test/',
            'tree': 'https://localhost/api/1.0/taxonomies/test/?representation:include=dsc'
        }
    }


def get_nonexisting_taxonomy_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/1.0/taxonomies/unknown')
    assert taxonomy.status_code == 404


def get_taxonomy_descendants_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/1.0/taxonomies/test?representation:include=dsc')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'https://localhost/api/1.0/taxonomies/test/',
            'tree': 'https://localhost/api/1.0/taxonomies/test/?representation:include=dsc'
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/a',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/a?representation:include=dsc'
                },
                'children': [
                    {
                        'title': 'AA',
                        'links': {
                            'self': 'https://localhost/api/1.0/taxonomies/test/a/aa',
                            'tree': 'https://localhost/api/1.0/taxonomies/test/a/aa?representation:include=dsc'
                        }
                    }
                ]
            },
            {
                'title': 'B',
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/b',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/b?representation:include=dsc'
                }
            }
        ]
    }


def get_taxonomy_descendants_level_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/1.0/taxonomies/test?representation:include=dsc&representation:levels=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'https://localhost/api/1.0/taxonomies/test/',
            'tree': 'https://localhost/api/1.0/taxonomies/test/?representation:include=dsc'
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/a',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/a?representation:include=dsc'
                }
            },
            {
                'title': 'B',
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/b',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/b?representation:include=dsc'
                }
            }
        ]
    }


def get_taxonomy_descendants_level_slug_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/1.0/taxonomies/test?representation:include=dsc,slug,lvl&representation:levels=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'https://localhost/api/1.0/taxonomies/test/',
            'tree': 'https://localhost/api/1.0/taxonomies/test/?representation:include=dsc'
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'slug': 'test/a',
                'level': 0,
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/a',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/a?representation:include=dsc'
                }
            },
            {
                'title': 'B',
                'slug': 'test/b',
                'level': 0,
                'links': {
                    'self': 'https://localhost/api/1.0/taxonomies/test/b',
                    'tree': 'https://localhost/api/1.0/taxonomies/test/b?representation:include=dsc'
                }
            }
        ]
    }


def get_taxonomy_paginated_descendants_test(api, client, sample_taxonomy):
    taxonomy = client.get(
        '/api/1.0/taxonomies/test?representation:include=dsc&representation:exclude=url,drl&page=1&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'page': 1,
        'size': 1,
        'total': 3,
        'data': {
            'code': 'test',
            'title': 'Test taxonomy',
            'children': [
                {
                    'title': 'A'
                }
            ]
        }
    }

    # second page - should keep 'A' to preserve the hierarchy
    taxonomy = client.get(
        '/api/1.0/taxonomies/test?representation:include=dsc&representation:exclude=url,drl&page=2&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'page': 2,
        'size': 1,
        'total': 3,
        'data': {
            'code': 'test',
            'title': 'Test taxonomy',
            'children': [
                {
                    'title': 'A',
                    'children': [
                        {
                            'title': 'AA',
                        }
                    ]
                }
            ]
        }
    }

    # third page - just B
    taxonomy = client.get(
        '/api/1.0/taxonomies/test?representation:include=dsc&representation:exclude=url,drl&page=3&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'page': 3,
        'size': 1,
        'total': 3,
        'data': {
            'code': 'test',
            'title': 'Test taxonomy',
            'children': [
                {
                    'title': 'B'
                }
            ]
        }
    }

