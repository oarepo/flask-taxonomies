# # -*- coding: utf-8 -*-
# """Functional tests using WebTest.
#
# See: http://webtest.readthedocs.org/
# """
"""Functional unit tests using WebTest."""
import json

import pytest

from flask_taxonomies.models import Taxonomy


@pytest.mark.usefixtures("db")
class TestTaxonomyAPI:
    """TaxonomyTerm functional test."""

    def test_list_taxonomies(self, db, testapp, root_taxonomy):
        """Test listing of taxonomies."""
        additional = Taxonomy(code="additional", extra_data={"extra": "data"})
        db.session.add(additional)
        db.session.commit()

        res = testapp.get("/taxonomies/")
        jsonres = json.loads(res.body)
        assert {
            "id": root_taxonomy.id,
            "code": root_taxonomy.code,
            "extra_data": root_taxonomy.extra_data,
            "links": {"self": "http://localhost/taxonomies/root/"},
        } in jsonres
        assert {
            "id": additional.id,
            "code": additional.code,
            "extra_data": additional.extra_data,
            "links": {"self": "http://localhost/taxonomies/additional/"},
        } in jsonres

    def test_create_taxonomy(self, testapp, root_taxonomy):
        """Test Taxonomy creation."""

        res = testapp.post(
            "/taxonomies/", {"code": "new", "extra_data": '{"extra": "new"}'}
        )

        retrieved = Taxonomy.query.filter(Taxonomy.code == "new").first()
        assert res.status_code == 201
        assert retrieved is not None
        assert retrieved.extra_data == {"extra": "new"}

        # Test putting invalid exxtra data fails
        res = testapp.post(
            "/taxonomies/",
            {"code": "bad", "extra_data": "{'extra': }"},
            expect_errors=True,
        )
        assert res.status_code == 400

        # Test duplicit create fails
        res = testapp.post(
            "/taxonomies/", {"code": root_taxonomy.code}, expect_errors=True
        )
        assert res.status_code == 400

    def test_list_taxonomy_roots(self, testapp, root_taxonomy, manager):
        """Test listing of top-level taxonomy terms."""

        # Test empty taxonomy
        res = testapp.get("/taxonomies/{}/".format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert jsonres == []

        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("top2", {"en": "Top2"}, "/root/")

        # Test multiple top-level terms
        res = testapp.get("/taxonomies/{}/".format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert len(jsonres) == 2
        slugs = [r["slug"] for r in jsonres]
        assert "top1" in slugs
        assert "top2" in slugs
        assert "leaf1" not in slugs

        # Test non-existent taxonomy
        res = testapp.get("/taxonomies/blah/", expect_errors=True)
        assert res.status_code == 404

    def test_get_taxonomy_term(self, testapp, root_taxonomy, manager):
        """Test getting Term details."""
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("leafeaf", {"en": "LeafOfLeaf"}, "/root/top1/leaf1")

        res = testapp.get("/taxonomies/{}/top1/leaf1/".format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert isinstance(jsonres, dict)
        assert jsonres["slug"] == "leaf1"
        assert jsonres["path"] == "/root/top1/leaf1"
        assert len(jsonres["children"]) == 1

        # Test get nonexistent path
        res = testapp.get(
            "/taxonomies/{}/top1/nope/".format(root_taxonomy.code), expect_errors=True
        )
        assert res.status_code == 404

    def test_term_create(self, root_taxonomy, testapp, manager):
        """Test TaxonomyTerm creation."""
        res = testapp.post(
            "/taxonomies/{}/leaf1/".format(root_taxonomy.code),
            {"title": '{"en": "Leaf"}'},
        )
        jsonres = json.loads(res.body)
        assert res.status_code == 201
        assert jsonres["slug"] == "leaf1"

        created = manager.get_term(root_taxonomy, "leaf1")
        assert created.title == {"en": "Leaf"}
        assert created.slug == "leaf1"
        assert created.taxonomy == root_taxonomy

        # Test invalid path fails
        res = testapp.post(
            "/taxonomies/{}/top1/leaf1/".format(root_taxonomy.code),
            {"title": '{"en": "Leaf"}'},
            expect_errors=True,
        )
        assert res.status_code == 400

        # Test create on nested path
        manager.create("top1", {"en": "Top1"}, "/root/")
        res = testapp.post(
            "/taxonomies/{}/top1/leaf2/".format(root_taxonomy.code),
            {"title": '{"en": "Leaf"}'},
        )
        assert res.status_code == 201

        created = manager.get_term(root_taxonomy, "leaf2")
        assert created.title == {"en": "Leaf"}
        assert created.slug == "leaf2"
        assert created.taxonomy == root_taxonomy

        # Test create duplicit slug fails
        res = testapp.post(
            "/taxonomies/{}/leaf2/".format(root_taxonomy.code),
            {"title": '{"en": "Leaf"}'},
            expect_errors=True,
        )
        assert res.status_code == 400

    def test_taxonomy_delete(self, db, root_taxonomy, manager, testapp):
        """Test deleting whole taxonomy."""
        t = Taxonomy(code="tbd")
        db.session.add(t)
        db.session.commit()

        manager.create("top1", {"en": "Top1"}, "/tbd/")
        manager.create("leaf1", {"en": "Leaf1"}, "/tbd/top1/")

        res = testapp.delete("/taxonomies/tbd/")
        assert res.status_code == 204
        assert manager.get_taxonomy("tbd") is None
        assert manager.get_term(t, "leaf1") is None
        assert manager.get_term(t, "top1") is None

        # Delete nonexistent taxonomy fails
        res = testapp.delete("/taxonomies/nope/", expect_errors=True)
        assert res.status_code == 404

    def test_term_delete(self, root_taxonomy, manager, testapp):
        """Test deleting whole term and a subtree."""
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("top2", {"en": "Top2"}, "/root/")

        testapp.delete("/taxonomies/root/top1/")
        assert manager.get_term(root_taxonomy, "leaf1") is None
        assert manager.get_term(root_taxonomy, "top1") is None
        assert manager.get_term(root_taxonomy, "top2") is not None

    def test_taxomomy_update(self, root_taxonomy, testapp, manager):
        """Test updating a taxonomy."""
        res = testapp.patch("/taxonomies/root/", {"extra_data": '{"updated": "yes"}'})
        jsonres = json.loads(res.body)
        assert res.status_code == 200
        assert jsonres["extra_data"] == {"updated": "yes"}
        assert manager.get_taxonomy("root").extra_data == {"updated": "yes"}

        # Test update invalid taxonomy fails
        res = testapp.patch(
            "/taxonomies/nope/",
            {"extra_data": '{"updated": "yes"}'},
            expect_errors=True,
        )
        assert res.status_code == 404

    def test_term_update(self, root_taxonomy, testapp, manager):
        """Test updating a term."""
        manager.create("term1", {"en": "Term1"}, "/root/")

        res = testapp.patch(
            "/taxonomies/root/term1/", {"extra_data": '{"updated": "yes"}'}
        )
        jsonres = json.loads(res.body)
        assert res.status_code == 200
        assert jsonres["extra_data"] == {"updated": "yes"}
        assert manager.get_term(root_taxonomy, "term1").extra_data == {"updated": "yes"}

        res = testapp.patch("/taxonomies/root/term1/", {"title": '{"updated": "yes"}'})
        jsonres = json.loads(res.body)
        assert res.status_code == 200
        assert jsonres["title"] == {"updated": "yes"}
        assert manager.get_term(root_taxonomy, "term1").title == {"updated": "yes"}

        # Test update invalid term fails
        res = testapp.patch(
            "/taxonomies/root/nope/",
            {"title": '{"updated": "yes"}'},
            expect_errors=True,
        )
        assert res.status_code == 404

    def test_term_move(self, db, root_taxonomy, testapp, manager):
        """Test moving a Taxonomy Term."""
        t = Taxonomy(code="groot")
        db.session.add(t)
        db.session.commit()

        manager.create("term1", {"en": "Term1"}, "/root/")
        term2 = manager.create("term2", {"en": "Term1"}, "/groot/")

        # Test move /root/term1 -> /groot/term2/term1
        res = testapp.patch("/taxonomies/root/term1/", {"move_target": "/groot/term2/"})
        assert res.status_code == 200
        moved = manager.get_term(t, "term1")
        assert moved is not None
        assert moved.taxonomy == t
        assert moved.is_descendant_of(term2)
        assert moved.tree_path == "/groot/term2/term1"

        # Test move subtree
        res = testapp.patch("/taxonomies/groot/term2/", {"move_target": "/root/"})
        assert res.status_code == 200

        moved1 = manager.get_term(root_taxonomy, "term2")
        moved2 = manager.get_term(root_taxonomy, "term1")

        assert moved1.tree_path == "/root/term2"
        assert moved2.tree_path == "/root/term2/term1"
        assert moved1.taxonomy == root_taxonomy
        assert moved2.taxonomy == root_taxonomy
        assert moved2.is_descendant_of(moved1)

        # Test move to invalid path fails
        res = testapp.patch(
            "/taxonomies/root/term2/",
            {"move_target": "/root/somethingbad/"},
            expect_errors=True,
        )
        assert res.status_code == 400

        # Test move from invalid source fails
        res = testapp.patch(
            "/taxonomies/root/somethingbad/",
            {"move_target": "/groot/"},
            expect_errors=True,
        )
        assert res.status_code == 404
