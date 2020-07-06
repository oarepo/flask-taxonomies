#!/bin/bash

cd flask_taxonomies

export FLASK_APP=../example/app.py 

flask db migrate --directory=alembic "$@"
