# -*- coding: utf-8 -*-
"""Model unit tests."""
import pytest
from sqlalchemy.exc import IntegrityError


@pytest.mark.usefixtures("db")
class TestTaxonomyManager:
    """Taxonomy manager tests."""

    def test_create_term(self, db, root_taxonomy, manager,
                         Taxonomy, TaxonomyTerm):
        """Taxonomy Term creation tests."""

        # Test create valid term
        created = manager.create(
            slug="child",
            extra_data={"extra": "data"},
            title={"en": "Leaf"},
            path="/root/",
        )

        assert isinstance(created, TaxonomyTerm)
        assert created.slug == "child"
        assert created.extra_data["extra"] == "data"
        assert created.parent.root_of == root_taxonomy

        # Test create term on non-existing path fails
        with pytest.raises(AttributeError):
            created = manager.create(
                slug="child", title={"en": "Leaf"}, path="/root/non-existent/"
            )

        # Test create term in non-existing taxonomy fails
        with pytest.raises(AttributeError):
            created = manager.create(slug="child",
                                     title={"en": "Leaf"},
                                     path="/nope/")

        # Test create nested term
        leaf = TaxonomyTerm(slug="leaf",
                            title={"en": "Leaf"})
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        subleaf = manager.create(
            slug="subleaf", title={"en": "Leaf"}, path="/root/leaf/"
        )

        assert subleaf.slug == "subleaf"
        assert subleaf.tree_id == root_taxonomy.root.tree_id
        assert subleaf.is_descendant_of(leaf)
        assert subleaf.is_descendant_of(root_taxonomy.root)

        # Test create duplicit term in same taxonomy fails
        with pytest.raises(IntegrityError):
            manager.create(slug="subleaf",
                           title={"en": "Leaf"},
                           path="/root/leaf/")
        db.session.rollback()

        # Test create duplicit term in different taxonomy
        different = Taxonomy.create(db.session, code="different")
        db.session.commit()

        created = manager.create(
            slug="subleaf", title={"en": "Leaf"}, path="/different/"
        )

        assert created.slug == subleaf.slug
        assert created.id != subleaf.id
        assert created.tree_id == different.root.tree_id

    def test_get_taxonomy(self, root_taxonomy, manager, Taxonomy):
        """Test get Taxonomy by codename."""
        retrieved = manager.get_taxonomy("root")

        assert isinstance(retrieved, Taxonomy)
        assert retrieved == root_taxonomy

        # Test nonexistent taxonomy
        retrieved = manager.get_taxonomy(code="nothing")
        assert retrieved is None

    def test_get_taxonomy_roots(self, root_taxonomy, manager):
        """Test get top-level taxonomy terms."""
        topterm = manager.create(slug="top",
                                 title={"en": "Top"},
                                 path="/root/")
        manager.create(slug="leaf", title={"en": "Leaf"}, path="/root/top/")

        # Test single toplevel term
        root = list(manager.get_taxonomy_roots(root_taxonomy))
        assert len(root) == 1
        assert root[0] == topterm

        # Test multiple toplevel terms
        anothertopterm = manager.create(slug="anothertop",
                                        title={"en": "Another Top"},
                                        path="/root/")
        roots = list(manager.get_taxonomy_roots(root_taxonomy))
        assert len(roots) == 2
        assert topterm in roots
        assert anothertopterm in roots

    def test_get_term(self, db, root_taxonomy, manager,
                      Taxonomy, TaxonomyTerm):
        """Test get terms associtated by taxonomy and slug."""
        leaf = TaxonomyTerm(slug="leaf",
                            title={"en": "Leaf"})
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        # Test simple slug get
        retrieved = manager.get_term(root_taxonomy, "leaf")
        assert retrieved == leaf

        # Test duplicit slug get
        second_taxonomy = Taxonomy.create(db.session, code="second")
        db.session.commit()

        dup_leaf = TaxonomyTerm(
            slug="leaf", title={"en": "Leaf"}
        )
        second_taxonomy.append(dup_leaf)
        db.session.add(dup_leaf)
        db.session.commit()

        retrieved = manager.get_term(second_taxonomy, "leaf")
        assert retrieved == dup_leaf
        assert retrieved != leaf

        # Test get invalid term fails
        retrieved = manager.get_term(root_taxonomy, "notterm")
        assert retrieved is None

    def test_get_from_path(self, db, root_taxonomy, manager,
                           Taxonomy, TaxonomyTerm):
        """Test get taxonomy and term by its path in a taxonomy tree."""
        leaf = TaxonomyTerm(slug="leaf",
                            title={"en": "Leaf"})
        root_taxonomy.append(leaf)
        db.session.add(leaf)
        db.session.commit()

        subleaf = TaxonomyTerm(slug="subleaf",
                               title={"en": "Leaf"},
                               parent=leaf)
        db.session.add(leaf)
        db.session.commit()

        subsubleaf = TaxonomyTerm(slug="subsubleaf",
                                  title={"en": "Leaf"},
                                  parent=subleaf)
        db.session.add(leaf)
        db.session.commit()

        # Test get root returns both None
        root, term = manager.get_from_path("/")
        assert root is None
        assert term is None

        # Test get taxonomy only
        root, term = manager.get_from_path("/root")
        assert root == root_taxonomy
        assert term is None

        # Test get both, toplevel term
        root, term = manager.get_from_path("/root/leaf")
        assert root == root_taxonomy
        assert term == leaf

        # Test get both, nested term
        root, term = manager.get_from_path("/root/leaf/subleaf/subsubleaf")
        assert root == root_taxonomy
        assert term == subsubleaf

        # Test get duplicit term
        different = Taxonomy.create(db.session, code="different")
        db.session.commit()

        created = manager.create(slug="leaf",
                                 title={"en": "Leaf"},
                                 path="/different/")

        root, term = manager.get_from_path("/different/leaf")
        assert root == different
        assert term == created
        assert term != leaf

    def test_move_tree(self, db, root_taxonomy, manager,
                       Taxonomy, TaxonomyTerm):
        """Test moving a tree into another tree."""
        manufacturer = Taxonomy.create(db.session, code="manufacturer")
        root_taxonomy.append(manufacturer)
        item = TaxonomyTerm(slug="item",
                            title={"en": "Item"})
        root_taxonomy.append(item)
        vehicle = TaxonomyTerm(slug="vehicle",
                               title={"en": "Vehicle"})
        root_taxonomy.append(vehicle)

        db.session.add(manufacturer)
        db.session.add(item)
        db.session.add(vehicle)
        db.session.commit()

        car = TaxonomyTerm(slug="car",
                           title={"en": "car"})
        root_taxonomy.append(car)
        car.parent = vehicle
        db.session.add(car)
        db.session.commit()

        suv = TaxonomyTerm(slug="suv",
                           title={"en": "SUV"})
        root_taxonomy.append(suv)
        suv.parent = car
        db.session.add(suv)
        db.session.commit()

        # Test move in same taxonomy
        manager.move_tree("/root/vehicle/car/", "/root/item/")

        car = TaxonomyTerm.get_by_id(car.id)
        suv = TaxonomyTerm.get_by_id(suv.id)
        assert car.taxonomy == root_taxonomy
        assert suv.taxonomy == root_taxonomy
        assert car.is_descendant_of(item)
        assert suv.is_descendant_of(car)

        # Test move between taxonomies
        manager.move_tree("/root/vehicle/", "/manufacturer/")

        vehicle = TaxonomyTerm.get_by_id(vehicle.id)
        assert vehicle.taxonomy == manufacturer

        # Test move to invalid target path
        with pytest.raises(AttributeError):
            manager.move_tree("/manufacturer/vehicle/", "/dump/")

        # Test move from invalid source path
        with pytest.raises(AttributeError):
            manager.move_tree("/nope/vehicle/", "/dump/")

    def test_delete_tree(self, db, root_taxonomy, manager, TaxonomyTerm):
        """Test deleting existing TaxonomyTerm tree."""
        vehicle = TaxonomyTerm(slug="vehicle",
                               title={"en": "Vehicle"})
        root_taxonomy.append(vehicle)
        db.session.add(vehicle)
        db.session.commit()

        car = TaxonomyTerm(slug="car",
                           title={"en": "car"},
                           parent=vehicle)
        db.session.add(car)
        db.session.commit()

        suv = TaxonomyTerm(slug="suv",
                           title={"en": "SUV"},
                           parent=car)
        db.session.add(suv)
        db.session.commit()

        assert car.is_descendant_of(vehicle)
        assert suv.is_descendant_of(car)

        manager.delete_tree("/root/vehicle/car/")

        assert TaxonomyTerm.get_by_id(vehicle.id) == vehicle
        assert TaxonomyTerm.get_by_id(car.id) is None
        assert TaxonomyTerm.get_by_id(suv.id) is None

        # Test delete invalid Term path fails
        with pytest.raises(AttributeError):
            manager.delete_tree("/root/")

        with pytest.raises(AttributeError):
            manager.delete_tree("/root/invalid/")
