import logging

from blinker import Namespace

logger = logging.getLogger('taxonomies')

taxonomy_signals = Namespace()

# signals emitted by REST methods
before_taxonomy_created = taxonomy_signals.signal('before-taxonomy-created')
after_taxonomy_created = taxonomy_signals.signal('after-taxonomy-created')

before_taxonomy_updated = taxonomy_signals.signal('before-taxonomy-updated')
after_taxonomy_updated = taxonomy_signals.signal('after-taxonomy-updated')

before_taxonomy_deleted = taxonomy_signals.signal('before-taxonomy-deleted')
after_taxonomy_deleted = taxonomy_signals.signal('after-taxonomy-deleted')

before_taxonomy_term_created = taxonomy_signals.signal('before-taxonomy-term-created')
after_taxonomy_term_created = taxonomy_signals.signal('after-taxonomy-term-created')

before_taxonomy_term_updated = taxonomy_signals.signal('before-taxonomy-term-updated')
after_taxonomy_term_updated = taxonomy_signals.signal('after-taxonomy-term-updated')

before_taxonomy_term_deleted = taxonomy_signals.signal('before-taxonomy-term-deleted')
after_taxonomy_term_deleted = taxonomy_signals.signal('after-taxonomy-term-deleted')

before_taxonomy_term_moved = taxonomy_signals.signal('before-taxonomy-term-moved')
after_taxonomy_term_moved = taxonomy_signals.signal('after-taxonomy-term-moved')
