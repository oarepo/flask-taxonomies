# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest

from flask_taxonomies.models import Taxonomy


@pytest.mark.usefixtures("db")
class TestTaxonomy:
    """Taxonomy Trees tests."""

    def test_get_by_id(self, db, root_taxonomy):
        """Get Taxonomy Tree Items by ID."""
        leaf = Taxonomy(
            slug="leaf", title='{"en": "Leaf"}', description="Taxonomy leaf term"
        )

        db.session.add(leaf)
        db.session.commit()

        retrieved_root = Taxonomy.get_by_id(root_taxonomy.id)
        assert retrieved_root == root_taxonomy
        retrieved_leaf = Taxonomy.get_by_id((leaf.id))
        assert retrieved_leaf == leaf

    def test_get_by_slug(self, db, root_taxonomy):
        """Get Taxonomy Tree Items by ID."""
        leaf = Taxonomy(
            slug="leaf", title='{"en": "Leaf"}', description="Taxonomy leaf term"
        )

        db.session.add(leaf)
        db.session.commit()

        retrieved_root = Taxonomy.get_by_slug("root")
        assert retrieved_root == root_taxonomy
        retrieved_leaf = Taxonomy.get_by_slug(("leaf"))
        assert retrieved_leaf == leaf

    def test_insert_term(self, db, root_taxonomy):
        """Insert Taxonomy term into a tree."""
        leaf = Taxonomy(
            slug="leaf",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )

        db.session.add(leaf)
        db.session.commit()
        print(root_taxonomy.drilldown_tree())
        assert leaf.is_descendant_of(root_taxonomy)

    def test_update_taxonomy(self, db, root_taxonomy):
        """Update Taxonomy description and name."""
        root_taxonomy.description = "updated"
        root_taxonomy.slug = "updatev1"
        root_taxonomy.title = '{"en": "orig", "_":"update"}'

        db.session.add(root_taxonomy)
        db.session.commit()

        retrieved_root = Taxonomy.get_by_id(root_taxonomy.id)
        assert retrieved_root.description == "updated"
        assert retrieved_root.slug == "updatev1"
        assert retrieved_root.title == '{"en": "orig", "_":"update"}'

    def test_move_tree(self, db, root_taxonomy):
        """Move existing Taxonomy tree under another tree."""
        vehicle = Taxonomy(
            slug="vehicle",
            title='{"en": "vehicle"}',
            description="Vehicle",
            parent_id=root_taxonomy.id,
        )
        db.session.add(vehicle)
        db.session.commit()

        car = Taxonomy(slug="car", title='{"en": "car"}', description="Car")
        db.session.add(car)
        db.session.commit()

        suv = Taxonomy(
            slug="suv", title='{"en": "SUV"}', description="SUV", parent_id=car.id
        )
        db.session.add(suv)
        db.session.commit()

        assert vehicle.is_descendant_of(root_taxonomy)
        assert not vehicle.is_ancestor_of(car)
        assert not vehicle.is_ancestor_of(suv)

        car.move_inside(vehicle.id)

        db.session.add(car)
        db.session.commit()

        assert vehicle.is_ancestor_of(car)
        assert vehicle.is_ancestor_of(suv)
        assert car.is_descendant_of(vehicle)
        assert suv.is_descendant_of(car)

    def test_delete_taxonomy(self, db, root_taxonomy):
        """Delete single Taxonomy term."""
        leaf = Taxonomy(
            slug="leaf",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        assert root_taxonomy.is_ancestor_of(leaf)

        db.session.delete(leaf)
        db.session.commit()

        assert not root_taxonomy.is_ancestor_of(leaf)
        assert not leaf.is_descendant_of(root_taxonomy)

    def test_delete_tree(self, db, root_taxonomy):
        """Move existing Taxonomy tree under another tree."""
        vehicle = Taxonomy(
            slug="vehicle",
            title='{"en": "vehicle"}',
            description="Vehicle",
            parent_id=root_taxonomy.id,
        )
        db.session.add(vehicle)
        db.session.commit()

        car = Taxonomy(
            slug="car", title='{"en": "car"}', description="Car", parent_id=vehicle.id
        )
        db.session.add(car)
        db.session.commit()

        suv = Taxonomy(
            slug="suv", title='{"en": "SUV"}', description="SUV", parent_id=car.id
        )
        db.session.add(suv)
        db.session.commit()

        assert vehicle.is_descendant_of(root_taxonomy)
        assert car.is_descendant_of(vehicle)
        assert suv.is_descendant_of(car)

        db.session.delete(car)
        db.session.commit()

        assert vehicle.is_descendant_of(root_taxonomy)
        assert not car.is_descendant_of(vehicle)
        assert not suv.is_descendant_of(vehicle)
