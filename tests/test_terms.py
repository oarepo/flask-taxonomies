import pytest


def simple_op_test(api, test_taxonomy):
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
    term22 = api.create_term(taxonomy=test_taxonomy.code, parent_path='b', slug='cc')
    assert term22.slug == 'b/cc'
    assert term22.level == 1

    with pytest.raises(ValueError):
        api.descendants_or_self()

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
