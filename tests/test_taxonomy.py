def taxonomy_test(api):
    tax = api.create_taxonomy(code='test')
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 1
    assert taxonomies == [tax]

    api.update_taxonomy(taxonomy='test', extra_data={'a': 'b'})
    api.session.refresh(tax)
    assert tax.extra_data == {'a': 'b'}

    api.delete_taxonomy(tax)
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 0
