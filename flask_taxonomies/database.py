# -*- coding: utf-8 -*-
"""Database module, including the SQLAlchemy database object and DB-related utilities."""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy_mptt import mptt_sessionmaker


class MpttSQLAlchemy(SQLAlchemy):
    """A custom SQLAlchemy with MPTT session manager."""

    def create_session(self, options):
        """Override the original session factory creation."""
        session = super().create_session(options)
        # Use wrapper from sqlalchemy_mptt that manage tree tables
        return mptt_sessionmaker(session)
