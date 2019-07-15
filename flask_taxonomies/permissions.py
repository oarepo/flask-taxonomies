# -*- coding: utf-8 -*-
"""Taxonomy permissions."""
#
# Action needs
#
from invenio_access import Permission, action_factory

from flask_taxonomies.models import Taxonomy, TaxonomyTerm

TaxonomyCreate = action_factory('taxonomy-create', True)
"""Action needed: Taxonomy create."""

TaxonomyUpdate = action_factory('taxonomy-update', True)
"""Action needed: Taxonomy update."""

TaxonomyRead = action_factory('taxonomy-read', True)
"""Action needed: Taxonomy Read."""

TaxonomyDelete = action_factory('taxonomy-delete', True)
"""Action needed: Taxonomy delete."""

TaxonomyTermCreate = action_factory('taxonomy-term-create', True)
"""Action needed: Taxonomy Term Create."""

TaxonomyTermUpdate = action_factory('taxonomy-term-update', True)
"""Action needed: Taxonomy Term update."""

TaxonomyTermRead = action_factory('taxonomy-term-read', True)
"""Action needed: Taxonomy Term Read."""

TaxonomyTermDelete = action_factory('taxonomy-term-delete', True)
"""Action needed: Taxonomy Term delete."""

TaxonomyTermMove = action_factory('taxonomy-term-move', True)
"""Action needed: Taxonomy Term Move."""


#
# Global action needs
#
taxonomy_create_all = TaxonomyCreate(None)
permission_taxonomy_create_all = Permission(taxonomy_create_all)
"""Action needed: create all taxonomies."""

taxonomy_update_all = TaxonomyUpdate(None)
permission_taxonomy_update_all = Permission(taxonomy_update_all)
"""Action needed: update all taxonomies."""

taxonomy_read_all = TaxonomyRead(None)
permission_taxonomy_read_all = Permission(taxonomy_read_all)
"""Action needed: read all taxonomies."""

taxonomy_delete_all = TaxonomyDelete(None)
permission_taxonomy_delete_all = Permission(taxonomy_delete_all)
"""Action needed: delete all taxonomies."""

taxonomy_term_create_all = TaxonomyTermCreate(None)
permission_term_create_all = Permission(taxonomy_term_create_all)
"""Action needed: create all terms."""

taxonomy_term_update_all = TaxonomyTermUpdate(None)
permission_term_update_all = Permission(taxonomy_term_update_all)
"""Action needed: update all terms."""

taxonomy_term_read_all = TaxonomyTermRead(None)
permission_term_read_all = Permission(taxonomy_term_read_all)
"""Action needed: read all terms."""

taxonomy_term_delete_all = TaxonomyTermDelete(None)
permission_term_delete_all = Permission(taxonomy_term_delete_all)
"""Action needed: delete all terms."""

taxonomy_term_move_all = TaxonomyTermMove(None)
permission_term_move_all = Permission(taxonomy_term_move_all)
"""Action needed: update all buckets"""


_action2need_map = {
    'taxonomy-create': TaxonomyCreate,
    'taxonomy-read': TaxonomyRead,
    'taxonomy-update': TaxonomyUpdate,
    'taxonomy-delete': TaxonomyDelete,
    'taxonomy-term-create': TaxonomyTermCreate,
    'taxonomy-term-read': TaxonomyTermRead,
    'taxonomy-term-update': TaxonomyTermUpdate,
    'taxonomy-term-delete': TaxonomyTermDelete,
    'taxonomy-term-move': TaxonomyTermMove,
}
"""Mapping of action names to action needs."""


def permission_factory(obj, action):
    """
    Get default permission factory.

    :param obj: An instance of :class:`invenio_files_rest.models.Bucket` or
        :class:`invenio_files_rest.models.ObjectVersion` or
        :class:`invenio_files_rest.models.MultipartObject` or ``None`` if
        the action is global.
    :param action: The required action.
    :raises RuntimeError: If the object is unknown.
    :returns: A :class:`invenio_access.permissions.DynamicPermission` instance.
    """
    need_class = _action2need_map[action]

    if obj is None:
        return Permission(need_class(None))  # pragma: nocover

    arg = None
    if isinstance(obj, Taxonomy):
        arg = str(obj.code)
    elif isinstance(obj, TaxonomyTerm):
        arg = str(obj.tree_path)
    else:
        raise RuntimeError('Unknown object')  # pragma: nocover

    return Permission(need_class(arg))
