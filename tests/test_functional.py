# # -*- coding: utf-8 -*-
# """Functional tests using WebTest.
#
# See: http://webtest.readthedocs.org/
# """
import json

import pytest

from flask_taxonomies.models import Taxonomy


# from webtest import AppError
#
# from flask_taxonomies.models import TaxonomyTerm
# from flask_taxonomies.views import slug_path_parent, slug_path_validator, slug_validator


@pytest.mark.usefixtures("db")
class TestTaxonomy:
    """TaxonomyTerm functional test."""

    def test_list_taxonomies(self, db, testapp, root_taxonomy):
        """Test listing of taxonomies."""
        additional = Taxonomy(code='additional', extra_data={'extra': 'data'})
        db.session.add(additional)
        db.session.commit()

        res = testapp.get('/taxonomies/')
        jsonres = json.loads(res.body)
        assert {'id': root_taxonomy.id, 'code': root_taxonomy.code, 'extra_data': root_taxonomy.extra_data} in jsonres
        assert {'id': additional.id, 'code': additional.code, 'extra_data': additional.extra_data} in jsonres

    def test_create_taxonomy(self, testapp, root_taxonomy):
        """Test Taxonomy creation."""

        res = testapp.post('/taxonomies/', {'code': 'new', 'extra_data': '{"extra": "new"}'})

        retrieved = Taxonomy.query.filter(Taxonomy.code == 'new').first()
        assert res.status_code == 201
        assert retrieved is not None
        assert retrieved.extra_data == {'extra': 'new'}

        # Test putting invalid exxtra data fails
        res = testapp.post('/taxonomies/', {'code': 'bad', 'extra_data': "{'extra': }"}, expect_errors=True)
        assert res.status_code == 400

        # Test duplicit create fails
        res = testapp.post('/taxonomies/', {'code': root_taxonomy.code}, expect_errors=True)
        assert res.status_code == 400

    def test_list_taxonomy_roots(self, testapp, root_taxonomy, manager):
        """Test listing of top-level taxonomy terms."""

        # Test empty taxonomy
        res = testapp.get('/taxonomies/{}/'.format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert jsonres == []

        manager.create('top1', {'en': 'Top1'}, '/root/')
        manager.create('leaf1', {'en': 'Leaf1'}, '/root/top1/')
        manager.create('top2', {'en': 'Top2'}, '/root/')

        # Test multiple top-level terms
        res = testapp.get('/taxonomies/{}/'.format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert len(jsonres) == 2
        slugs = [r['slug'] for r in jsonres]
        assert 'top1' in slugs
        assert 'top2' in slugs
        assert 'leaf1' not in slugs

        # Test non-existent taxonomy
        res = testapp.get('/taxonomies/blah/', expect_errors=True)
        assert res.status_code == 404

    def test_get_taxonomy_term(self, testapp, root_taxonomy, manager):
        """Test getting Term details."""
        manager.create('top1', {'en': 'Top1'}, '/root/')
        manager.create('leaf1', {'en': 'Leaf1'}, '/root/top1/')
        manager.create('leafeaf', {'en': 'LeafOfLeaf'}, '/root/top1/leaf1')

        res = testapp.get('/taxonomies/{}/top1/leaf1/'.format(root_taxonomy.code))
        jsonres = json.loads(res.body)
        assert isinstance(jsonres, dict)
        assert jsonres['slug'] == 'leaf1'
        assert jsonres['path'] == '/root/top1/leaf1'
        assert len(jsonres['children']) == 1

        # Test get nonexistent path
        res = testapp.get('/taxonomies/{}/top1/nope/'.format(root_taxonomy.code), expect_errors=True)
        assert res.status_code == 404

    def test_term_create(self, root_taxonomy, testapp, manager):
        """Test TaxonomyTerm creation."""
        res = testapp.post('/taxonomies/{}/leaf1/'.format(root_taxonomy.code), {'title': '{"en": "Leaf"}'})
        jsonres = json.loads(res.body)
        assert res.status_code == 201
        assert jsonres['slug'] == 'leaf1'

        created = manager.get_term(root_taxonomy, 'leaf1')
        assert created.title == {'en': 'Leaf'}
        assert created.slug == 'leaf1'
        assert created.taxonomy == root_taxonomy

        # Test invalid path fails
        res = testapp.post('/taxonomies/{}/top1/leaf1/'.format(root_taxonomy.code), {'title': '{"en": "Leaf"}'},
                           expect_errors=True)
        assert res.status_code == 400

        # Test create on nested path
        manager.create('top1', {'en': 'Top1'}, '/root/')
        res = testapp.post('/taxonomies/{}/top1/leaf2/'.format(root_taxonomy.code), {'title': '{"en": "Leaf"}'})
        assert res.status_code == 201

        created = manager.get_term(root_taxonomy, 'leaf2')
        assert created.title == {'en': 'Leaf'}
        assert created.slug == 'leaf2'
        assert created.taxonomy == root_taxonomy

        # Test create duplicit slug fails
        res = testapp.post('/taxonomies/{}/leaf2/'.format(root_taxonomy.code), {'title': '{"en": "Leaf"}'},
                           expect_errors=True)
        assert res.status_code == 400

    def test_taxonomy_delete(self, db, root_taxonomy, manager, testapp):
        """Test deleting whole taxonomy."""
        t = Taxonomy(code='tbd')
        db.session.add(t)
        db.session.commit()

        manager.create('top1', {'en': 'Top1'}, '/tbd/')
        manager.create('leaf1', {'en': 'Leaf1'}, '/tbd/top1/')

        res = testapp.delete('/taxonomies/tbd/')
        assert res.status_code == 204
        assert manager.get_taxonomy('tbd') is None
        assert manager.get_term(t, 'leaf1') is None
        assert manager.get_term(t, 'top1') is None

        # Delete nonexistent taxonomy fails
        res = testapp.delete('/taxonomies/nope/', expect_errors=True)
        assert res.status_code == 404

    def test_term_delete(self, root_taxonomy, manager, testapp):
        manager.create('top1', {'en': 'Top1'}, '/root/')
        manager.create('leaf1', {'en': 'Leaf1'}, '/root/top1/')
        manager.create('top2', {'en': 'Top2'}, '/root/')

        testapp.delete('/taxonomies/root/top1/')
        assert manager.get_term(root_taxonomy, 'leaf1') is None
        assert manager.get_term(root_taxonomy, 'top1') is not None
        assert manager.get_term(root_taxonomy, 'top2') is not None

