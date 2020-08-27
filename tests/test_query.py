import pytest

from flask_taxonomies.query import TaxonomyQueryNotSupported


def taxonomy_string_query_test(api, sample_taxonomy):
    sqlalchemy_query = api.list_taxonomies()
    sqlalchemy_query = api.apply_taxonomy_query(sqlalchemy_query, 'test')
    assert list(sqlalchemy_query) == [sample_taxonomy]


@pytest.mark.xfail
def taxonomy_title_string_query_test(api, sample_taxonomy):
    sqlalchemy_query = api.list_taxonomies()
    sqlalchemy_query = api.apply_taxonomy_query(sqlalchemy_query, 'title')
    assert list(sqlalchemy_query) == []  # title should not match on correct implementation


def term_string_query_test(api, country_taxonomy):
    sqlalchemy_query = api.list_taxonomy('country')
    sqlalchemy_query = api.apply_term_query(sqlalchemy_query, 'Czech', 'country')
    assert [x.slug for x in sqlalchemy_query] == ['europe/cz']


def term_title_query_test(api, country_taxonomy):
    try:
        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(sqlalchemy_query, 'CountryName:"Czech Republic"', 'country')
        assert [x.slug for x in sqlalchemy_query] == ['europe/cz']

        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(sqlalchemy_query, 'CountryName:"Czech Republic" OR CountryCode:GB',
                                                'country')
        assert set([x.slug for x in sqlalchemy_query]) == {'europe/cz', 'europe/gb'}

        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(sqlalchemy_query, 'CountryName:"Czech Republic" AND CountryCode:GB',
                                                'country')
        assert not [x.slug for x in sqlalchemy_query]

        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(sqlalchemy_query, 'CountryName:"Czech Republic" AND CountryCode:CZ',
                                                'country')
        assert set([x.slug for x in sqlalchemy_query]) == {'europe/cz'}

        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(
            sqlalchemy_query,
            '(CountryName:"Czech Republic" AND CountryCode:CZ) OR CountryCode:GB',
            'country'
        )
        assert set([x.slug for x in sqlalchemy_query]) == {'europe/cz', 'europe/gb'}

        sqlalchemy_query = api.list_taxonomy('country')
        sqlalchemy_query = api.apply_term_query(
            sqlalchemy_query,
            'CountryCode:CZ AND NOT ( CountryCode:GB )',
            'country'
        )
        assert set([x.slug for x in sqlalchemy_query]) == {'europe/cz'}

    except TaxonomyQueryNotSupported:
        # databases other than postgres are not supported for complex query
        if api.session.bind.dialect.name == 'postgresql':
            raise


def rest_query_test(client, country_taxonomy):
    terms = client.get('/api/2.0/taxonomies/country/europe?q=Prague',
                       headers={
                           'prefer': 'return=minimal; include=data dsc; exclude=self'
                       })
    assert terms.status_code == 200
    assert terms.json == [{
        'CapitalLatitude': '50.083333333333336', 'CapitalLongitude': '14.466667', 'CapitalName': 'Prague',
        'ContinentName': 'Europe',
        'CountryCode': 'CZ', 'CountryName': 'Czech Republic', 'slug': 'europe/cz'
    }]
