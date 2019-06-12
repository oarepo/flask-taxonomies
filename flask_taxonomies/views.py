# -*- coding: utf-8 -*-
"""User views."""
from flask import Blueprint, render_template
from flask_login import login_required

blueprint = Blueprint("taxonomies", __name__, url_prefix="/taxonomies", static_folder="../static")


@blueprint.route("/")
def taxonomies():
    """List all taxonomy trees."""
    return {}
