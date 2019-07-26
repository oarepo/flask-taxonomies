# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest
from sqlalchemy.orm import Session
from sqlalchemy_mptt import mptt_sessionmaker


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

    def test_move_taxonomy_term(self, db, root_taxonomy, Taxonomy, TaxonomyTerm):
        mptt_sessionmaker(db.session)

        def structure():
            rt = Taxonomy.get(root_taxonomy.code)
            return [
                (x.level, x.slug) for x in rt.descendants
            ]

        def move(term, parent, order):
            term = TaxonomyTerm.query.filter_by(slug=term).one()
            parent = TaxonomyTerm.query.filter_by(slug=parent).one()
            parent.append(term, order)

        leafs = []
        for i in range(3):
            leaf = TaxonomyTerm(slug="leaf%s" % i)
            root_taxonomy.append(leaf)
            db.session.add(leaf)
            db.session.commit()
            leafs.append(leaf)

            for i in range(3):
                cleaf = TaxonomyTerm(slug="%s%s" % (leaf.slug, i))
                assert Session.object_session(leaf)
                leaf.append(cleaf)
                db.session.add(cleaf)
                db.session.commit()

        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf00'),
            (3, 'leaf01'),
            (3, 'leaf02'),
            (2, 'leaf1'),
            (3, 'leaf10'),
            (3, 'leaf11'),
            (3, 'leaf12'),
            (2, 'leaf2'),
            (3, 'leaf20'),
            (3, 'leaf21'),
            (3, 'leaf22')
        ]
        
        # move leaf2 to the end of leaf0
        move('leaf2', 'leaf0', -1)
        db.session.commit()
        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf00'),
            (3, 'leaf01'),
            (3, 'leaf02'),
            (3, 'leaf2'),
            (4, 'leaf20'),
            (4, 'leaf21'),
            (4, 'leaf22'),
            (2, 'leaf1'),
            (3, 'leaf10'),
            (3, 'leaf11'),
            (3, 'leaf12'),
        ]

        # move leaf1 to the start of leaf 0
        move('leaf1', 'leaf0', 0)
        db.session.commit()
        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf1'),
            (4, 'leaf10'),
            (4, 'leaf11'),
            (4, 'leaf12'),
            (3, 'leaf00'),
            (3, 'leaf01'),
            (3, 'leaf02'),
            (3, 'leaf2'),
            (4, 'leaf20'),
            (4, 'leaf21'),
            (4, 'leaf22'),
        ]

        # move leaf1 after leaf00
        move('leaf1', 'leaf0', 1)
        db.session.commit()
        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf00'),
            (3, 'leaf1'),
            (4, 'leaf10'),
            (4, 'leaf11'),
            (4, 'leaf12'),
            (3, 'leaf01'),
            (3, 'leaf02'),
            (3, 'leaf2'),
            (4, 'leaf20'),
            (4, 'leaf21'),
            (4, 'leaf22'),
        ]

        # move leaf1 after leaf00
        move('leaf2', 'leaf1', 2)
        db.session.commit()
        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf00'),
            (3, 'leaf1'),
            (4, 'leaf10'),
            (4, 'leaf11'),
            (4, 'leaf2'),
            (5, 'leaf20'),
            (5, 'leaf21'),
            (5, 'leaf22'),
            (4, 'leaf12'),
            (3, 'leaf01'),
            (3, 'leaf02'),
        ]

        # and back
        move('leaf2', 'leaf0', 1)
        db.session.commit()
        assert structure() == [
            (2, 'leaf0'),
            (3, 'leaf00'),
            (3, 'leaf2'),
            (4, 'leaf20'),
            (4, 'leaf21'),
            (4, 'leaf22'),
            (3, 'leaf1'),
            (4, 'leaf10'),
            (4, 'leaf11'),
            (4, 'leaf12'),
            (3, 'leaf01'),
            (3, 'leaf02'),
        ]
