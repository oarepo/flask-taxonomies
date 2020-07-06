from build.lib.flask_taxonomies.constants import INCLUDE_ANCESTORS
from flask_taxonomies.constants import INCLUDE_DATA, INCLUDE_ANCESTORS_HIERARCHY, INCLUDE_URL, INCLUDE_DESCENDANTS_URL, \
    INCLUDE_SLUG, INCLUDE_SELF

#
# Server name hosting the taxonomies. If not set,
# SERVER_NAME will be used.
#
# FLASK_TAXONOMIES_SERVER_NAME =

#
# Protocol to use in generated urls
#
FLASK_TAXONOMIES_SERVER_SCHEME = 'https'

#
# A prefix on which taxonomies are served
#
FLASK_TAXONOMIES_URL_PREFIX = '/api/2.0/taxonomies/'

#
# A function with signature (obj: [Taxonomy, TaxonomyTerm], representation: Representation)
# that should return processed obj.extra_data as a dictionary.
#
# The default implementation looks at representation.select and if set, extracts only those
# json pointers
#
# FLASK_TAXONOMIES_DATA_EXTRACTOR =

FLASK_TAXONOMIES_REPRESENTATION = {
    'minimal': {
        'include': [INCLUDE_SLUG, INCLUDE_SELF],
        'exclude': [],
        'select': None,
        'options': {}
    },
    'representation': {
        'include': [INCLUDE_DATA, INCLUDE_ANCESTORS, INCLUDE_URL, INCLUDE_SELF],
        'exclude': [],
        'select': None,
        'options': {}
    },
    'full': {
        'include': [INCLUDE_DATA, INCLUDE_ANCESTORS, INCLUDE_URL, INCLUDE_DESCENDANTS_URL, INCLUDE_SELF],
        'exclude': [],
        'select': None,
        'options': {}
    }
}

FLASK_TAXONOMIES_MAX_RESULTS_RETURNED = 10000
