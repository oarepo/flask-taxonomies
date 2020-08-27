import pytest

from flask_taxonomies.query import TaxonomyQueryNotSupported


def taxonomy_levels_test(api, client, sample_taxonomy):
    terms = client.get('/api/2.0/taxonomies/test?representation:levels=1',
                       headers={
                           'prefer': 'return=minimal; include=data dsc'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {'slug': 'a', 'title': 'A'},
            {'slug': 'b', 'title': 'B'}
        ],
        'code': 'test',
        'title': 'Test taxonomy'
    }


def taxonomy_levels_prefer_test(api, client, sample_taxonomy):
    terms = client.get('/api/2.0/taxonomies/test',
                       headers={
                           'prefer': 'return=minimal; include=data dsc; levels=1'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {'slug': 'a', 'title': 'A'},
            {'slug': 'b', 'title': 'B'}
        ],
        'code': 'test',
        'title': 'Test taxonomy'
    }


def taxonomy_levels_no_self_test(api, client, sample_taxonomy):
    terms = client.get('/api/2.0/taxonomies/test?representation:levels=1',
                       headers={
                           'prefer': 'return=minimal; include=data dsc; exclude=self'
                       })
    assert terms.status_code == 200
    assert terms.json == [
        {'slug': 'a', 'title': 'A'},
        {'slug': 'b', 'title': 'B'}
    ]


def taxonomy_multiple_levels_test(api, client, deep_taxonomy):
    terms = client.get('/api/2.0/taxonomies/deep?representation:levels=2',
                       headers={
                           'prefer': 'return=minimal; include=data dsc'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {
                'children': [
                    {'slug': 'a/aa', 'title': 'AA'}
                ],
                'slug': 'a',
                'title': 'A'
            },
            {
                'slug': 'b',
                'title': 'B',
                'children': [{'slug': 'b/b1', 'title': 'B1'},
                             {'slug': 'b/b2', 'title': 'B2'}],
            }
        ],
        'code': 'deep',
        'title': 'Test deep taxonomy'}


def term_levels_test(api, client, deep_taxonomy):
    terms = client.get('/api/2.0/taxonomies/deep/a?representation:levels=1',
                       headers={
                           'prefer': 'return=minimal; include=data dsc'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {
                'slug': 'a/aa',
                'title': 'AA'
            }
        ],
        'slug': 'a',
        'title': 'A'
    }


def term_levels_no_self_test(api, client, deep_taxonomy):
    terms = client.get('/api/2.0/taxonomies/deep/b?representation:levels=1',
                       headers={
                           'prefer': 'return=minimal; include=data dsc; exclude=self'
                       })
    assert terms.status_code == 200
    assert terms.json == [
        {'slug': 'b/b1', 'title': 'B1'},
        {'slug': 'b/b2', 'title': 'B2'}
    ]


def term_multiple_levels_test(api, client, deep_taxonomy):
    terms = client.get('/api/2.0/taxonomies/deep/a?representation:levels=2',
                       headers={
                           'prefer': 'return=minimal; include=data dsc'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {
                'slug': 'a/aa',
                'title': 'AA',
                'children': [
                    {
                        'slug': 'a/aa/aaa',
                        'title': 'AAA'
                    }
                ]
            }
        ],
        'slug': 'a',
        'title': 'A'
    }


def country_levels_test(api, client, country_taxonomy):
    terms = client.get('/api/2.0/taxonomies/country?representation:levels=1',
                       headers={
                           'prefer': 'return=minimal; include=data dsc'
                       })
    assert terms.status_code == 200
    assert terms.json == {
        'children': [
            {'slug': 'africa'},
            {'slug': 'antarctica'},
            {'slug': 'asia'},
            {'slug': 'australia'},
            {'slug': 'central-america'},
            {'slug': 'europe'},
            {'slug': 'north-america'},
            {'slug': 'south-america'}
        ],
        'code': 'country',
        'title': 'List of countries'
    }
