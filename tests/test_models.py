# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from flask_taxonomies.models import Taxonomy, TaxonomyTerm


@pytest.mark.usefixtures('db')
class TestTaxonomy:
    """Taxonomy model tests."""

    def test_create(self, db):
        tax = Taxonomy(code='code', extra_data={'extra': 'data'})
        db.session.add(tax)
        db.session.commit()

        retrieved = Taxonomy.get_by_id(tax.id)
        assert retrieved.code == 'code'
        assert retrieved.extra_data == {'extra': 'data'}


    def test_get_terms(self, db, root_taxonomy):
        """Get terms  listassocitated with this taxonomy."""
        leaf = TaxonomyTerm(slug="leaf", title={'en': 'Leaf'}, taxonomy=root_taxonomy)
        db.session.add(leaf)
        db.session.commit()

        nested = TaxonomyTerm(slug="nested", title={'en': 'Leaf'}, taxonomy=root_taxonomy)
        nested.parent = leaf
        db.session.add(nested)
        db.session.commit()

        children = root_taxonomy.terms
        assert children == [leaf, nested]  #

    def test_update_taxonomy(self, db, root_taxonomy):
        """Update Taxonomy extra_data."""

        root_taxonomy.update(extra_data={'description': 'updated'})

        retrieved_root = Taxonomy.get_by_id(root_taxonomy.id)
        assert retrieved_root.extra_data == {'description': 'updated'}

    def test_delete_taxonomy(self, db, root_taxonomy, manager):
        """Test deleting the whole Taxonomy."""
        leaf = TaxonomyTerm(
            slug='leaf',
            title={'en': 'Leaf'},
            extra_data={'description': 'TaxonomyTerm leaf term'},
            taxonomy=root_taxonomy
        )
        leaf2 = TaxonomyTerm(
            slug='leaf',
            title={'en': 'Leaf'},
            extra_data={'description': 'TaxonomyTerm leaf term'},
            taxonomy=root_taxonomy
        )
        db.session.add(leaf)
        db.session.add(leaf2)
        db.session.commit()

        db.session.delete(root_taxonomy)
        db.session.commit()

        assert Taxonomy.get_by_id(root_taxonomy.id) is None
        assert TaxonomyTerm.get_by_id(leaf.id) is None
        assert TaxonomyTerm.get_by_id(leaf2.id) is None


@pytest.mark.usefixtures('db')
class TestTaxonomyTerm:
    """TaxonomyTerm model tests."""

    def test_get_by_id(self, db, root_taxonomy):
        """Get TaxonomyTerm Tree Items by ID."""
        leaf = TaxonomyTerm(slug='leaf', title={'en': 'Leaf'}, taxonomy=root_taxonomy)
        db.session.add(leaf)
        db.session.commit()

        retrieved_leaf = TaxonomyTerm.get_by_id((leaf.id))
        assert retrieved_leaf == leaf

    def test_update_taxonomy_term(self, db, root_taxonomy):
        """Update TaxonomyTerm extra_data and name."""
        leaf = TaxonomyTerm(slug="leaf", title={"en": "Leaf"}, taxonomy=root_taxonomy)
        db.session.add(leaf)
        db.session.commit()

        leaf.update(extra_data={'description': 'updated'}, title={'en': 'newleaf'})

        retrieved_root = TaxonomyTerm.get_by_id(root_taxonomy.id)
        assert retrieved_root.extra_data == {'description': 'updated'}
        assert retrieved_root.title == {'en': 'newleaf'}

    def test_term_tree_path(self, db, root_taxonomy):
        """Test getting full path of a Term."""
        leaf = TaxonomyTerm(
            slug='leaf',
            title={'en': 'Leaf'},
            extra_data={'description': 'TaxonomyTerm leaf term'},
            taxonomy=root_taxonomy
        )
        db.session.add(leaf)
        db.session.commit()

        nested = TaxonomyTerm(
            slug='nested',
            title={'en': 'Nested'},
            extra_data={'description': 'Nested TaxonomyTerm'},
            taxonomy=root_taxonomy
        )
        nested.parent = leaf
        db.session.add(nested)
        db.session.commit()

        assert leaf.tree_path == '/root/leaf'
        assert nested.tree_path == '/root/leaf/nested'

    def test_delete_taxonomy_term(self, db, root_taxonomy):
        """Delete single TaxonomyTerm term."""
        leaf = TaxonomyTerm(
            slug='leaf',
            title={'en': 'Leaf'},
            extra_data={'description': 'TaxonomyTerm leaf term'},
            taxonomy=root_taxonomy
        )
        db.session.add(leaf)
        db.session.commit()

        db.session.delete(leaf)
        db.session.commit()

        assert TaxonomyTerm.get_by_id(leaf.id) is None
