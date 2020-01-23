from jsonresolver import JSONResolver

from flask_taxonomies.proxies import current_flask_taxonomies


def test_redis(db, root_taxonomy, mkt):
    """Get terms  listassocitated with this taxonomy."""

    leaf = root_taxonomy.create_term(slug="leaf")
    nested = leaf.create_term(slug="nested")

    db.session.refresh(root_taxonomy)
    db.session.refresh(leaf)
    db.session.refresh(nested)

    jsonRes = JSONResolver(entry_point_group='invenio_records.jsonresolver')
    document = jsonRes.resolve("http://taxonomy-server.com/api/taxonomies/root/leaf")
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

    # change the document directly in the database
    leaf.extra_data = {
        'title': 'a title'
    }
    db.session.add(leaf)
    db.session.commit()

    # the document must be the original one - coming from redis
    document = jsonRes.resolve("http://taxonomy-server.com/api/taxonomies/root/leaf")
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

    # change the document via api
    current_flask_taxonomies.update_term(root_taxonomy, leaf, {
        'extra_data': {'title': 'a title'}
    })
    document = jsonRes.resolve("http://taxonomy-server.com/api/taxonomies/root/leaf")
    assert document == {
        'descendants_count': 1.0,
        'id': leaf.id,
        'title': 'a title',
        'links': {'parent': 'http://localhost/taxonomies/root/',
                  'parent_tree': 'http://localhost/taxonomies/root/?drilldown=True',
                  'self': 'http://localhost/taxonomies/root/leaf/',
                  'tree': 'http://localhost/taxonomies/root/leaf/?drilldown=True'},
        'path': '/leaf',
        'slug': 'leaf',
        'level': 1
    }
