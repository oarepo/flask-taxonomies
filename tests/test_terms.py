import pytest

from flask_taxonomies.api import TermIdentification
from flask_taxonomies.models import TaxonomyError, TaxonomyTerm, TermStatusEnum
from flask_taxonomies.utils import to_json


def simple_op_test(api, test_taxonomy):
    # can not cfreate term outside of taxonomy
    with pytest.raises(TaxonomyError):
        api.create_term('b')

    term2 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='b'))
    assert term2.slug == 'b'
    assert term2.level == 0
    term1 = api.create_term(TermIdentification(parent=test_taxonomy.code, slug='a'))
    assert term1.slug == 'a'
    assert term1.level == 0
    term11 = api.create_term(TermIdentification(parent=test_taxonomy.code + '/a', slug='aa'))
    assert term11.slug == 'a/aa'
    assert term11.level == 1
    term21 = api.create_term(TermIdentification(parent=term2, slug='bb'))
    assert term21.slug == 'b/bb'
    assert term21.level == 1
    term22 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='b/cc'))
    assert term22.slug == 'b/cc'
    assert term22.level == 1

    # term filter

    assert list(api.filter_term(TermIdentification(taxonomy=test_taxonomy, slug=term2.slug))) == [term2]
    assert list(api.filter_term(TermIdentification(parent=term2, slug='bb'))) == [term21]

    assert list(api.filter_term(TermIdentification(taxonomy=test_taxonomy, slug='b'))) == [term2]
    assert list(api.filter_term(TermIdentification(parent='test/b', slug='bb'))) == [term21]

    assert list(api.filter_term(TermIdentification(taxonomy='test', slug='b'))) == [term2]
    assert list(api.filter_term(TermIdentification(parent='test/b', slug='bb'))) == [term21]

    assert list(api.filter_term('test/b')) == [term2]
    assert list(api.filter_term(TermIdentification(parent='test', slug='b'))) == [term2]
    assert list(api.filter_term(TermIdentification(parent='test/b', slug='bb'))) == [term21]

    # different ways of listing taxonomy
    assert list(api.list_taxonomy(test_taxonomy)) == [term1, term11, term2, term21, term22]
    assert list(api.list_taxonomy('test')) == [term1, term11, term2, term21, term22]

    # list just 1 level
    assert list(api.list_taxonomy(test_taxonomy, levels=1)) == [term1, term2]

    # start at term
    assert list(api.descendants_or_self(term1)) == [term1, term11]
    assert list(api.descendants(term1)) == [term11]
    assert list(api.descendants_or_self(TermIdentification(parent=term1, slug='aa'))) == [term11]
    assert list(api.descendants_or_self(TermIdentification(parent='test/a', slug='aa'))) == [term11]

    # specify number of levels
    assert list(api.descendants_or_self(term1, levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(term1, levels=0)) == [term1]

    assert list(api.descendants(TermIdentification(taxonomy=test_taxonomy, slug='a'))) == [term11]
    assert list(api.descendants(TermIdentification(taxonomy=test_taxonomy, slug='a'))) == [term11]

    assert list(api.descendants_or_self(
        TermIdentification(taxonomy=test_taxonomy, slug='a'), levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(TermIdentification(taxonomy=test_taxonomy, slug='a'), levels=0)) == [term1]

    assert list(api.descendants(test_taxonomy.code + '/a')) == [term11]

    assert list(api.descendants_or_self(test_taxonomy.code + '/a', levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(test_taxonomy.code + '/a', levels=0)) == [term1]

    # descendant of non-existing
    assert list(api.descendants(TermIdentification(taxonomy=test_taxonomy, slug='a/bb'))) == []

    # ancestors
    assert list(api.ancestors_or_self(term11)) == [term1, term11]
    assert list(api.ancestors(term11)) == [term1]

    # empty ancestor of a taxonomy (term not given)

    # empty ancestor of root term
    assert list(api.ancestors(TermIdentification(taxonomy=test_taxonomy, slug='a'))) == []

    assert list(api.ancestors(TermIdentification(taxonomy=test_taxonomy, slug='a/aa'))) == [term1]

    assert list(api.ancestors_or_self(TermIdentification(taxonomy=test_taxonomy, slug='a/aa'))) == [term1, term11]

    assert list(api.ancestors('test/a/aa')) == [term1]
    assert list(api.ancestors(TermIdentification(parent='test/a', slug='aa'))) == [term1]

    term11_id = term11.id
    api.session.refresh(term11)
    assert term11.busy_count == 0

    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'slug': 'a',
            'status': TermStatusEnum.alive.value,
            'children': [
                {
                    'children': [],
                    'level': 1,
                    'slug': 'a/aa',
                    'status': TermStatusEnum.alive.value,
                }
            ],
        },
        {
            'level': 0,
            'slug': 'b',
            'status': TermStatusEnum.alive.value,
            'children': [
                {
                    'children': [],
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/bb'
                },

                {
                    'children': [],
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/cc'
                }
            ],
        }
    ]

    # try to delete busy terms
    locked_terms = [
        r[0] for r in
        api.descendants_or_self(term11, order=False).with_for_update().values(TaxonomyTerm.id)
    ]  # get ids to actually lock the terms

    api.mark_busy(locked_terms)
    with pytest.raises(TaxonomyError):
        api.delete_term(term11, remove_after_delete=False)
    api.unmark_busy(locked_terms)

    # delete ordinary term but keep in database
    api.delete_term(term11, remove_after_delete=False)
    assert list(api.descendants(term1)) == []

    api.session.refresh(term11)
    assert term11.status == TermStatusEnum.deleted
    assert term11.busy_count == 0

    with pytest.raises(TaxonomyError):
        # can not create term inside deleted one
        api.create_term(TermIdentification(parent=term11, slug='cc'))

    # delete for ever
    api.delete_term(term11)
    assert list(api.descendants(term1)) == []

    # check no more there
    assert not api.session.query(TaxonomyTerm).filter(TaxonomyTerm.id == term11_id).first()
    api.session.commit()


def update_test(api, test_taxonomy):
    term = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='b'))
    api.update_term(TermIdentification(taxonomy=test_taxonomy, slug='b'), extra_data={
        'a': 'b'
    })
    api.session.commit()
    api.session.refresh(term)
    assert term.extra_data == {'a': 'b'}

    api.update_term(term, extra_data=[{
        'op': 'replace',
        'path': '/a',
        'value': 'c'
    }], patch=True)
    api.session.commit()
    api.session.refresh(term)
    assert term.extra_data == {'a': 'c'}

    term = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    api.update_term(term, extra_data=[{
        'op': 'add',
        'path': '/a',
        'value': 'c'
    }], patch=True)
    api.session.commit()
    api.session.refresh(term)
    assert term.extra_data == {'a': 'c'}
