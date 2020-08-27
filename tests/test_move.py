import pytest
import sqlalchemy

from flask_taxonomies.models import TaxonomyError, TaxonomyTerm, TermStatusEnum
from flask_taxonomies.signals import after_taxonomy_term_moved
from flask_taxonomies.term_identification import TermIdentification
from flask_taxonomies.utils import to_json


def move_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/b')
    t3 = api.create_term('test/a/c')
    api.move_term(t1, new_parent=t2)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/a',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.alive.value,
                            'slug': 'b/a/c',
                            'children': [],
                        }
                    ],
                }
            ],
        }
    ]


def move_no_delete_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/b')
    t3 = api.create_term('test/a/c')
    api.move_term(t1, new_parent=t2, remove_after_delete=False)

    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.deleted.value,
            'slug': 'a',
            'obsoleted_by': 'b/a',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.deleted.value,
                    'slug': 'a/c',
                    'obsoleted_by': 'b/a/c',
                    'children': [],
                }
            ],
        },
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/a',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.alive.value,
                            'slug': 'b/a/c',
                            'children': [],
                        }
                    ],
                }
            ],
        }
    ]


def move_to_root_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    t3 = api.create_term('test/a/b/c')
    api.move_term(t2, new_parent=None)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [],
        },
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/c',
                    'children': [],
                }
            ],
        }
    ]


def move_to_root_nondelete_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    t3 = api.create_term('test/a/b/c')
    api.move_term(t2, new_parent=None, remove_after_delete=False)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.deleted.value,
                    'slug': 'a/b',
                    'obsoleted_by': 'b',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.deleted.value,
                            'obsoleted_by': 'b/c',
                            'slug': 'a/b/c',
                            'children': [],
                        }
                    ],
                }
            ],
        },
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'b/c',
                    'children': [],
                }
            ],
        }
    ]


def move_to_itself_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    with pytest.raises(TaxonomyError):
        api.move_term(t1, t1)


def move_to_descendant_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    with pytest.raises(TaxonomyError):
        api.move_term(t1, t2)


def move_with_signal_test(api, db, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/b')
    t3 = api.create_term('test/a/c')

    def long_running_move_action(sender, term=None, new_term=None, **kwargs):
        # lock both the old and new terms so that they can not be manipulated.
        # start a background process to replace the term in referencing documents.
        api.mark_busy([
            x[0] for x in api.descendants_or_self(term, status_cond=sqlalchemy.sql.true()).values(TaxonomyTerm.id)
        ])
        api.mark_busy([
            x[0] for x in api.descendants_or_self(new_term, status_cond=sqlalchemy.sql.true()).values(TaxonomyTerm.id)
        ])

    try:
        after_taxonomy_term_moved.connect(long_running_move_action)
        api.move_term(t1, new_parent=t2, remove_after_delete=False)

        db.session.refresh(t1)
        db.session.refresh(t2)

        assert t1.busy_count == 1
        assert t1.status == TermStatusEnum.deleted
        assert t3.busy_count == 1
        assert t3.status == TermStatusEnum.deleted

        new_t1 = api.filter_term(TermIdentification(taxonomy=test_taxonomy, slug='b/a')).one()
        assert new_t1.busy_count == 1
        assert new_t1.status == TermStatusEnum.alive

        new_t3 = api.filter_term(TermIdentification(taxonomy=test_taxonomy, slug='b/a/c')).one()
        assert new_t3.busy_count == 1
        assert new_t3.status == TermStatusEnum.alive

    finally:
        after_taxonomy_term_moved.disconnect(long_running_move_action)


def move_to_locked_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    p1 = api.create_term('test/p')
    p2 = api.create_term('test/p/a')
    api.mark_busy([p2.id])
    with pytest.raises(TaxonomyError):
        api.move_term(t1, p2)


def move_to_locked_ancestor_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    p1 = api.create_term('test/p')
    api.mark_busy([p1.id])
    p2 = api.create_term('test/p/a')
    with pytest.raises(TaxonomyError):
        api.move_term(t1, p2)


def move_locked_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    p1 = api.create_term('test/p')
    api.mark_busy([t1.id])
    p2 = api.create_term('test/p/a')
    with pytest.raises(TaxonomyError):
        api.move_term(t1, p2)


def move_locked_descendant_test(api, test_taxonomy):
    t1 = api.create_term('test/a')
    t2 = api.create_term('test/a/b')
    p1 = api.create_term('test/p')
    api.mark_busy([t2.id])
    p2 = api.create_term('test/p/a')
    with pytest.raises(TaxonomyError):
        api.move_term(t1, p2)
