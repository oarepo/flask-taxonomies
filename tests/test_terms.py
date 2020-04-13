import pytest

from flask_taxonomies.models import TermStatusEnum, TaxonomyTerm, TaxonomyError


def simple_op_test(api, test_taxonomy):
    # can not cfreate term outside of taxonomy
    with pytest.raises(TaxonomyError):
        api.create_term(slug='b')

    term2 = api.create_term(taxonomy=test_taxonomy, slug='b')
    assert term2.slug == 'b'
    assert term2.level == 0
    term1 = api.create_term(parent_path=test_taxonomy.code, slug='a')
    assert term1.slug == 'a'
    assert term1.level == 0
    term11 = api.create_term(parent_path=test_taxonomy.code + '/a', slug='aa')
    assert term11.slug == 'a/aa'
    assert term11.level == 1
    term21 = api.create_term(parent=term2, slug='bb')
    assert term21.slug == 'b/bb'
    assert term21.level == 1
    term22 = api.create_term(taxonomy=test_taxonomy, parent_path='b', slug='cc')
    assert term22.slug == 'b/cc'
    assert term22.level == 1

    with pytest.raises(TaxonomyError):
        api.descendants_or_self()

    # term filter

    with pytest.raises(TaxonomyError):
        api.filter_term(taxonomy=test_taxonomy)

    assert list(api.filter_term(taxonomy=test_taxonomy, parent=term2)) == [term2]
    assert list(api.filter_term(taxonomy=test_taxonomy, parent=term2, slug='bb')) == [term21]

    assert list(api.filter_term(taxonomy=test_taxonomy, slug='b')) == [term2]
    assert list(api.filter_term(taxonomy=test_taxonomy, parent='b')) == [term2]
    assert list(api.filter_term(taxonomy=test_taxonomy, parent='b', slug='bb')) == [term21]

    assert list(api.filter_term(taxonomy='test', slug='b')) == [term2]
    assert list(api.filter_term(taxonomy='test', parent='b')) == [term2]
    assert list(api.filter_term(taxonomy='test', parent='b', slug='bb')) == [term21]

    assert list(api.filter_term(slug='test/b')) == [term2]
    assert list(api.filter_term(parent='test/b')) == [term2]
    assert list(api.filter_term(parent='test/b', slug='bb')) == [term21]

    # different ways of listing taxonomy
    assert list(api.descendants_or_self(taxonomy=test_taxonomy)) == [term1, term11, term2, term21, term22]
    assert list(api.descendants_or_self(taxonomy='test')) == [term1, term11, term2, term21, term22]

    assert list(api.descendants_or_self(parent='test')) == [term1, term11, term2, term21, term22]
    assert list(api.descendants_or_self(slug='test')) == [term1, term11, term2, term21, term22]

    # list just 1 level
    assert list(api.descendants_or_self(taxonomy=test_taxonomy, levels=1)) == [term1, term2]

    # start at term
    assert list(api.descendants_or_self(parent=term1)) == [term1, term11]
    assert list(api.descendants(parent=term1)) == [term11]
    assert list(api.descendants_or_self(parent=term1, slug='aa')) == [term11]
    assert list(api.descendants_or_self(parent='test/a', slug='aa')) == [term11]

    # specify number of levels
    assert list(api.descendants_or_self(parent=term1, levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(parent=term1, levels=0)) == [term1]

    assert list(api.descendants(taxonomy=test_taxonomy, parent='a')) == [term11]
    assert list(api.descendants(taxonomy=test_taxonomy, slug='a')) == [term11]

    assert list(api.descendants_or_self(taxonomy=test_taxonomy, parent='a', levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(taxonomy=test_taxonomy, slug='a', levels=0)) == [term1]

    assert list(api.descendants(parent=test_taxonomy.code + '/a')) == [term11]
    assert list(api.descendants(slug=test_taxonomy.code + '/a')) == [term11]

    assert list(api.descendants_or_self(parent=test_taxonomy.code + '/a', levels=1)) == [term1, term11]
    assert list(api.descendants_or_self(slug=test_taxonomy.code + '/a', levels=0)) == [term1]

    # descendant of non-existing
    assert list(api.descendants(taxonomy=test_taxonomy, slug='a/bb')) == []

    # ancestors
    assert list(api.ancestors_or_self(term=term11)) == [term1, term11]
    assert list(api.ancestors(term=term11)) == [term1]

    # empty ancestor of a taxonomy (term not given)
    assert list(api.ancestors(taxonomy=test_taxonomy)) == []
    assert list(api.ancestors(taxonomy=test_taxonomy, term='')) == []
    assert list(api.ancestors(taxonomy=test_taxonomy, slug='')) == []
    assert list(api.ancestors(term='test')) == []
    assert list(api.ancestors(slug='test')) == []

    # empty ancestor of root term
    assert list(api.ancestors(taxonomy=test_taxonomy, term='a')) == []
    assert list(api.ancestors(taxonomy=test_taxonomy, slug='a')) == []

    assert list(api.ancestors(taxonomy=test_taxonomy, term='a/aa')) == [term1]
    assert list(api.ancestors(taxonomy=test_taxonomy, slug='a/aa')) == [term1]
    assert list(api.ancestors(taxonomy=test_taxonomy, term='a', slug='aa')) == [term1]

    assert list(api.ancestors_or_self(taxonomy=test_taxonomy, term='a/aa')) == [term1, term11]

    assert list(api.ancestors(term='test/a/aa')) == [term1]
    assert list(api.ancestors(slug='test/a/aa')) == [term1]
    assert list(api.ancestors(term='test/a', slug='aa')) == [term1]

    term11_id = term11.id
    api.session.refresh(term11)
    assert term11.busy_count == 0

    # try to delete busy terms
    api.mark_busy(api.descendants_or_self(parent=term11, order=False))
    with pytest.raises(TaxonomyError):
        api.delete_term(term=term11, remove_after_delete=False)
    api.unmark_busy(api.descendants_or_self(parent=term11, order=False))

    # delete ordinary term but keep in database
    api.delete_term(term=term11, remove_after_delete=False)
    assert list(api.descendants(parent=term1)) == []

    api.session.refresh(term11)
    assert term11.status == TermStatusEnum.deleted
    assert term11.busy_count == 0

    with pytest.raises(TaxonomyError):
        # can not create term inside deleted one
        api.create_term(taxonomy=test_taxonomy.code, parent=term11, slug='cc')

    # delete for ever
    api.delete_term(term=term11)
    assert list(api.descendants(parent=term1)) == []

    # check no more there
    assert not api.session.query(TaxonomyTerm).filter(TaxonomyTerm.id == term11_id).first()
    api.session.commit()
