import pytest

from flask_taxonomies.models import TaxonomyError, TermStatusEnum
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
