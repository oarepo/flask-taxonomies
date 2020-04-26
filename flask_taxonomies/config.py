from flask_taxonomies.constants import INCLUDE_DATA, INCLUDE_ANCESTORS, INCLUDE_URL, INCLUDE_DESCENDANTS_URL

#
# Server name hosting the taxonomies. If not set,
# SERVER_NAME will be used.
#
# FLASK_TAXONOMIES_SERVER_NAME =

#
# Protocol to use in generated urls
#
FLASK_TAXONOMIES_PROTOCOL = 'https'

#
# A prefix on which taxonomies are served
#
FLASK_TAXONOMIES_URL_PREFIX = '/api/1.0/taxonomies/'

#
# A function with signature (obj: [Taxonomy, TaxonomyTerm], representation: Representation)
# that should return processed obj.extra_data as a dictionary.
#
# The default implementation looks at representation.selectors and if set, extracts only those
# json pointers
#
# FLASK_TAXONOMIES_DATA_EXTRACTOR =

FLASK_TAXONOMIES_REPRESENTATION = {
    'minimal': {
        'include': [],
        'exclude': [],
        'selectors': None
    },
    'representation': {
        'include': [INCLUDE_DATA, INCLUDE_ANCESTORS, INCLUDE_URL, INCLUDE_DESCENDANTS_URL],
        'exclude': [],
        'selectors': None
    }
}
