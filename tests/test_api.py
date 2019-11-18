# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from flask_taxonomies.models import MovePosition, TaxonomyError
from flask_taxonomies.proxies import current_flask_taxonomies


@pytest.mark.usefixtures("db")
class TestTaxonomyAPI:
    """Taxonomy model tests."""

    def test_create(self, db, Taxonomy, TaxonomyTerm):
        """Test create taxonomy."""
        tax = current_flask_taxonomies.create_taxonomy('code', {'extra': 'data'})
        db.session.add(tax)
        db.session.commit()

        retrieved = Taxonomy(TaxonomyTerm.query.get(tax.id))
        assert retrieved.code == "code"
        assert retrieved.extra_data == {"extra": "data"}

        tax.check()

    def test_taxonomy_list(self, db, root_taxonomy, mkt):
        """Get terms  listassocitated with this taxonomy."""
        taxos = list(current_flask_taxonomies.taxonomy_list())

        assert len(taxos) == 1
        assert taxos[0] == root_taxonomy

        root_taxonomy.check()

    def test_update_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Update Taxonomy extra_data."""
        current_flask_taxonomies.update_taxonomy(root_taxonomy, {"description": "updated"})

        retrieved_root = TaxonomyTerm.query.get(root_taxonomy.id)
        assert retrieved_root.extra_data == {"description": "updated"}

        root_taxonomy.check()

    def test_delete_taxonomy(self, db, root_taxonomy, TaxonomyTerm):
        """Test deleting the whole Taxonomy."""

        leaf = root_taxonomy.create_term(slug="leaf")
        nested = leaf.create_term(slug="nested")

        root_taxonomy.check()

        current_flask_taxonomies.delete_taxonomy(root_taxonomy)

        assert TaxonomyTerm.query.get(root_taxonomy.id) is None
        assert TaxonomyTerm.query.get(leaf.id) is None
        assert TaxonomyTerm.query.get(nested.id) is None


@pytest.mark.usefixtures("db")
class TestTaxonomyTerm:
    """TaxonomyTerm model tests."""

    def test_update_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm):
        """Update TaxonomyTerm extra_data and name."""
        leaf = root_taxonomy.create_term(slug="leaf")

        current_flask_taxonomies.update_term(root_taxonomy, leaf,
                                             {'extra_data': {"description": "updated"}})

        retrieved_root = TaxonomyTerm.query.get(leaf.id)
        assert retrieved_root.extra_data == {"description": "updated"}

        root_taxonomy.check()

    def test_delete_taxonomy_term(self, db, root_taxonomy, TaxonomyTerm, mkt):
        """Delete single TaxonomyTerm term."""
        leaf = root_taxonomy.create_term(slug="leaf")
        root_taxonomy.create_term(slug="leaf2")

        assert list(root_taxonomy.dump()) == mkt('leaf', 'leaf2')

        root_taxonomy.check()

        current_flask_taxonomies.delete_term(root_taxonomy, leaf)

        assert TaxonomyTerm.query.get(leaf.id) is None

        assert list(root_taxonomy.dump()) == mkt('leaf2')

        root_taxonomy.check()

    def test_move_taxonomy_term_inside(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t2 = root_taxonomy.create_term(slug="leaf2")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                           destination_order=MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t2.tree_path,
                                           destination_order=MovePosition.INSIDE)
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

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                           destination_order=MovePosition.INSIDE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt(
            ('leaf2',
             'leaf21', 'leaf22'),
            ('leaf1',
             'leaf11', 'leaf12'),
        )
        current_flask_taxonomies.move_term(root_taxonomy, term_path=t2.tree_path,
                                           destination_order=MovePosition.INSIDE)
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
        current_flask_taxonomies.move_term(root_taxonomy, term_path=t2.tree_path,
                                           target_path=root_taxonomy.code + t1.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                           target_path=root_taxonomy.code + t2.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                           target_path=root_taxonomy.code + t3.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf1', 'leaf3')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t3.tree_path,
                                           target_path=root_taxonomy.code + t1.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf2', 'leaf3', 'leaf1')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t3.tree_path,
                                           target_path=root_taxonomy.code + t2.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf3', 'leaf2', 'leaf1')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                           target_path=root_taxonomy.code + t3.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf3', 'leaf2')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t2.tree_path,
                                           target_path=root_taxonomy.code + t3.tree_path,
                                           destination_order=MovePosition.BEFORE)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

    def test_move_taxonomy_term_after(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="leaf1")
        t2 = root_taxonomy.create_term(slug="leaf2")
        t3 = root_taxonomy.create_term(slug="leaf3")

        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

        current_flask_taxonomies.move_term(root_taxonomy, term_path=t2.tree_path,
                                           target_path=root_taxonomy.code + t1.tree_path,
                                           destination_order=MovePosition.AFTER)
        root_taxonomy.check()
        assert list(root_taxonomy.dump()) == mkt('leaf1', 'leaf2', 'leaf3')

    def test_move_taxonomy_prohibited(self, db, root_taxonomy, mkt):
        t1 = root_taxonomy.create_term(slug="1")
        t11 = t1.create_term(slug="11")
        t12 = t1.create_term(slug="12")

        with pytest.raises(TaxonomyError,
                           match='Can not move term inside, before or after the same term'):
            current_flask_taxonomies.move_term(root_taxonomy, term_path=t1.tree_path,
                                               target_path=root_taxonomy.code + t1.tree_path,
                                               destination_order=MovePosition.INSIDE)
