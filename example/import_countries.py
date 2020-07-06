# countries are taken from https://www.kaggle.com/nikitagrec/world-capitals-gps/data
from flask_taxonomies.api import TermIdentification
from flask_taxonomies.models import Base
from flask_taxonomies.proxies import current_flask_taxonomies
import os
import csv


def import_countries(db):
    try:
        Base.metadata.create_all(db.engine)
    except:
        pass
    tax = current_flask_taxonomies.get_taxonomy(code='country', fail=False)
    if tax:
        return

    tax = current_flask_taxonomies.create_taxonomy(
        code='country',
        extra_data={
            'title': 'List of countries'
        },
        url='https://www.kaggle.com/nikitagrec/world-capitals-gps/data')

    continents = {}
    with open(os.path.join(os.path.dirname(__file__), 'countries.csv'), 'r') as f:
        rdr = csv.DictReader(f)
        for row in rdr:
            continent = row['ContinentName']
            country = row['CountryCode']
            if continent not in continents:
                print('Creating continent', continent.lower())
                continent_term = current_flask_taxonomies.create_term(
                    TermIdentification(taxonomy=tax, slug=continent.lower().replace(' ', '-')),
                )
                continents[continent] = continent_term

            slug = '%s/%s' % (continent.lower(), country.lower())
            slug = slug.replace(' ', '-')
            print('Importing', slug)
            current_flask_taxonomies.create_term(
                TermIdentification(taxonomy=tax, slug=slug),
                extra_data=row
            )
