def taxonomy_test(api):
    tax = api.create_taxonomy(code='test')
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 1
    assert taxonomies == [tax]

    api.delete_taxonomy(tax)
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 0
