def taxonomy_delete_test(api, client, test_taxonomy):
    resp = client.delete('/api/2.0/taxonomies/test')
    assert resp.status_code == 204
    resp = client.get('/api/2.0/taxonomies/test')
    assert resp.status_code == 404
