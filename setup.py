# -*- coding: utf-8 -*-
"""Setup module for flask taxonomy."""

from setuptools import setup

DATABASE = "postgresql"
INVENIO_VERSION = "3.1.0"

install_requires = [
    'webargs>=5.3.2',
    'sqlalchemy_mptt>=0.2.4',
    'invenio[{db},base]~={version}'.format(
        db=DATABASE, version=INVENIO_VERSION)
]

tests_require = [
    'pytest>=4.6.3',
    'factory-boy>=2.12.0',
    'pdbpp>=0.10.0',
    'pydocstyle<4.0.0',
    'check-manifest>=0.25',
    'coverage>=4.0',
    'isort>=4.3.3',
    'mock>=2.0.0',
    'pytest-cache>=1.0',
    'pytest-invenio>=1.0.2,<1.1.0',
    'pytest-mock>=1.6.0',
    'pytest-cov>=1.8.0',
    'pytest-random-order>=0.5.4',
    'pytest-pep8>=1.0.6',
]

setup(
    name="flask_taxonomies",
    version="3.0.0",
    url="https://github.com/oarepo/flask-taxonomies",
    license="MIT",
    author="Miroslav Bauer",
    author_email="bauer@cesnet.cz",
    description="Taxonomy Term trees REST API for Invenio Applications",
    zip_safe=False,
    packages=['flask_taxonomies'],
    entry_points={
        'invenio_db.models': [
            'flask_taxonomies = flask_taxonomies.models',
        ],
        'invenio_db.alembic': [
            'flask_taxonomies = flask_taxonomies:alembic',
        ],
        'invenio_base.api_blueprints': [
            'flask_taxonomies = flask_taxonomies.views:blueprint',
        ],
        'invenio_base.apps': [
            'flask_taxonomies = flask_taxonomies.ext:FlaskTaxonomies',
        ],
        'invenio_base.api_apps': [
            'flask_taxonomies = flask_taxonomies.ext:FlaskTaxonomies',
        ],
    },
    include_package_data=True,
    install_requires=install_requires,
    tests_require=tests_require,
    platforms='any',
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Development Status :: 4 - Beta',
    ],
)
