# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest


@pytest.mark.usefixtures("db")
class TestTaxonomy:
    """Taxonomy model tests."""

    def test_create(self, db, Taxonomy, TaxonomyTerm):
        """Test create taxonomy."""
        tax = Taxonomy.create_taxonomy(code="code", extra_data={"extra": "data"})
        db.session.add(tax)
        db.session.commit()

        retrieved = Taxonomy(TaxonomyTerm.query.get(tax.id))
        assert retrieved.code == "code"
        assert retrieved.extra_data == {"extra": "data"}

    def test_get_terms(self, db, root_taxonomy, TaxonomyTerm):
        """Get terms  listassocitated with this taxonomy."""
        leaf = TaxonomyTerm(slug="leaf")
        db.session.add(leaf)

        root_taxonomy.append(leaf)
        db.session.commit()

        nested = TaxonomyTerm(slug="nested")
        nested.parent = leaf
        db.session.add(nested)
        db.session.commit()

        children = list(root_taxonomy.terms)
        assert children == [leaf, nested]  #

    def test_update_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Update Taxonomy extra_data."""

        root_taxonomy.update(extra_data={"description": "updated"})

        retrieved_root = TaxonomyTerm.query.get(root_taxonomy.id)
        assert retrieved_root.extra_data == {"description": "updated"}

    def test_delete_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Test deleting the whole Taxonomy."""
        leaf = TaxonomyTerm(slug="leaf")
        root_taxonomy.append(leaf)
        leaf2 = TaxonomyTerm(slug="leaf2")
        root_taxonomy.append(leaf2)
        db.session.add(leaf)
        db.session.add(leaf2)
        db.session.commit()

        db.session.delete(root_taxonomy)
        db.session.commit()

        assert TaxonomyTerm.query.get(root_taxonomy.id) is None
        assert TaxonomyTerm.query.get(leaf.id) is None
        assert TaxonomyTerm.query.get(leaf2.id) is None


@pytest.mark.usefixtures("db")
class TestTaxonomyTerm:
    """TaxonomyTerm model tests."""

    def test_get_by_id(self, db, root_taxonomy, TaxonomyTerm):
        """Get TaxonomyTerm Tree Items by ID."""
        leaf = TaxonomyTerm(slug="leaf")
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        retrieved_leaf = TaxonomyTerm.query.get(leaf.id)
        assert retrieved_leaf == leaf

        # Test get invalid id
        retrieved_leaf = TaxonomyTerm.query.get(12345)
        assert retrieved_leaf is None

    def test_update_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm):
        """Update TaxonomyTerm extra_data and name."""
        leaf = TaxonomyTerm(slug="leaf")
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        leaf.update(extra_data={"description": "updated"})

        retrieved_root = TaxonomyTerm.query.get(leaf.id)
        assert retrieved_root.extra_data == {"description": "updated"}

    def test_term_tree_path(self, db, root_taxonomy, TaxonomyTerm):
        """Test getting full path of a Term."""
        leaf = TaxonomyTerm(slug="leaf")
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        nested = TaxonomyTerm(
            slug="nested",
            parent=leaf
        )
        db.session.add(nested)
        db.session.commit()

        assert leaf.tree_path == "/root/leaf"
        assert nested.tree_path == "/root/leaf/nested"

    def test_delete_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm):
        """Delete single TaxonomyTerm term."""
        leaf = TaxonomyTerm(slug="leaf")
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        db.session.delete(leaf)
        db.session.commit()

        assert TaxonomyTerm.query.get(leaf.id) is None

    @pytest.mark.parametrize('filled_taxonomy',
                             [[1000]],
                             indirect=['filled_taxonomy'])
    def test_large_taxonomy(self, db, filled_taxonomy):
        assert filled_taxonomy.terms.count() == 1000
