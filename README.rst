===============================
Flask Taxonomies
===============================

.. image:: https://img.shields.io/github/license/oarepo/flask-taxonomies.svg
        :target: https://github.com/oarepo/flask-taxonomies/blob/master/LICENSE

.. image:: https://img.shields.io/travis/oarepo/flask-taxonomies.svg
        :target: https://travis-ci.org/oarepo/flask-taxonomies

.. image:: https://img.shields.io/coveralls/oarepo/flask-taxonomies.svg
        :target: https://coveralls.io/r/oarepo/flask-taxonomies

Taxonomy trees REST API for Flask Applications


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

Usage
-----

Create taxonomies ::

    curl -X POST \
      http://localhost:5000/taxonomies/vehicle/ \
      -d '{"title": "{\"en\": \"Vehicle\"}", "description": "Some Vehicle"}'

    curl -X POST \
      http://localhost:5000/taxonomies/vehicle/land-vehicle/ \
      -d '{"title": "{\"en\": \"Land Vehicle\"}", "description": "Land Vehicle"}'

    curl -X POST \
      http://localhost:5000/taxonomies/car/ \
      -d '{"title": "{\"en\": \"Vehicle\"}", "description": "Some Vehicle", "attach_to": "land-vehicle"}'


List taxonomies ::

    curl -X GET http://localhost:5000/taxonomies/car/
    > [ { "description": "A Car", "id": 7, "label": "", "path": "vehicle/land-vehicle/car", "slug": "car", "title": "{\"en\": \"Car\"}" } ]

    curl -X GET http://localhost:5000/taxonomies/vehicle/land-vehicle/
    > [ { "children": [ { "description": "A Car", "id": 7, "label": "", "path": "vehicle/land-vehicle/car", "slug": "car", "title": "{\"en\": \"Car\"}" } ], "description": "Some Land Vehicle", "id": 6, "label": "", "path": "vehicle/land-vehicle", "slug": "land-vehicle", "title": "{\"en\": \"Land Vehicle\"}" } ]

Update taxonomy entry ::

    curl -X PATCH \
      http://localhost:5000/taxonomies/vehicle/land-vehicle/ \
      -d '{"description": "A Fancy Land vehicle"}'

Delete taxonomy (or Taxonomy subtree) ::

    curl -X DELETE \
      http://localhost:5000/taxonomies/vehicle/land-vehicle/

Move taxonony (or whole subtree) to another tree (identified by slug) ::

    curl -X POST \
        http://localhost:5000/taxonomies/vehicle/land-vehicle/car/move \
        -d '{"destination":"road-vehicle"}'
