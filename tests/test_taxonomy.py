def taxonomy_test(api):
    tax = api.create_taxonomy(code='test')
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 1
    assert taxonomies == [tax]

    taxonomies = list(api.list_taxonomies(return_descendants_count=True))
    assert taxonomies[0].descendants_count == 0

    api.update_taxonomy(taxonomy='test', extra_data={'a': 'b'})
    api.session.refresh(tax)
    assert tax.extra_data == {'a': 'b'}

    api.delete_taxonomy(tax)
    taxonomies = list(api.list_taxonomies())
    assert len(taxonomies) == 0


def descendants_count_test(api, sample_taxonomy):
    taxonomies = list(api.list_taxonomies(return_descendants_count=True))
    assert taxonomies[0].descendants_count == 3
