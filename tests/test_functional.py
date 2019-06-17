# -*- coding: utf-8 -*-
"""Functional tests using WebTest.

See: http://webtest.readthedocs.org/
"""
import json

import pytest
from webtest import AppError
from werkzeug.exceptions import BadRequest

from flask_taxonomies.models import Taxonomy
from flask_taxonomies.views import slug_path_parent, slug_path_validator, slug_validator


@pytest.mark.usefixtures("db")
class TestTaxonomy:
    """Taxonomy functional test."""

    def test_slug_valdiator(self, root_taxonomy):
        """Returns BadRequest on invalid/non-existent slugs."""
        with pytest.raises(BadRequest):
            slug_validator("nonexistent-slug")

        assert slug_validator("root") is None

    def test_slug_path_validator(self, db, root_taxonomy):
        """Returns BadRequest on invalid/non-existent paths."""
        leaf = Taxonomy(
            slug="valid-path",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        with pytest.raises(BadRequest):
            slug_path_validator("root/invalid-path")

        assert slug_path_validator("root/valid-path") is None

    def test_slug_path_parent(self, db, root_taxonomy):
        """Returns last component of slug path as Taxonomy instance."""
        leaf = Taxonomy(
            slug="valid-path",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        returned = slug_path_parent("root/valid-path")
        assert returned == returned

    def test_taxonomy_list(self, db, root_taxonomy, testapp):
        """Test listing of taxonomies."""
        leaf = Taxonomy(
            slug="valid-path",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        expected_root = {
            "description": "Taxonomy root term",
            "path": "root",
            "slug": "root",
            "id": 1,
            "label": "<Taxonomy(root)>",
            "title": '{"en": "Root"}',
        }

        expected_leaf = {
            "description": "Taxonomy leaf term",
            "path": "root/valid-path",
            "slug": "valid-path",
            "id": 2,
            "label": "<Taxonomy(valid-path)>",
            "title": '{"en": "Leaf"}',
        }
        expected_fulltree = expected_root.copy()
        expected_fulltree.update({"children": [expected_leaf]})

        # List top-level Taxonomy trees
        res = testapp.get("/taxonomies/")
        jsonres = json.loads(res.body)
        assert jsonres == [expected_root]

        # List full Taxonomy tree terms
        res = testapp.get("/taxonomies/root/")
        jsonres = json.loads(res.body)
        assert jsonres == [expected_fulltree]

    def test_taxonomy_create(self, root_taxonomy, testapp):
        """Test Taxonomy creation."""
        newtitle = {"en": "NEW"}

        # Create on path
        resp = testapp.post("/taxonomies/root/new/", {"title": json.dumps(newtitle)})
        assert resp.status_code == 201

        created: Taxonomy = Taxonomy.get_by_slug("new")
        assert created.is_descendant_of(root_taxonomy)
        assert created.title == json.dumps(newtitle)

        # Create and attach to
        resp = testapp.post(
            "/taxonomies/new2/",
            {"title": json.dumps(newtitle), "attach_to": root_taxonomy.slug},
        )
        assert resp.status_code == 201

        created: Taxonomy = Taxonomy.get_by_slug("new2")
        assert created.is_descendant_of(root_taxonomy)
        assert created.title == json.dumps(newtitle)

        # Both create on path and attach to fails
        with pytest.raises(AppError) as ae:
            testapp.post(
                "/taxonomies/root/new3/",
                {"title": json.dumps(newtitle), "attach_to": root_taxonomy.slug},
            )
            assert ae.error.code == 400

    def test_taxonomy_delete(self, db, root_taxonomy, testapp):
        """Test Taxonomy deletion."""
        leaf = Taxonomy(
            slug="valid-path",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        # Delete leaf
        resp = testapp.delete("/taxonomies/valid-path/")
        assert resp.status_code == 204

        assert Taxonomy.get_by_slug("valid-path") is None

        leaf = Taxonomy(
            slug="valid-path",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        # Delete tree
        resp = testapp.delete("/taxonomies/root/")
        assert resp.status_code == 204

        assert Taxonomy.get_by_slug("valid-path") is None
        assert Taxonomy.get_by_slug("root") is None

    def test_taxonomy_patch(self, root_taxonomy, testapp):
        """Test update Taxonomy node."""
        newtitle = json.dumps({"en": "patched"})
        newdesc = "Patched"

        resp = testapp.patch(
            "/taxonomies/root/", {"title": newtitle, "description": newdesc}
        )
        assert resp.status_code == 200

        patched = Taxonomy.get_by_slug("root")
        assert patched.title == newtitle
        assert patched.description == newdesc

    def test_taxonomy_move(self, db, root_taxonomy, testapp):
        """Test move ops on Taxonomy nodes.

                   11
        root - 1 <       ==>  root - 1 - 11 - 12
                   12
        """
        leaf = Taxonomy(
            slug="1",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=root_taxonomy.id,
        )
        db.session.add(leaf)
        db.session.commit()

        subleaf1 = Taxonomy(
            slug="11",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=leaf.id,
        )
        subleaf2 = Taxonomy(
            slug="12",
            title='{"en": "Leaf"}',
            description="Taxonomy leaf term",
            parent_id=leaf.id,
        )
        db.session.add_all([subleaf1, subleaf2])
        db.session.commit()

        assert not subleaf2.is_descendant_of(subleaf1)

        resp = testapp.post("/taxonomies/root/1/12/move", {"destination": "11"})
        assert resp.status_code == 200

        moved: Taxonomy = Taxonomy.get_by_slug("12")
        assert moved.is_descendant_of(Taxonomy.get_by_slug("11"))
