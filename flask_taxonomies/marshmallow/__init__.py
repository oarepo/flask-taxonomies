# -*- coding: utf-8 -*-
"""Flask Taxonomies Marshmallow schemas."""
from invenio_records_rest.schemas import StrictKeysMixin
from invenio_records_rest.schemas.fields import SanitizedUnicode, PersistentIdentifier
from marshmallow import pre_load, ValidationError
from marshmallow.fields import Nested
from sqlalchemy.orm.exc import NoResultFound

from flask_taxonomies.models import Taxonomy, TaxonomyTerm
from flask_taxonomies.views import url_to_path


class TaxonomyLinksSchemaV1(StrictKeysMixin):
    self = SanitizedUnicode(required=False)
    tree = SanitizedUnicode(required=False)


class TaxonomySchemaV1(StrictKeysMixin):
    """Taxonomy schema."""
    id = PersistentIdentifier(required=False)
    slug = SanitizedUnicode(required=False)
    path = SanitizedUnicode(required=False)
    links = Nested(TaxonomyLinksSchemaV1, required=False)
    ref = SanitizedUnicode(required=False, dump_to='$ref', load_from='$ref')

    @pre_load
    def convert_ref(self, in_data, **kwargs):
        ref = None
        if '$ref' in in_data:
            ref = in_data['$ref']
        elif 'links' in in_data:
            ref = (in_data['links'] or {}).get('self', None)
        if not ref:
            raise ValidationError('Either links or $ref must be provided for a Taxonomy record')  # noqa

        path = url_to_path(ref)
        try:
            tax, term = Taxonomy.find_taxonomy_and_term(path)
        except NoResultFound:
            raise ValidationError('Taxonomy $ref link is invalid: {}'.format(ref))  # noqa

        if not tax:
            raise ValidationError('Taxonomy $ref link is invalid: {}'.format(ref))  # noqa

        for k, v in term.extra_data.items():
            in_data[k] = v

        in_data["id"] = term.id
        in_data["slug"] = term.slug
        in_data["path"] = term.tree_path
        in_data["links"] = dict()
        in_data["links"]["self"] = term.link_self
        in_data["links"]["self"] = term.link_tree

        return in_data


__all__ = ('TaxonomySchemaV1',)
