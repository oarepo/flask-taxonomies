# # -*- coding: utf-8 -*-
# """Functional tests using WebTest.
#
# See: http://webtest.readthedocs.org/
# """
"""Functional unit tests using WebTest."""
import json

import pytest
from flask_security import AnonymousUser
from invenio_access import ActionUsers

from tests.testutils import login_user


@pytest.mark.usefixtures("db")
class TestTaxonomyAPI:
    """TaxonomyTerm functional test."""

    def test_list_taxonomies(self, db, client, root_taxonomy,
                             Taxonomy, permissions):
        """Test listing of taxonomies."""
        login_user(client, permissions['taxonomies'])

        additional = Taxonomy(code="additional", extra_data={"extra": "data"})
        db.session.add(additional)
        db.session.commit()

        res = client.get("/taxonomies/")
        jsonres = res.json
        assert {
                   "id": root_taxonomy.id,
                   "code": root_taxonomy.code,
                   "links": {"self": "http://localhost/taxonomies/root/"},
               } in jsonres
        assert {
                   "id": additional.id,
                   "code": additional.code,
                   "extra": "data",
                   "links": {
                       "self": "http://localhost/taxonomies/additional/"},
               } in jsonres

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.get("/taxonomies/")
        jsonres = res.json
        assert jsonres is None
        assert res.status_code == 403

    def test_create_taxonomy(self, client, root_taxonomy,
                             Taxonomy, permissions):
        """Test Taxonomy creation."""
        login_user(client, permissions['taxonomies'])
        res = client.post("/taxonomies/",
                          json={"code": "new", "extra": "new"})

        assert res.status_code == 201
        assert res.headers['Location'] == 'http://localhost/taxonomies/new/'

        retrieved = Taxonomy.query.filter(Taxonomy.code == "new").first()
        assert retrieved is not None
        assert retrieved.extra_data == {"extra": "new"}

        # Test duplicit create fails
        res = client.post("/taxonomies/", json={"code": root_taxonomy.code})
        assert res.status_code == 400

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.post("/taxonomies/", json={"code": "no-root"})
        assert res.status_code == 403

    def test_list_taxonomy_roots(self, client, root_taxonomy,
                                 manager, permissions):
        """Test listing of top-level taxonomy terms."""
        login_user(client, permissions['root-taxo'])

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

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code))
        assert res.status_code == 403

    def test_get_taxonomy_term(self, client, root_taxonomy,
                               manager, permissions):
        """Test getting Term details."""
        login_user(client, permissions['terms'])
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("leafeaf", {"en": "LeafOfLeaf"}, "/root/top1/leaf1")

        res = client.get("/taxonomies/{}/top1/leaf1/"
                         .format(root_taxonomy.code))
        assert res.json["slug"] == "leaf1"
        assert res.json["path"] == "/root/top1/leaf1"
        assert len(res.json["children"]) == 1

        # Test get parent/child details
        res = client.get("/taxonomies/{}/top1/"
                         .format(root_taxonomy.code))
        assert len(res.json['children']) == 1
        assert 'children' in res.json['children'][0]
        assert res.json['children'][0]['children'][0]['slug'] == 'leafeaf'

        # Test get nonexistent path
        res = client.get("/taxonomies/{}/top1/nope/"
                         .format(root_taxonomy.code))
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.get("/taxonomies/{}/top1/leaf1/"
                         .format(root_taxonomy.code))
        assert res.status_code == 403

    def test_term_create(self, root_taxonomy, client,
                         manager, permissions):
        """Test TaxonomyTerm creation."""
        login_user(client, permissions['terms'])
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

        # Test access forbidden for user without permission
        login_user(client, permissions['taxonomies'])
        res = client.post("/taxonomies/{}/"
                          .format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "noperm"})
        assert res.status_code == 403

    def test_taxonomy_delete(self, db, root_taxonomy,
                             manager, client, Taxonomy, permissions):
        """Test deleting whole taxonomy."""
        t = Taxonomy(code="tbd")
        db.session.add(t)
        db.session.commit()

        manager.create("top1", {"en": "Top1"}, "/tbd/")
        manager.create("leaf1", {"en": "Leaf1"}, "/tbd/top1/")

        # Test unauthenticated delete fails
        res = client.delete("/taxonomies/tbd/")
        assert res.status_code == 401

        login_user(client, permissions['taxonomies'])
        res = client.delete("/taxonomies/tbd/")
        assert res.status_code == 204
        assert manager.get_taxonomy("tbd") is None
        assert manager.get_term(t, "leaf1") is None
        assert manager.get_term(t, "top1") is None

        # Delete nonexistent taxonomy fails
        res = client.delete("/taxonomies/nope/")
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['terms'])
        res = client.delete("/taxonomies/root/")
        assert res.status_code == 403

    def test_term_delete(self, root_taxonomy, manager, client, permissions):
        """Test deleting whole term and a subtree."""
        login_user(client, permissions['terms'])
        manager.create("top1", {"en": "Top1"}, "/root/")
        manager.create("leaf1", {"en": "Leaf1"}, "/root/top1/")
        manager.create("top2", {"en": "Top2"}, "/root/")

        client.delete("/taxonomies/root/top1/")
        assert manager.get_term(root_taxonomy, "leaf1") is None
        assert manager.get_term(root_taxonomy, "top1") is None
        assert manager.get_term(root_taxonomy, "top2") is not None

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.delete("/taxonomies/root/top2/")
        assert res.status_code == 403

    def test_taxomomy_update(self, root_taxonomy, client,
                             manager, permissions):
        """Test updating a taxonomy."""
        login_user(client, permissions['root-taxo'])
        res = client.patch("/taxonomies/root/",
                           json={"updated": "yes"})
        assert res.status_code == 200
        assert res.json["updated"] == "yes"
        assert manager.get_taxonomy("root").extra_data == {"updated": "yes"}

        # Test update invalid taxonomy fails
        res = client.patch("/taxonomies/nope/",
                           json={"updated": "yes"})
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.patch("/taxonomies/root/",
                           json={"updated": "yes"})
        assert res.status_code == 403

    def test_term_update(self, root_taxonomy, client, manager, permissions):
        """Test updating a term."""
        login_user(client, permissions['terms'])
        manager.create("term1", {"en": "Term1"}, "/root/")

        res = client.patch("/taxonomies/root/term1/",
                           json={"updated": "yes"})
        assert res.status_code == 200
        assert res.json["updated"] == "yes"
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

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.patch("/taxonomies/root/term1/",
                           json={"updated": "yes"})
        assert res.status_code == 403

    def test_term_move(self, db, root_taxonomy, client, manager,
                       Taxonomy, permissions):
        """Test moving a Taxonomy Term."""
        t = Taxonomy(code="groot")
        db.session.add(t)
        db.session.commit()

        manager.create("term1", {"en": "Term1"}, "/root/")
        term2 = manager.create("term2", {"en": "Term1"}, "/groot/")

        # Allow user terms to move term1
        login_user(client, permissions['terms'])
        res = client.post("/taxonomies/root/term1/",
                          json={"title": {},
                                "slug": "whatever",
                                "move_target": "http://localhost/taxonomies/groot/term2/"})  # noqa
        assert res.status_code == 200
        moved = manager.get_term(t, "term1")
        assert moved is not None
        assert moved.taxonomy == t
        assert moved.is_descendant_of(term2)
        assert moved.tree_path == "/groot/term2/term1"

        # Test move subtree
        res = client.post("/taxonomies/groot/term2/",
                          json={"title": {},
                                "slug": "whatever",
                                "move_target": "http://localhost/taxonomies/root/"})  # noqa
        assert res.status_code == 200

        moved1 = manager.get_term(root_taxonomy, "term2")
        moved2 = manager.get_term(root_taxonomy, "term1")

        assert moved1.tree_path == "/root/term2"
        assert moved2.tree_path == "/root/term2/term1"
        assert moved1.taxonomy == root_taxonomy
        assert moved2.taxonomy == root_taxonomy
        assert moved2.is_descendant_of(moved1)

        # Test move to invalid path fails
        res = client.post("/taxonomies/root/term2/",
                          json={"title": term2.title,
                                "slug": term2.slug,
                                "move_target": "http://localhost/taxonomies/root/somethingbad/"})  # noqa
        assert res.status_code == 400

        # Test move to invalid url prefix fails
        res = client.post("/taxonomies/root/term2/",
                          json={"title": term2.title,
                                "slug": term2.slug,
                                "move_target": "http://localhost/taxi/root/somethinggood/"})  # noqa
        assert res.status_code == 400

        # Test move from invalid source fails
        res = client.post("/taxonomies/root/somethingbad/",
                          json={"title": {},
                                "slug": "whatever",
                                "move_target": "http://localhost/taxonomies/groot/"})  # noqa
        assert res.status_code == 400
