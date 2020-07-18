from sqlalchemy_utils.types.json import json


def taxonomy_list_empty_test(api, client):
    taxonomies = client.get('/api/2.0/taxonomies/')
    assert json.loads(taxonomies.data) == []


def taxonomy_list_test(api, client, sample_taxonomy):
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


def taxonomy_list_no_urls_test(api, client, sample_taxonomy):
    taxonomies = client.get('/api/2.0/taxonomies/',
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
    taxonomies = client.get('/api/2.0/taxonomies/',
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
    taxonomies = client.get('/api/2.0/taxonomies/?representation:exclude=url,drl&representation:include=id')
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
    taxonomies = client.get('/api/2.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; select=; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test'
        }
    ]


def taxonomy_list_default_selector_test(api, client, excluded_title_sample_taxonomy):
    taxonomies = client.get('/api/2.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; select=; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
        {
            'code': 'test'
        }
    ]


def taxonomy_list_overwrite_default_selector_test(api, client, excluded_title_sample_taxonomy):
    taxonomies = client.get('/api/2.0/taxonomies/',
                            headers={
                                'prefer': 'return=representation; select=/title; exclude=url drl'
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


def taxonomy_list_pagination_test(api, client, many_taxonomies):
    taxonomies = client.get('/api/2.0/taxonomies/?page=2&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl; include=env'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == {
        'data': [
            {'code': 'test-11', 'data': {'title': 'Test taxonomy #11'}},
            {'code': 'test-12', 'data': {'title': 'Test taxonomy #12'}},
            {'code': 'test-13', 'data': {'title': 'Test taxonomy #13'}},
            {'code': 'test-14', 'data': {'title': 'Test taxonomy #14'}},
            {'code': 'test-15', 'data': {'title': 'Test taxonomy #15'}},
            {'code': 'test-16', 'data': {'title': 'Test taxonomy #16'}},
            {'code': 'test-17', 'data': {'title': 'Test taxonomy #17'}},
            {'code': 'test-18', 'data': {'title': 'Test taxonomy #18'}},
            {'code': 'test-19', 'data': {'title': 'Test taxonomy #19'}},
            {'code': 'test-20', 'data': {'title': 'Test taxonomy #20'}}],
        'links': {'self': 'http://localhost/api/2.0/taxonomies/?page=2&size=10'},
        'page': 2,
        'size': 10,
        'total': 100
    }

    taxonomies = client.get('/api/2.0/taxonomies/?page=2&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == [
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

    # out of pages
    taxonomies = client.get('/api/2.0/taxonomies/?page=11&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl; include=env'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == {
        'data': [],
        'links': {'self': 'http://localhost/api/2.0/taxonomies/?page=11&size=10'},
        'page': 11,
        'size': 10,
        'total': 100
    }

    taxonomies = client.get('/api/2.0/taxonomies/?page=11&size=10',
                            headers={
                                'prefer': 'return=representation; exclude=url drl'
                            })
    if taxonomies.status_code != 200:
        print(taxonomies.data)
    assert taxonomies.status_code == 200
    assert json.loads(taxonomies.data) == []


def get_taxonomy_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/test')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'title': 'Test taxonomy',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        }
    }


def get_nonexisting_taxonomy_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/unknown')
    assert taxonomy.status_code == 404


def get_taxonomy_descendants_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/test?representation:include=dsc')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/a',
                },
                'children': [
                    {
                        'title': 'AA',
                        'links': {
                            'self': 'http://localhost/api/2.0/taxonomies/test/a/aa',
                        }
                    }
                ]
            },
            {
                'title': 'B',
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/b',
                }
            }
        ]
    }


def get_taxonomy_descendants_level_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/test?representation:include=dsc&representation:levels=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/a',
                }
            },
            {
                'title': 'B',
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/b',
                }
            }
        ]
    }


def get_taxonomy_descendants_level_slug_test(api, client, sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/test?representation:include=dsc,slug,lvl&representation:levels=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'level': 0,
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'title': 'A',
                'slug': 'a',
                'level': 1,
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/a',
                }
            },
            {
                'title': 'B',
                'slug': 'b',
                'level': 1,
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/b',
                }
            }
        ]
    }


def get_taxonomy_paginated_descendants_test(api, client, sample_taxonomy):
    taxonomy = client.get(
        '/api/2.0/taxonomies/test?representation:include=dsc,env&representation:exclude=url,drl&page=1&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'children': [
            {'data': {'title': 'A'}}
        ],
        'code': 'test',
        'data': {'title': 'Test taxonomy'},
        'page': 1,
        'size': 1,
        'total': 3
    }

    # second page - should keep 'A' to preserve the hierarchy
    taxonomy = client.get(
        '/api/2.0/taxonomies/test?representation:include=dsc,anh,env&representation:exclude=url,drl&page=2&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'children': [
            {
                'ancestor': True,
                'children': [
                    {'data': {'title': 'AA'}}
                ],
                'data': {'title': 'A'}
            }
        ],
        'code': 'test',
        'data': {'title': 'Test taxonomy'},
        'page': 2,
        'size': 1,
        'total': 3
    }

    # third page - just B
    taxonomy = client.get(
        '/api/2.0/taxonomies/test?representation:include=dsc,anh,env&representation:exclude=url,drl&page=3&size=1')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'children': [
            {'data': {'title': 'B'}}
        ],
        'code': 'test',
        'data': {'title': 'Test taxonomy'},
        'page': 3,
        'size': 1,
        'total': 3
    }


def get_excluded_title_descendants(api, client, excluded_title_sample_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/test?representation:include=dsc')
    if taxonomy.status_code != 200:
        print(taxonomy.data)
    assert taxonomy.status_code == 200
    assert json.loads(taxonomy.data) == {
        'code': 'test',
        'links': {
            'self': 'http://localhost/api/2.0/taxonomies/test/',
        },
        'title': 'Test taxonomy',
        'children': [
            {
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/a',
                },
                'children': [
                    {
                        'links': {
                            'self': 'http://localhost/api/2.0/taxonomies/test/a/aa',
                        }
                    }
                ]
            },
            {
                'links': {
                    'self': 'http://localhost/api/2.0/taxonomies/test/b',
                }
            }
        ]
    }


def list_dcn_test(client, country_taxonomy):
    taxonomy = client.get('/api/2.0/taxonomies/country',
                          headers={
                              'prefer': 'return=minimal; include=dcn'
                          })
    assert taxonomy.status_code == 200
    assert taxonomy.json == {
        'code': 'country',
        'descendants_count': 253
    }


def list_paginated_dcn_test(client, country_taxonomy):
    terms = client.get('/api/2.0/taxonomies/country?page=2&size=50',
                       headers={
                           'prefer': 'return=minimal; include=dcn dsc anh'
                       })
    assert terms.status_code == 200
    assert terms.json['children'][0]['descendants_count'] == 58
