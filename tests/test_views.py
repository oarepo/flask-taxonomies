# # -*- coding: utf-8 -*-
# """Functional tests using WebTest.
#
# See: http://webtest.readthedocs.org/
# """
"""Functional unit tests using WebTest."""
import json
import time

import pytest

from tests.testutils import login_user

if False:
    from sqlalchemy import event
    from sqlalchemy.engine import Engine

    @event.listens_for(Engine, "before_cursor_execute")
    def before_cursor_execute(conn, cursor, statement,
                              parameters, context, executemany):
        conn.info.setdefault('query_start_time', []).append(time.time())
        print("Start Query: %s", statement, parameters)

    @event.listens_for(Engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement,
                             parameters, context, executemany):
        total = time.time() - conn.info['query_start_time'].pop(-1)
        print("Query Complete!")
        print("Query Time:", total)


@pytest.mark.usefixtures("db")
class TestTaxonomyViews:
    """TaxonomyTerm functional test."""

    def test_list_taxonomies(self, db, client, root_taxonomy, Taxonomy, permissions):
        """Test listing of taxonomies."""
        login_user(client, permissions['taxonomies'])
        additional = Taxonomy.create_taxonomy(code="additional",
                                              extra_data={"extra": "data"})
        db.session.add(additional)
        db.session.commit()

        res = client.get("/taxonomies/")
        jsonres = res.json
        assert {
                   "id": root_taxonomy.id,
                   "code": root_taxonomy.code,
                   "links": {"self": "http://localhost/taxonomies/root/",
                             "tree": "http://localhost/taxonomies/root/?drilldown=True"},
               } in jsonres
        assert {
                   "id": additional.id,
                   "code": additional.code,
                   "extra": "data",
                   "links": {
                       "self": "http://localhost/taxonomies/additional/",
                       "tree": "http://localhost/taxonomies/additional/?drilldown=True"
                   },
               } in jsonres

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.get("/taxonomies/")
        jsonres = res.json
        assert jsonres is None
        assert res.status_code == 403

    def test_create_taxonomy(self, client, root_taxonomy, Taxonomy, permissions):
        """Test Taxonomy creation."""

        login_user(client, permissions['taxonomies'])

        res = client.post("/taxonomies/",
                          json={"code": "new", "extra": "new"})

        assert res.status_code == 201
        assert res.headers['Location'] == 'http://localhost/taxonomies/new/'
        assert res.json['links']['self'] == 'http://localhost/taxonomies/new/'
        assert res.json['links']['tree'] == 'http://localhost/taxonomies/new/?drilldown=True'

        retrieved = next(Taxonomy.taxonomies(lambda q: q.filter_by(slug="new")))
        assert retrieved is not None
        assert retrieved.extra_data == {"extra": "new"}

        # Test duplicit create fails
        res = client.post("/taxonomies/", json={"code": root_taxonomy.code})
        assert res.status_code == 400

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.post("/taxonomies/", json={"code": "no-root"})
        assert res.status_code == 403

    def test_list_taxonomy_roots(self, client, root_taxonomy, permissions):
        """Test listing of top-level taxonomy terms."""
        login_user(client, permissions['root-taxo'])

        # Test empty taxonomy
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert res.json == []

        root_taxonomy.create_term(slug="top1").create_term(slug="leaf1")
        root_taxonomy.create_term(slug='top2')

        # Test multiple top-level terms
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert len(res.json) == 2
        slugs = [r["slug"] for r in res.json]
        assert "top1" in slugs
        assert "top2" in slugs
        assert "leaf1" not in slugs

        # Test non-existent taxonomy
        login_user(client, permissions['taxonomies'])
        res = client.get("/taxonomies/blah/",
                         headers={'Accept': 'application/json'})
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.get("/taxonomies/{}/".format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert res.status_code == 403

    def test_get_taxonomy_term(self, client, root_taxonomy, permissions):
        """Test getting Term details."""
        login_user(client, permissions['terms'])

        leaf1 = root_taxonomy.create_term(slug="top1").create_term(slug="leaf1")
        leaf1.create_term(slug="leafeaf")

        res = client.get("/taxonomies/{}/top1/leaf1/?drilldown=1"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})

        assert res.json["slug"] == "leaf1"
        assert res.json["path"] == "/top1/leaf1"
        assert len(res.json["children"]) == 1

        assert res.json['links']['self'].endswith(
            '/taxonomies/root/top1/leaf1/')
        assert res.json['links']['tree'].endswith(
            '/taxonomies/root/top1/leaf1/?drilldown=True')

        assert res.json['links']['parent'].endswith(
            '/taxonomies/root/top1/')
        assert res.json['links']['parent_tree'].endswith(
            '/taxonomies/root/top1/?drilldown=True')

        assert 'ancestors' in res.json
        assert len(res.json['ancestors']) == 1
        assert res.json['ancestors'][0] == {
            'level': 1,
            'slug': 'top1'
        }

        assert res.json['level'] == 2

        res_child = res.json["children"][0]
        assert res_child["slug"] == "leafeaf"
        assert res_child["path"] == "/top1/leaf1/leafeaf"

        assert res_child['links']['self'].endswith(
            '/taxonomies/root/top1/leaf1/leafeaf/')
        assert res_child['links']['tree'].endswith(
            '/taxonomies/root/top1/leaf1/leafeaf/?drilldown=True')

        assert 'ancestors' not in res_child

        # Test get parent/child details
        res = client.get("/taxonomies/{}/top1/?drilldown=True"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert len(res.json['children']) == 1
        assert 'children' in res.json['children'][0]
        assert res.json['children'][0]['children'][0]['slug'] == 'leafeaf'

        # Test get nonexistent path
        res = client.get("/taxonomies/{}/top1/nope/"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.get("/taxonomies/{}/top1/leaf1/"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})
        assert res.status_code == 403

    def test_get_taxonomy_term_parent_link(self, client, root_taxonomy, permissions):
        """Test getting Term details."""
        login_user(client, permissions['terms'])

        root_taxonomy.create_term(slug="top1").create_term(slug="leaf1")

        res = client.get("/taxonomies/{}/top1/?drilldown=1"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})

        assert res.json["slug"] == "top1"
        assert res.json["path"] == "/top1"

        assert res.json['links']['self'].endswith(
            '/taxonomies/root/top1/')
        assert res.json['links']['tree'].endswith(
            '/taxonomies/root/top1/?drilldown=True')

        assert res.json['links']['parent'].endswith(
            '/taxonomies/root/')
        assert res.json['links']['parent_tree'].endswith(
            '/taxonomies/root/?drilldown=True')

        res = client.get("/taxonomies/{}/top1/leaf1/?drilldown=1"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})

        assert res.json["slug"] == "leaf1"
        assert res.json["path"] == "/top1/leaf1"

        assert res.json['links']['self'].endswith(
            '/taxonomies/root/top1/leaf1/')
        assert res.json['links']['tree'].endswith(
            '/taxonomies/root/top1/leaf1/?drilldown=True')

        assert res.json['links']['parent'].endswith(
            '/taxonomies/root/top1/')
        assert res.json['links']['parent_tree'].endswith(
            '/taxonomies/root/top1/?drilldown=True')

        res = client.get("/taxonomies/{}/top1/"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})

        assert res.json["slug"] == "top1"
        assert res.json["path"] == "/top1"

        assert res.json['links']['self'].endswith(
            '/taxonomies/root/top1/')
        assert res.json['links']['tree'].endswith(
            '/taxonomies/root/top1/?drilldown=True')

        assert res.json['links']['parent'].endswith(
            '/taxonomies/root/')
        assert res.json['links']['parent_tree'].endswith(
            '/taxonomies/root/?drilldown=True')

        res = client.get("/taxonomies/{}/top1/leaf1/"
                         .format(root_taxonomy.code),
                         headers={'Accept': 'application/json'})

        assert res.json["slug"] == "leaf1"
        assert res.json["path"] == "/top1/leaf1"

        assert res.json['links']['self'].endswith(
            '/taxonomies/root/top1/leaf1/')
        assert res.json['links']['tree'].endswith(
            '/taxonomies/root/top1/leaf1/?drilldown=True')

        assert res.json['links']['parent'].endswith(
            '/taxonomies/root/top1/')
        assert res.json['links']['parent_tree'].endswith(
            '/taxonomies/root/top1/?drilldown=True')

    def test_term_create(self, root_taxonomy, client, permissions):
        """Test TaxonomyTerm creation."""
        login_user(client, permissions['terms'])
        res = client.post("/taxonomies/{}/".format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 201
        assert res.json["slug"] == "leaf-1"
        assert res.headers['location'] == 'http://localhost/taxonomies/{}/leaf-1/'.format(root_taxonomy.code)  # noqa

        created = root_taxonomy.get_term("leaf-1")
        assert created.slug == "leaf-1"
        assert created.tree_id == root_taxonomy.tree_id

        # Test invalid path fails
        res = client.post("/taxonomies/{}/top1/top2/"
                          .format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 400

        # Test create on nested path
        top1 = root_taxonomy.create_term(slug="top1")
        res = client.post("/taxonomies/{}/top1/"
                          .format(root_taxonomy.code),
                          json={"slug": "leaf 2"})
        assert res.status_code == 201

        created = root_taxonomy.get_term("leaf-2")
        assert created.slug == "leaf-2"
        assert created.tree_id == root_taxonomy.tree_id
        assert created.parent == top1
        root_taxonomy.check()

        # Test create duplicit slug creates a new slug
        res = client.post("/taxonomies/{}/top1/".format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "leaf 2"})
        assert res.status_code == 201
        assert res.headers['location'] == \
               'http://localhost/taxonomies/{}/top1/leaf-2-1/'.format(root_taxonomy.code)

        # Test create in non-existent taxonomy fails
        res = client.post("/taxonomies/none/",
                          json={"title": {"en": "Leaf"}, "slug": "leaf 1"})
        assert res.status_code == 404

        # Test create Term with unicode title
        res = client.post("/taxonomies/{}/".format(root_taxonomy.code),
                          json={"title": {"cs": "Příliš žluťoučký kůň úpěl ďábelské ódy."},  # noqa
                                "slug": "kun1"})
        assert res.status_code == 201
        assert res.json["title"]["cs"] == "Příliš žluťoučký kůň úpěl ďábelské ódy."

        # Test access forbidden for user without permission
        login_user(client, permissions['taxonomies'])
        res = client.post("/taxonomies/{}/"
                          .format(root_taxonomy.code),
                          json={"title": {"en": "Leaf"}, "slug": "noperm"})
        assert res.status_code == 403

    def test_taxonomy_delete(self, db, root_taxonomy,
                             client, Taxonomy, TaxonomyTerm,
                             permissions):
        """Test deleting whole taxonomy."""
        root_taxonomy.check()

        t = Taxonomy.create_taxonomy(code="tbd")
        assert t.tree_id != root_taxonomy.tree_id

        t.create_term(slug="top1").create_term(slug="leaf1")

        root_taxonomy.check()
        t.check()

        # Test unauthenticated delete fails
        res = client.delete("/taxonomies/tbd/")
        assert res.status_code == 401

        login_user(client, permissions['taxonomies'])
        res = client.delete("/taxonomies/tbd/")
        assert res.status_code == 204
        assert Taxonomy.get("tbd") is None
        assert TaxonomyTerm.query.filter_by(slug="leaf1").one_or_none() is None
        assert TaxonomyTerm.query.filter_by(slug="top1").one_or_none() is None
        root_taxonomy.check()

        # Delete nonexistent taxonomy fails
        res = client.delete("/taxonomies/nope/")
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['terms'])
        res = client.delete("/taxonomies/root/")
        assert res.status_code == 403

    def test_term_delete(self, root_taxonomy, client, permissions):
        """Test deleting whole term and a subtree."""
        login_user(client, permissions['terms'])
        root_taxonomy.create_term(slug="top1").create_term(slug="leaf1")
        root_taxonomy.create_term(slug="top2")
        root_taxonomy.check()

        client.delete("/taxonomies/root/top1/")
        assert root_taxonomy.get_term("leaf1") is None
        assert root_taxonomy.get_term("top1") is None
        assert root_taxonomy.get_term("top2") is not None
        root_taxonomy.check()

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.delete("/taxonomies/root/top2/")
        assert res.status_code == 403

    def test_taxomomy_update(self, root_taxonomy, client, Taxonomy, permissions):
        """Test updating a taxonomy."""
        login_user(client, permissions['root-taxo'])
        res = client.patch("/taxonomies/root/",
                           json={"updated": "yes"})
        assert res.status_code == 200
        assert res.json["updated"] == "yes"
        assert Taxonomy.get('root').extra_data == {"updated": "yes"}

        # Test update invalid taxonomy fails
        res = client.patch("/taxonomies/nope/",
                           json={"updated": "yes"})
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['noperms'])
        res = client.patch("/taxonomies/root/",
                           json={"updated": "yes"})
        assert res.status_code == 403

    def test_term_update(self, root_taxonomy, client, permissions):
        """Test updating a term."""
        login_user(client, permissions['terms'])
        root_taxonomy.create_term(slug="term1")

        res = client.patch("/taxonomies/root/term1/",
                           json={"updated": "yes"})
        assert res.status_code == 200
        assert res.json["updated"] == "yes"
        assert root_taxonomy.get_term("term1").extra_data == {"updated": "yes"}

        res = client.patch("/taxonomies/root/term1/",
                           json={"title": {"updated": "yes"}})
        assert res.status_code == 200
        assert res.json["title"] == {"updated": "yes"}
        assert root_taxonomy.get_term("term1").extra_data['title'] == {"updated": "yes"}

        # Test update invalid term fails
        res = client.patch("/taxonomies/root/nope/",
                           json={"title": {"updated": "yes"}})
        assert res.status_code == 404

        # Test access forbidden for user without permission
        login_user(client, permissions['root-taxo'])
        res = client.patch("/taxonomies/root/term1/",
                           json={"updated": "yes"})
        assert res.status_code == 403

    def test_term_move(self, db, root_taxonomy, client, Taxonomy, permissions):
        """Test moving a Taxonomy Term."""

        root_taxonomy.create_term(slug="term1")
        term2 = root_taxonomy.create_term(slug="term2")
        term3 = root_taxonomy.create_term(slug="term3")

        # Test move /root/term1 -> /groot/term2/term1
        login_user(client, permissions['terms'])
        res = client.post("/taxonomies/root/term1/",
                          headers={
                              'Destination': "http://localhost/taxonomies/root/term2/",
                              'Content-Type': 'application/vnd.move'
                          })

        assert res.status_code == 200
        moved = root_taxonomy.get_term("term1")
        assert moved is not None
        assert moved.tree_id == root_taxonomy.tree_id
        assert moved.parent == term2
        assert moved.tree_path == "/term2/term1"

        # Test move subtree
        res = client.post("/taxonomies/root/term2/",
                          headers={
                              "Destination": "http://localhost/taxonomies/root/term3/",
                              'Content-Type': 'application/vnd.move'
                          })  # noqa
        assert res.status_code == 200

        moved1 = root_taxonomy.get_term("term2")
        moved2 = root_taxonomy.get_term("term1")

        assert moved1.tree_path == "/term3/term2"
        assert moved2.tree_path == "/term3/term2/term1"
        assert moved1.parent == term3
        assert moved2.parent == term2

        # Test move to invalid path fails
        res = client.post("/taxonomies/root/term2/",
                          headers={
                              "Destination": "http://localhost/taxonomies/root/somethingbad/",
                              'Content-Type': 'application/vnd.move'
                          })  # noqa
        assert res.status_code == 400

        # Test move to invalid url prefix fails
        res = client.post("/taxonomies/root/term2/",
                          headers={
                              "Destination": "http://localhost/taxi/root/somethinggood/",
                              'Content-Type': 'application/vnd.move'
                          })  # noqa
        assert res.status_code == 400

        # Test move from invalid source fails
        res = client.post("/taxonomies/root/somethingbad/",
                          headers={
                              "Destination": "http://localhost/taxonomies/groot/",
                              'Content-Type': 'application/vnd.move'
                          })  # noqa
        assert res.status_code == 400

    @pytest.mark.parametrize('filled_taxonomy',
                             [[1000]],
                             indirect=['filled_taxonomy'])
    def test_large_taxonomy(self, client, filled_taxonomy, permissions):
        """Test listing of top-level taxonomy terms."""
        login_user(client, permissions['root-taxo'])
        t1 = time.time()
        res = client.get(
            "/taxonomies/{}/?drilldown=True".format(filled_taxonomy.code))
        print('Total time', time.time() - t1)
        t1 = time.time()
        print("Request starts")
        res = client.get(
            "/taxonomies/{}/?drilldown=True".format(filled_taxonomy.code),
            headers={'Accept': 'application/json'})
        print('Total time', time.time() - t1)
        assert len(res.json) == 1000
