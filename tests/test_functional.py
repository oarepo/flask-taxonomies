# # -*- coding: utf-8 -*-
# """Functional tests using WebTest.
#
# See: http://webtest.readthedocs.org/
# """
"""Functional unit tests using WebTest."""
import json

import pytest


@pytest.mark.usefixtures("db")
class TestTaxonomyAPI:
    """TaxonomyTerm functional test."""

    def test_list_taxonomies(self, db, client, root_taxonomy, Taxonomy):
        """Test listing of taxonomies."""
        additional = Taxonomy(code="additional", extra_data={"extra": "data"})
        db.session.add(additional)
        db.session.commit()

        res = client.get("/taxonomies/")
        jsonres = res.json
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
                   "links": {
                       "self": "http://localhost/taxonomies/additional/"},
               } in jsonres

    def test_create_taxonomy(self, client, root_taxonomy, Taxonomy):
        """Test Taxonomy creation."""

        res = client.post("/taxonomies/",
                          json={"code": "new",
                                "extra_data": {"extra": "new"}})

        assert res.status_code == 201
        assert res.headers['Location'] == 'http://localhost/taxonomies/new/'

        retrieved = Taxonomy.query.filter(Taxonomy.code == "new").first()
        assert retrieved is not None
        assert retrieved.extra_data == {"extra": "new"}

        # Test putting invalid exxtra data fails
        res = client.post("/taxonomies/",
                          json={"code": "bad", "extra_data": "{'extra'}"})
        assert res.status_code == 422

        # Test duplicit create fails
        res = client.post("/taxonomies/", json={"code": root_taxonomy.code})
        assert res.status_code == 400

    def test_list_taxonomy_roots(self, client, root_taxonomy, manager):
        """Test listing of top-level taxonomy terms."""

        # Test empty taxonomy
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code))
        assert res.json == []

        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("top2", {"en": "Top2"}, "/root/")

        # Test multiple top-level terms
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code))
        assert len(res.json) == 2
        slugs = [r["slug"] for r in res.json]
        assert "top1" in slugs
        assert "top2" in slugs
        assert "leaf1" not in slugs

        # Test non-existent taxonomy
        res = client.get("/taxonomies/blah/")
        assert res.status_code == 404

    def test_get_taxonomy_term(self, client, root_taxonomy, manager):
        """Test getting Term details."""
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("leafeaf", {"en": "LeafOfLeaf"}, "/root/top1/leaf1")

        res = client.get("/taxonomies/{}/top1/leaf1/"
                         .format(root_taxonomy.code))
        assert res.json["slug"] == "leaf1"
        assert res.json["path"] == "/root/top1/leaf1"
        assert len(res.json["children"]) == 1

        # Test get nonexistent path
        res = client.get("/taxonomies/{}/top1/nope/"
                         .format(root_taxonomy.code))
        assert res.status_code == 404

    def test_term_create(self, root_taxonomy, client, manager):
        """Test TaxonomyTerm creation."""
        res = client.post("/taxonomies/{}/".format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 201
        assert res.json["slug"] == "leaf-1"
        assert res.headers['location'] == 'http://localhost/taxonomies/{}/leaf-1/'.format(root_taxonomy.code)  # noqa

        created = manager.get_term(root_taxonomy, "leaf-1")
        assert created.title == {"en": "Leaf"}
        assert created.slug == "leaf-1"
        assert created.taxonomy == root_taxonomy

        # Test invalid path fails
        res = client.post("/taxonomies/{}/top1/top2/"
                          .format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 400

        # Test create on nested path
        top1 = manager.create("top1", {"en": "Top1"}, "/root/")
        res = client.post("/taxonomies/{}/top1/"
                          .format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 2"})
        assert res.status_code == 201

        created = manager.get_term(root_taxonomy, "leaf-2")
        assert created.title == {"en": "Leaf"}
        assert created.slug == "leaf-2"
        assert created.taxonomy == root_taxonomy
        assert created.is_descendant_of(top1)

        # Test create duplicit slug fails
        res = client.post("/taxonomies/{}/top1/".format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 2"})
        assert res.status_code == 400

        # Test create in non-existent taxonomy fails
        res = client.post("/taxonomies/none/",
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 404

    def test_taxonomy_delete(self, db, root_taxonomy,
                             manager, client, Taxonomy):
        """Test deleting whole taxonomy."""
        t = Taxonomy(code="tbd")
        db.session.add(t)
        db.session.commit()

        manager.create("top1", {"en": "Top1"}, "/tbd/")
        manager.create("leaf1", {"en": "Leaf1"}, "/tbd/top1/")

        res = client.delete("/taxonomies/tbd/")
        assert res.status_code == 204
        assert manager.get_taxonomy("tbd") is None
        assert manager.get_term(t, "leaf1") is None
        assert manager.get_term(t, "top1") is None

        # Delete nonexistent taxonomy fails
        res = client.delete("/taxonomies/nope/")
        assert res.status_code == 404

    def test_term_delete(self, root_taxonomy, manager, client):
        """Test deleting whole term and a subtree."""
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("top2", {"en": "Top2"}, "/root/")

        client.delete("/taxonomies/root/top1/")
        assert manager.get_term(root_taxonomy, "leaf1") is None
        assert manager.get_term(root_taxonomy, "top1") is None
        assert manager.get_term(root_taxonomy, "top2") is not None

    def test_taxomomy_update(self, root_taxonomy, client, manager):
        """Test updating a taxonomy."""
        res = client.patch("/taxonomies/root/",
                           json={"extra_data": {"updated": "yes"}})
        assert res.status_code == 200
        assert res.json["extra_data"] == {"updated": "yes"}
        assert manager.get_taxonomy("root").extra_data == {"updated": "yes"}

        # Test update invalid taxonomy fails
        res = client.patch("/taxonomies/nope/",
                           json={"extra_data": {"updated": "yes"}})
        assert res.status_code == 404

    def test_term_update(self, root_taxonomy, client, manager):
        """Test updating a term."""
        manager.create("term1", {"en": "Term1"}, "/root/")

        res = client.patch("/taxonomies/root/term1/",
                           json={"extra_data": {"updated": "yes"}})
        assert res.status_code == 200
        assert res.json["extra_data"] == {"updated": "yes"}
        assert manager.get_term(root_taxonomy, "term1") \
                      .extra_data == {"updated": "yes"}

        res = client.patch("/taxonomies/root/term1/",
                           json={"title": {"updated": "yes"}})
        assert res.status_code == 200
        assert res.json["title"] == {"updated": "yes"}
        assert manager.get_term(root_taxonomy, "term1") \
                      .title == {"updated": "yes"}

        # Test update invalid term fails
        res = client.patch("/taxonomies/root/nope/",
                           json={"title": {"updated": "yes"}})
        assert res.status_code == 404

    def test_term_move(self, db, root_taxonomy, client, manager, Taxonomy):
        """Test moving a Taxonomy Term."""
        t = Taxonomy(code="groot")
        db.session.add(t)
        db.session.commit()

        manager.create("term1", {"en": "Term1"}, "/root/")
        term2 = manager.create("term2", {"en": "Term1"}, "/groot/")

        # Test move /root/term1 -> /groot/term2/term1
        res = client.patch("/taxonomies/root/term1/",
                           data={"move_target": "/groot/term2/"})
        assert res.status_code == 200
        moved = manager.get_term(t, "term1")
        assert moved is not None
        assert moved.taxonomy == t
        assert moved.is_descendant_of(term2)
        assert moved.tree_path == "/groot/term2/term1"

        # Test move subtree
        res = client.patch("/taxonomies/groot/term2/",
                           data={"move_target": "/root/"})
        assert res.status_code == 200

        moved1 = manager.get_term(root_taxonomy, "term2")
        moved2 = manager.get_term(root_taxonomy, "term1")

        assert moved1.tree_path == "/root/term2"
        assert moved2.tree_path == "/root/term2/term1"
        assert moved1.taxonomy == root_taxonomy
        assert moved2.taxonomy == root_taxonomy
        assert moved2.is_descendant_of(moved1)

        # Test move to invalid path fails
        res = client.patch("/taxonomies/root/term2/",
                           data={"move_target": "/root/somethingbad/"})
        assert res.status_code == 400

        # Test move from invalid source fails
        res = client.patch("/taxonomies/root/somethingbad/",
                           data={"move_target": "/groot/"})
        assert res.status_code == 404
