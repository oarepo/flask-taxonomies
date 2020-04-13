import json

from flask_taxonomies.api import TermIdentification
from flask_taxonomies.models import TermStatusEnum
from flask_taxonomies.utils import to_json


def root_rename_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a'), new_slug='b')
    assert to_json(api, test_taxonomy) == [
        {
            'children': [],
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b'
        }
    ]


def root_rename_no_delete_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a'), new_slug='b', remove_after_delete=False)
    assert to_json(api, test_taxonomy) == [
        {
            'children': [],
            'level': 0,
            'slug': 'a',
            'status': TermStatusEnum.deleted.value,
            'obsoleted_by': 'b'
        },
        {
            'children': [],
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'b'
        }
    ]


def root_rename_hierarchy_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    r1 = api.create_term(TermIdentification(parent=root, slug='a'))
    r2 = api.create_term(TermIdentification(parent=r1, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a'), new_slug='b')
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
                            'slug': 'b/a/a',
                            'children': [],
                        }
                    ],
                }
            ],
        }
    ]


def root_rename_hierarchy_no_delete_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    r1 = api.create_term(TermIdentification(parent=root, slug='a'))
    r2 = api.create_term(TermIdentification(parent=r1, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a'), new_slug='b', remove_after_delete=False)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.deleted.value,
            'slug': 'a',
            'obsoleted_by': 'b',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.deleted.value,
                    'slug': 'a/a',
                    'obsoleted_by': 'b/a',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.deleted.value,
                            'slug': 'a/a/a',
                            'obsoleted_by': 'b/a/a',
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
                    'slug': 'b/a',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.alive.value,
                            'slug': 'b/a/a',
                            'children': [],
                        }
                    ],
                }
            ],
        },
    ]


def nested_rename_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    nested = api.create_term(TermIdentification(parent=root, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a/a'), new_slug='b')
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'a/b',
                    'children': [],
                }
            ],
        }
    ]


def nested_rename_no_delete_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    nested = api.create_term(TermIdentification(parent=root, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a/a'), new_slug='b', remove_after_delete=False)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [
                {
                    'children': [],
                    'level': 1,
                    'slug': 'a/a',
                    'status': TermStatusEnum.deleted.value,
                    'obsoleted_by': 'a/b'
                },
                {
                    'children': [],
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'a/b'
                }
            ]
        }
    ]


def nested_rename_hierarchy_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    nested = api.create_term(TermIdentification(parent=root, slug='a'))
    r1 = api.create_term(TermIdentification(parent=nested, slug='a'))
    r2 = api.create_term(TermIdentification(parent=r1, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a/a'), new_slug='b')
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'a/b',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.alive.value,
                            'slug': 'a/b/a',
                            'children': [
                                {
                                    'level': 3,
                                    'status': TermStatusEnum.alive.value,
                                    'slug': 'a/b/a/a',
                                    'children': [],
                                }
                            ],
                        }
                    ],
                }
            ]
        }
    ]


def nested_rename_hierarchy_no_delete_test(api, test_taxonomy):
    root = api.create_term(TermIdentification(taxonomy=test_taxonomy, slug='a'))
    nested = api.create_term(TermIdentification(parent=root, slug='a'))
    r1 = api.create_term(TermIdentification(parent=nested, slug='a'))
    r2 = api.create_term(TermIdentification(parent=r1, slug='a'))
    api.rename_term(TermIdentification(taxonomy=test_taxonomy, slug='a/a'), new_slug='b', remove_after_delete=False)
    assert to_json(api, test_taxonomy) == [
        {
            'level': 0,
            'status': TermStatusEnum.alive.value,
            'slug': 'a',
            'children': [
                {
                    'level': 1,
                    'status': TermStatusEnum.deleted.value,
                    'slug': 'a/a',
                    'obsoleted_by': 'a/b',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.deleted.value,
                            'slug': 'a/a/a',
                            'obsoleted_by': 'a/b/a',
                            'children': [
                                {
                                    'level': 3,
                                    'status': TermStatusEnum.deleted.value,
                                    'slug': 'a/a/a/a',
                                    'obsoleted_by': 'a/b/a/a',
                                    'children': [],
                                }
                            ],
                        }
                    ],
                },
                {
                    'level': 1,
                    'status': TermStatusEnum.alive.value,
                    'slug': 'a/b',
                    'children': [
                        {
                            'level': 2,
                            'status': TermStatusEnum.alive.value,
                            'slug': 'a/b/a',
                            'children': [
                                {
                                    'level': 3,
                                    'status': TermStatusEnum.alive.value,
                                    'slug': 'a/b/a/a',
                                    'children': [],
                                }
                            ],
                        }
                    ],
                },
            ]
        }
    ]
