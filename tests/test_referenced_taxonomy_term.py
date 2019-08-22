from jsonresolver import JSONResolver


def test_referenced_taxonomy_term(db, root_taxonomy, mkt):
    """Get terms  listassocitated with this taxonomy."""

    leaf = root_taxonomy.create_term(slug="leaf")
    nested = leaf.create_term(slug="nested")

    db.session.refresh(root_taxonomy)
    db.session.refresh(leaf)
    db.session.refresh(nested)

    jsonRes = JSONResolver(entry_point_group='invenio_records.jsonresolver')
    document = jsonRes.resolve("http://localhost/api/taxonomies/root/leaf")
    assert document == {
        'descendants_count': 1.0,
        'id': leaf.id,
        'links': {'parent': 'http://localhost/taxonomies/root/',
                  'parent_tree': 'http://localhost/taxonomies/root/?drilldown=True',
                  'self': 'http://localhost/taxonomies/root/leaf/',
                  'tree': 'http://localhost/taxonomies/root/leaf/?drilldown=True'},
        'path': '/leaf',
        'slug': 'leaf',
        'level': 1
    }
