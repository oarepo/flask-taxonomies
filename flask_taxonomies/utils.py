import sqlalchemy

from flask_taxonomies.models import Taxonomy, TaxonomyTerm
from flask_taxonomies.term_identification import TermIdentification


def to_json(api, taxonomy_or_term):
    if isinstance(taxonomy_or_term, Taxonomy):
        elements = api.list_taxonomy(
            taxonomy_or_term,
            status_cond=sqlalchemy.sql.true()
        )
    else:
        elements = api.descendants_or_self(
            TermIdentification(term=taxonomy_or_term),
            status_cond=sqlalchemy.sql.true()
        )
    stack = None
    min_level = None

    for el in elements:
        level = len(el.slug.split('/'))
        if stack is None:
            stack = [{
                'children': []
            }]
            min_level = level
        data = {
            **(el.extra_data or {}),
            'slug': el.slug,
            'level': el.level,
            'status': el.status.value,
            'children': []
        }
        if el.obsoleted_by_id:
            data['obsoleted_by'] = el.obsoleted_by.slug
        idx = level - min_level
        stack[idx]['children'].append(data)
        if idx + 1 == len(stack):
            stack.append(None)
        stack[idx + 1] = data
    return stack[0]['children']
