import enum
import logging

import sqlalchemy.dialects
from sqlalchemy import Column, Integer, String, JSON, ForeignKey, Index, Enum, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from flask_taxonomies.fields import SlugType, PostgresSlugType

logger = logging.getLogger('taxonomies')


class TaxonomyError(Exception):
    pass


Base = declarative_base()


class Taxonomy(Base):
    __tablename__ = 'taxonomy_taxonomy'

    id = Column(Integer, primary_key=True, autoincrement=True)
    code = Column(String(256), unique=True, index=True)
    url = Column(String(1024), unique=True, index=True)
    """
    Custom url of the taxonomy. If not set, the url is supposed to be 
    <FLASK_TAXONOMIES_SERVER_NAME or SERVER_NAME>/api/2.0/taxonomies/<name>
    """
    extra_data = Column(JSON().with_variant(
        sqlalchemy.dialects.postgresql.JSONB, 'postgresql'))
    terms = relationship("TaxonomyTerm", cascade="all, delete", lazy="dynamic")

    def __str__(self):
        return 'Taxonomy[{}]'.format(self.code)

    def __repr__(self):
        return str(self)


class TermStatusEnum(enum.Enum):
    alive = 'A'
    """
    Alive taxonomy terms
    """

    deleted = 'D'
    """
    Taxonomy terms that have been deleted but should be kept in the database
    """

    delete_pending = 'd'
    """
    Taxonomy term that is in process of deletion. When its busy_count reaches 0,
    it will be permanently removed from the database
    """


class TaxonomyTerm(Base):
    __tablename__ = 'taxonomy_term'

    id = Column(Integer, primary_key=True, autoincrement=True)
    slug = Column(SlugType(1024).with_variant(PostgresSlugType(), 'postgresql'),
                  unique=False, index=True)
    extra_data = Column(JSON().with_variant(
        sqlalchemy.dialects.postgresql.JSONB, 'postgresql'))
    level = Column(Integer)

    parent_id = Column(Integer, ForeignKey(__tablename__ + '.id'))
    parent = relationship("TaxonomyTerm", back_populates="children",
                          remote_side=id, foreign_keys=parent_id)
    children = relationship("TaxonomyTerm", back_populates="parent",
                            lazy="dynamic", foreign_keys=parent_id,
                            order_by=slug)

    taxonomy_id = Column(Integer, ForeignKey(Taxonomy.__tablename__ + '.id'))
    taxonomy = relationship("Taxonomy", back_populates="terms")

    busy_count = Column(Integer, default=0)
    obsoleted_by_id = Column(Integer, ForeignKey(__tablename__ + '.id'))
    obsoleted_by = relationship("TaxonomyTerm", back_populates="obsoletes",
                                remote_side=id, foreign_keys=obsoleted_by_id)
    obsoletes = relationship("TaxonomyTerm", back_populates="obsoleted_by",
                             lazy="dynamic", foreign_keys=obsoleted_by_id)
    status = Column(Enum(TermStatusEnum), default=TermStatusEnum.alive, nullable=False)

    __table_args__ = (
        Index('index_term_slug', slug, postgresql_using="gist"),
        UniqueConstraint(taxonomy_id, slug, name='unique_taxonomy_slug')
    )

    def __str__(self):
        return 'TaxonomyTerm[tax {}, lev {}, slug {}]'.format(
            self.taxonomy.code, self.level, self.slug)

    def __repr__(self):
        return str(self)
