import pytest

from flask_taxonomies.api import TermIdentification
from flask_taxonomies.models import TaxonomyError, TaxonomyTerm


def term_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1'))
    t2 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1/t2'))
    assert t2.parent == t1

    ti1 = TermIdentification(term=t1)
    ti2 = TermIdentification(term=t2)

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, taxonomy=test_taxonomy)

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, parent=t1)

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, slug='abc')

    assert ti1 != ti2
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti1.taxonomy is None
    assert ti1.slug is None

    assert ti2.taxonomy is None
    assert ti2.slug is None

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def term_slug_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1'))
    t2 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1/t2'))
    assert t2.parent == t1

    ti1 = TermIdentification(term=t1)
    ti2 = TermIdentification(taxonomy=test_taxonomy, slug='t1/t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, taxonomy=test_taxonomy)

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, parent=t1)

    with pytest.raises(TaxonomyError):
        TermIdentification(term=t1, slug='abc')

    assert ti1 != ti2
    assert ti2 != ti1
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti1 == TermIdentification(taxonomy='test', slug='t1')
    assert TermIdentification(taxonomy='test', slug='t1') == ti1

    assert ti1 == TermIdentification(taxonomy=test_taxonomy.id, slug='t1')
    assert TermIdentification(taxonomy=test_taxonomy.id, slug='t1') == ti1

    assert ti1.taxonomy is None
    assert ti1.slug is None

    assert ti2.taxonomy is not None
    assert ti2.slug is not None

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def taxonomy_slug_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1'))
    t2 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1/t2'))

    ti1 = TermIdentification(taxonomy=test_taxonomy, slug='t1')
    ti2 = TermIdentification(taxonomy=test_taxonomy, slug='t1/t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(taxonomy=test_taxonomy)

    assert ti1 != ti2
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def taxonomy_code_slug_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1'))
    t2 = api.create_term(TermIdentification(taxonomy=test_taxonomy.code, slug='t1/t2'))

    ti1 = TermIdentification(taxonomy=test_taxonomy, slug='t1')
    ti2 = TermIdentification(taxonomy=test_taxonomy.code, slug='t1/t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(taxonomy=test_taxonomy)

    assert ti1 != ti2
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti2 != ti1
    assert ti2.parent_identification() == ti1

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def taxonomy_id_slug_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='t1'))
    t2 = api.create_term(TermIdentification(taxonomy=test_taxonomy.id, slug='t1/t2'))

    ti1 = TermIdentification(taxonomy=test_taxonomy, slug='t1')
    ti2 = TermIdentification(taxonomy=test_taxonomy.id, slug='t1/t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(taxonomy=test_taxonomy)

    assert ti1 != ti2
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti2 != ti1
    assert ti2.parent_identification() == ti1

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def slug_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(slug='test/t1'))
    t2 = api.create_term(TermIdentification(slug='test/t1/t2'))

    ti1 = TermIdentification(slug='test/t1')
    ti2 = TermIdentification(slug='test/t1/t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(slug='aaa')  # no taxonomy here

    assert ti1 != ti2
    assert ti1 != 'aaa'
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti2 != ti1
    assert ti2.parent_identification() == ti1

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def incompatible_taxonomies_test(api, test_taxonomy):
    ti1 = TermIdentification(taxonomy=test_taxonomy.id, slug='test/t1')
    ti2 = TermIdentification(taxonomy=test_taxonomy.code, slug='test/t1/t2')

    with pytest.raises(ValueError):
        assert ti1 != ti2


def parent_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(slug='test/t1'))
    t2 = api.create_term(TermIdentification(slug='test/t1/t2'))

    ti1 = TermIdentification(parent='test', slug='t1')
    ti2 = TermIdentification(parent='test/t1', slug='t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(taxonomy=test_taxonomy, parent='t1', slug='t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(parent='test/t1')

    assert ti1 != ti2
    assert ti1 == ti2.parent_identification()
    assert ti1.parent_identification() is None

    assert ti2 != ti1
    assert ti2.parent_identification() == ti1

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy


def parent_object_test(api, test_taxonomy):
    t1 = api.create_term(TermIdentification(slug='test/t1'))
    t2 = api.create_term(TermIdentification(slug='test/t1/t2'))

    ti1 = TermIdentification(parent='test', slug='t1')
    ti2 = TermIdentification(parent=t1, slug='t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(taxonomy=test_taxonomy, parent='t1', slug='t2')

    with pytest.raises(TaxonomyError):
        TermIdentification(parent='test/t1')

    assert list(ti1.term_query(api.session)) == [t1]
    assert list(ti2.term_query(api.session)) == [t2]

    assert list(ti1.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]
    assert list(ti2.descendant_query(api.session).order_by(TaxonomyTerm.slug)) == [t2]

    assert list(ti1.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1]
    assert list(ti2.ancestor_query(api.session).order_by(TaxonomyTerm.slug)) == [t1, t2]

    assert ti1.leaf_slug == 't1'
    assert ti2.leaf_slug == 't2'

    assert ti1.get_taxonomy(api.session) == test_taxonomy
    assert ti2.get_taxonomy(api.session) == test_taxonomy
