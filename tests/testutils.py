# -*- coding: utf-8 -*-
"""Defines fixtures available to all tests."""


def login_user(client, user):
    """Log in a specified user."""
    with client.session_transaction() as sess:
        sess['user_id'] = user.id if user else None
        sess['_fresh'] = True
