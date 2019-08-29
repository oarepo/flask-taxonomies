import pytest
from sqlalchemy.orm.exc import NoResultFound

from flask_taxonomies.utils import find_in_json, find_in_json_contains


@pytest.mark.usefixtures("db")
class TestFindInJson:
    """Taxonomy model tests."""

    def test_successful_find(self, db, root_taxonomy):
        """"""
        if db.engine.name != "postgresql":
            pytest.skip("unsupported configuration")

        leaf = root_taxonomy.create_term(slug="leaf",
                                         extra_data={"title": [
                                             {"lang": "cze",
                                              "value": "Filozofie"}
                                         ]
                                         }
                                         )

        db.session.refresh(root_taxonomy)
        db.session.refresh(leaf)

        query = find_in_json("Filozofie", root_taxonomy, tree_address=("title", 0, "value"))
        matched_taxonomy = query.one()
        assert matched_taxonomy.extra_data["title"][0]["value"] == "Filozofie"

    def test_unsuccessful_find(self, db, root_taxonomy):
        """"""

        if db.engine.name != "postgresql":
            pytest.skip("unsupported configuration")

        leaf = root_taxonomy.create_term(slug="leaf",
                                         extra_data={"title": [
                                             {"lang": "cze",
                                              "value": "Filozofie"}
                                         ]
                                         }
                                         )

        db.session.refresh(root_taxonomy)
        db.session.refresh(leaf)

        query = find_in_json("Invalid query", root_taxonomy, tree_address=("title", 0, "value"))
        with pytest.raises(NoResultFound):
            query.one()

    def test_successful_find_contains(self, db, root_taxonomy):
        """"""
        if db.engine.name != "postgresql":
            pytest.skip("unsupported configuration")

        leaf = root_taxonomy.create_term(slug="leaf",
                                         extra_data={
                                             "title": [
                                                 {
                                                     "lang": "cze",
                                                     "value": "Filozofie"
                                                 }
                                             ],
                                             "aliases": [
                                                 "alias",
                                                 "other_item",
                                                 "other_item_2"
                                             ]
                                         }
                                         )

        db.session.refresh(root_taxonomy)
        db.session.refresh(leaf)

        query = find_in_json_contains("alias", root_taxonomy, tree_address="aliases")
        matched_taxonomy = query.one()
        assert matched_taxonomy.extra_data["title"][0]["value"] == "Filozofie"

    def test_unsuccessful_find_contains(self, db, root_taxonomy):
        """"""

        if db.engine.name != "postgresql":
            pytest.skip("unsupported configuration")

        leaf = root_taxonomy.create_term(slug="leaf",
                                         extra_data={
                                             "title": [
                                                 {
                                                     "lang": "cze",
                                                     "value": "Filozofie"
                                                 }
                                             ],
                                             "aliases": [
                                                 "alias",
                                                 "other_item",
                                                 "other_item_2"
                                             ]
                                         }
                                         )

        db.session.refresh(root_taxonomy)
        db.session.refresh(leaf)

        query = find_in_json_contains("Invalid query", root_taxonomy, tree_address="aliases")
        with pytest.raises(NoResultFound):
            query.one()
