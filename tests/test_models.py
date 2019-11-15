# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from flask_taxonomies.models import MovePosition, TaxonomyError


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

        tax.check()

    def test_get_terms(self, db, root_taxonomy, mkt):
        """Get terms  listassocitated with this taxonomy."""

        leaf = root_taxonomy.create_term(slug="leaf")
        nested = leaf.create_term(slug="nested")

        db.session.refresh(root_taxonomy)
        db.session.refresh(leaf)
        db.session.refresh(nested)

        assert list(root_taxonomy.dump()) == mkt(('leaf', 'nested'))

        terms = list(root_taxonomy.terms)
        assert terms == [leaf, nested]

        root_taxonomy.check()

    def test_update_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Update Taxonomy extra_data."""
        root_taxonomy.update(extra_data={"description": "updated"})

        retrieved_root = TaxonomyTerm.query.get(root_taxonomy.id)
        assert retrieved_root.extra_data == {"description": "updated"}

        root_taxonomy.check()

    def test_delete_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Test deleting the whole Taxonomy."""

        leaf = root_taxonomy.create_term(slug="leaf")
        nested = leaf.create_term(slug="nested")

        root_taxonomy.check()

        db.session.delete(root_taxonomy)
        db.session.commit()

        assert TaxonomyTerm.query.get(root_taxonomy.id) is None
        assert TaxonomyTerm.query.get(leaf.id) is None
        assert TaxonomyTerm.query.get(nested.id) is None


