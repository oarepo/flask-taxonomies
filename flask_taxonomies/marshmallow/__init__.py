# -*- coding: utf-8 -*-
"""Flask Taxonomies Marshmallow schemas."""
from invenio_records_rest.schemas.fields import SanitizedUnicode, PersistentIdentifier
from marshmallow.fields import Nested


class TaxonomyLinksSchemaV1():
    self = SanitizedUnicode(required=False)
    tree = SanitizedUnicode(required=False)


class TaxonomySchemaV1Mixin():
    """Taxonomy schema."""
    id = PersistentIdentifier(required=False)
    slug = SanitizedUnicode(required=False)
    path = SanitizedUnicode(required=False)
    links = Nested(TaxonomyLinksSchemaV1)


__all__ = ('TaxonomySchemaV1Mixin',)
