# -*- coding: utf-8 -*-
"""Database module for database models."""
# Support both Invenio and Flask databases
try:
    from invenio_db import db as _db
except ImportError:
    _db = None

db=_db