@pytest.mark.usefixtures("db")
class TestTaxonomyTerm:
    """TaxonomyTerm model tests."""

    def test_get_by_id(self, db, root_taxonomy, TaxonomyTerm):
        """Get TaxonomyTerm Tree Items by ID."""
        leaf = root_taxonomy.create_term(slug="leaf")

        retrieved_leaf = TaxonomyTerm.query.get(leaf.id)
        assert retrieved_leaf == leaf

        # Test get invalid id
        retrieved_leaf = TaxonomyTerm.query.get(12345)
        assert retrieved_leaf is None
        root_taxonomy.check()

    def test_update_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm):
        """Update TaxonomyTerm extra_data and name."""
        leaf = root_taxonomy.create_term(slug="leaf")

        leaf.update(extra_data={"description": "updated"})

        retrieved_root = TaxonomyTerm.query.get(leaf.id)
        assert retrieved_root.extra_data == {"description": "updated"}

        root_taxonomy.check()

    def test_term_tree_path(self, db, root_taxonomy, TaxonomyTerm):
        """Test getting full path of a Term."""
        leaf = root_taxonomy.create_term(slug="leaf")
        nested = leaf.create_term(slug="nested")

        assert leaf.tree_path == "/leaf"
        assert nested.tree_path == "/leaf/nested"

        root_taxonomy.check()

    def test_delete_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm, mkt):
        """Delete single TaxonomyTerm term."""
        leaf = root_taxonomy.create_term(slug="leaf")
        root_taxonomy.create_term(slug="leaf2")

        assert list(root_taxonomy.dump()) == mkt('leaf', 'leaf2')

        root_taxonomy.check()

        leaf.delete()

        assert TaxonomyTerm.query.get(leaf.id) is None

        assert list(root_taxonomy.dump()) == mkt('leaf2')

        root_taxonomy.check()

    def test_term_order(self, db, root_taxonomy):
        root_taxonomy.create_term(slug="leaf1")
        root_taxonomy.create_term(slug="leaf2")

        assert list(root_taxonomy.dump()) == [
            ('root', 1, 1, 6, 0),
            ('leaf1', 2, 2, 3, 0),
            ('leaf2', 2, 4, 5, 1),
        ]

        root_taxonomy.check()

    @pytest.mark.parametrize('filled_taxonomy',
                             [[1000]],
                             indirect=['filled_taxonomy'])
    def test_large_taxonomy(self, db, filled_taxonomy):
        assert filled_taxonomy.terms.count() == 1000

    def test_move_taxonomy_term_inside(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t2 = root_taxonomy.create_term(slug="leaf2")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2')

        t1.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1')

        t2.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2')

    def test_move_taxonomy_term_with_children_inside(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t1.create_term(slug="leaf11")
        t1.create_term(slug="leaf12")
        t2 = root_taxonomy.create_term(slug="leaf2")
        t2.create_term(slug="leaf21")
        t2.create_term(slug="leaf22")

        root_taxonomy.check()
        print(mkt(
            ('leaf1',
             'leaf11', 'leaf12'),
            ('leaf2',
             'leaf21', 'leaf22')))
        assert list(root_taxonomy.dump()) == mkt(
            ('leaf1',
             'leaf11', 'leaf12'),
            ('leaf2',
             'leaf21', 'leaf22'))

        t1.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('leaf2',
             'leaf21', 'leaf22'),
            ('leaf1',
             'leaf11', 'leaf12'),
        )
        t2.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('leaf1',
             'leaf11', 'leaf12'),
            ('leaf2',
             'leaf21', 'leaf22'))

    def test_move_taxonomy_term_before(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t2 = root_taxonomy.create_term(slug="leaf2")
        t3 = root_taxonomy.create_term(slug="leaf3")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')
        t2.move(t1, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        t1.move(t2, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

        t1.move(t3, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        t3.move(t1, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf3', 'leaf1')

        t3.move(t2, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf3', 'leaf2', 'leaf1')

        t1.move(t3, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf3', 'leaf2')

        t2.move(t3, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

    def test_move_taxonomy_term_after(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t2 = root_taxonomy.create_term(slug="leaf2")
        t3 = root_taxonomy.create_term(slug="leaf3")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

        t2.move(t1, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

        t1.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        t1.move(t3, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf3', 'leaf1')

        t3.move(t1, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        t3.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf3', 'leaf1')

        t2.move(t1, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf3', 'leaf1', 'leaf2')

        t3.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

    def test_move_taxonomy_term_before_with_children(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t1.create_term(slug="11")
        t1.create_term(slug="12")
        t2 = root_taxonomy.create_term(slug="2")
        t2.create_term(slug="21")
        t2.create_term(slug="22")
        t3 = root_taxonomy.create_term(slug="3")
        t3.create_term(slug="31")
        t3.create_term(slug="32")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

        t2.move(t1, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', '22'), ('1', '11', '12'), ('3', '31', '32'))

        t3.move(t1, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', '22'), ('3', '31', '32'), ('1', '11', '12'))

        t1.move(t2, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

    def test_move_taxonomy_term_after_with_children(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t1.create_term(slug="11")
        t1.create_term(slug="12")
        t2 = root_taxonomy.create_term(slug="2")
        t2.create_term(slug="21")
        t2.create_term(slug="22")
        t3 = root_taxonomy.create_term(slug="3")
        t3.create_term(slug="31")
        t3.create_term(slug="32")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

        t1.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', '22'), ('1', '11', '12'), ('3', '31', '32'))

        t2.move(t3, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('3', '31', '32'), ('2', '21', '22'))

        t3.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

    def test_move_taxonomy_term_inside_child(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t1.create_term(slug="11")
        t1.create_term(slug="12")
        t2 = root_taxonomy.create_term(slug="2")
        t2.create_term(slug="21")
        t2.create_term(slug="22")
        t3 = root_taxonomy.create_term(slug="3")
        t3.create_term(slug="31")
        t3.create_term(slug="32")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

        t1.move(t2, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', '22', ('1', '11', '12')), ('3', '31', '32'))

        t2.move(t3, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', '31', '32', ('2', '21', '22', ('1', '11', '12'))))

        t1.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', '31', '32', ('2', '21', '22')), ('1', '11', '12'))

        t2.move(t1, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', '31', '32'), ('1', '11', '12', ('2', '21', '22')))

        t2.move(t3, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', '31', '32', ('2', '21', '22')), ('1', '11', '12'))

        t2.move(root_taxonomy, MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', '31', '32'), ('1', '11', '12'), ('2', '21', '22'))

    def test_move_taxonomy_term_before_child(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t1.create_term(slug="11")
        t1.create_term(slug="12")
        t2 = root_taxonomy.create_term(slug="2")
        t21 = t2.create_term(slug="21")
        t22 = t2.create_term(slug="22")
        t3 = root_taxonomy.create_term(slug="3")
        t31 = t3.create_term(slug="31")
        t3.create_term(slug="32")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

        t1.move(t21, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', ('1', '11', '12'), '21', '22'), ('3', '31', '32'))

        db.session.begin_nested()

        t3.move(t22, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', ('1', '11', '12'), '21', ('3', '31', '32'), '22'))

        db.session.rollback()

        t2.move(t31, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('3', ('2', ('1', '11', '12'), '21', '22'), '31', '32'))

        t1.move(t3, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('3', ('2', '21', '22'), '31', '32'))

        t2.move(t3, MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

    def test_move_taxonomy_term_after_child(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t1.create_term(slug="11")
        t1.create_term(slug="12")
        t2 = root_taxonomy.create_term(slug="2")
        t21 = t2.create_term(slug="21")
        t22 = t2.create_term(slug="22")
        t3 = root_taxonomy.create_term(slug="3")
        t31 = t3.create_term(slug="31")
        t32 = t3.create_term(slug="32")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

        t1.move(t21, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', ('1', '11', '12'), '22'), ('3', '31', '32'))

        t3.move(t22, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', ('1', '11', '12'), '22', ('3', '31', '32')))

        t31.move(t22, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', ('1', '11', '12'), '22', '31', ('3', '32')))

        t3.move(t21, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', ('3', '32'), ('1', '11', '12'), '22', '31'))

        t1.move(t2, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', ('3', '32'), '22', '31'), ('1', '11', '12'))

        t3.move(t1, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('2', '21', '22', '31'), ('1', '11', '12'), ('3', '32'))

        t2.move(t1, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22', '31'), ('3', '32'))

        t31.move(t32, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '32', '31'))

        t32.move(t31, MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('1', '11', '12'), ('2', '21', '22'), ('3', '31', '32'))

    def test_move_taxonomy_prohibited(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t11 = t1.create_term(slug="11")
        t12 = t1.create_term(slug="12")

        with pytest.raises(TaxonomyError,
                           match='Can not move term inside, before or after the same term'):
            t1.move(t1, MovePosition.INSIDE)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t11, MovePosition.INSIDE)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t11, MovePosition.BEFORE)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t11, MovePosition.AFTER)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t12, MovePosition.INSIDE)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t12, MovePosition.BEFORE)

        with pytest.raises(TaxonomyError,
                           match='Can not move a term inside its own descendants'):
            t1.move(t12, MovePosition.AFTER)
