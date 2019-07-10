===============================
Flask Taxonomies
===============================

.. image:: https://img.shields.io/github/license/oarepo/flask-taxonomies.svg
        :target: https://github.com/oarepo/flask-taxonomies/blob/master/LICENSE

.. image:: https://img.shields.io/travis/oarepo/flask-taxonomies.svg
        :target: https://travis-ci.org/oarepo/flask-taxonomies

.. image:: https://img.shields.io/coveralls/oarepo/flask-taxonomies.svg
        :target: https://coveralls.io/r/oarepo/flask-taxonomies

.. image:: https://img.shields.io/pypi/v/flask-taxonomies.svg
        :target: https://pypi.org/pypi/flask-taxonomies


TaxonomyTerm trees REST API for Flask Applications


Quickstart
----------

Run the following commands to bootstrap your environment ::

    git clone https://github.com/oarepo/flask_taxonomies
    cd flask_taxonomies
    pip install -r requirements/dev.txt

Once you have installed your DBMS, run the following to create your app's
database tables and perform the initial migration ::

    flask db init
    flask db migrate
    flask db upgrade
    flask run


Deployment
----------

To deploy::

    export FLASK_ENV=production
    export FLASK_DEBUG=0
    export DATABASE_URL="<YOUR DATABASE URL>"
    flask run       # start the flask server

In your production environment, make sure the ``FLASK_DEBUG`` environment
variable is unset or is set to ``0``.

Python Usage
------------

    >>> from flask_taxonomies.managers import TaxonomyManager
    >>> from flask_taxonomies.models import Taxonomy, TaxonomyTerm
    >>> # To create Taxonomy:
    >>> t = Taxonomy(code='taxcode')
    >>> # To create TaxonomyTerm
    >>> m = TaxonomyManager()
    >>> term = m.create('slug', title={'en': 'Tax Term'}, path='/taxcode/taxterm', extra_data={})
    >>> # To get taxonomy by code
    >>> t = m.get_taxonomy('taxcode')
    >>> # To list taxonomy top-level terms
    >>> terms = list(m.get_taxonomy_roots(t))
    >>> # To get term by taxonomy and slug
    >>> term = m.get_term(t, 'taxcode')
    >>> # To get term from taxonomy path
    >>> t, term = manager.get_from_path('/taxcode/taxterm')
    >>> # To move term to a different path
    >>> m.move_tree('/taxcode/taxterm/', '/anothertax/otherterm/') # moves term subtree to '/anothertax/otherterm/taxterm/'
    >>> # To delete term and its descendants
    >>> m.delete_tree('/taxcode/taxterm/')
    >>> # To update Taxonomy/TaxonomyTerm
    >>> t.update(extra_data={'updated': true})
    >>> # To delete Taxonomy (including all related terms) or a single TaxonomyTerm
    >>> db.session.delete(t)

REST API Usage
-----

To list available taxonomies ::

    curl -X GET http://localhost:5000/taxonomies/
    > [{'code': ..., 'extra_data': ...}, ...]

To create taxonomy ::

    curl -X POST \
      http://localhost:5000/taxonomies/ \
      -d '{"code": "...", "extra_data": "{...}"}'

To list top-level terms in a taxonomy ::

    curl -X GET http://localhost:5000/taxonomies/<taxonomy-code>/
    > [{'slug': ..., ...}, {'slug': ..., ...}, ...]

To get Taxonomy Term details ::

    curl -X GET http://localhost:5000/taxonomies/<taxonomy-code>/<taxonomy-term-path>/
    > {'slug': ..., 'title': ..., 'extra_data', ..., 'children': [...], ...}

Delete taxonomy (including all its terms) ::

    curl -X DELETE \
      http://localhost:5000/taxonomies/<taxonomy-code>

Delete taxonomy term (including all its childrens) ::

    curl -X DELETE \
      http://localhost:5000/taxonomies/<taxonomy-code>/<taxonomy-term-path>/

Update taxonomy extra data ::

    curl -X PATCH \
        http://localhost:5000/taxonomies/<taxonomy-code>/ \
        -d '{"extra_data":"{...}"}'

Update taxonomy term data ::

    curl -X PATCH \
        http://localhost:5000/taxonomies/<taxonomy-code>/<taxonomy-term-path>/ \
        -d '{"title":"{...}", "extra_data":"{...}"}'

Move taxonomy term (or whole term subtree) to another location ::

    curl -X PATCH \
        http://localhost:5000/taxonomies/<taxonomy-code>/<taxonomy-term-path>/ \
        -d '{"move_target":"/<target-taxonomy-code>/<target-taxonomy-term-path>/"}'
