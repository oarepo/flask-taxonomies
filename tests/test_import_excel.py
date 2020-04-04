from pprint import pprint

import pytest

from flask_taxonomies.import_export.import_excel import convert_data_to_dict


@pytest.fixture
def data():
    return [
        ['level', 'slug', '@title lang', '@title value', '@title lang', '@title value', 'marcCode',
         'dataCiteCode', ''],
        ['1', 'contact-person', 'cze', 'kontaktní osoba', 'eng', 'contact person', '',
         'ContactPerson', ''],
        ['1', 'data-curator', 'cze', 'kurátor dat', 'eng', 'data curator', '', 'DataCurator', ''],
        ['1', 'data-manager', 'cze', 'manažer dat', 'eng', 'data manager', 'dtm', 'DataManager',
         ''],
        ['1', 'distributor', 'cze', 'distributor', 'eng', 'distributor', 'dst', 'Distributor', ''],
        ['1', 'editor', 'cze', 'editor', 'eng', 'editor', 'edt', 'Editor', ''],
        ['1', 'producer', 'cze', 'producent', 'eng', 'producer', 'pro', 'Producer', ''],
        ['1', 'project-leader', 'cze', 'vedoucí projektu', 'eng', 'project leader', 'rth',
         'ProjectLeader', ''],
        ['1', 'project-manager', 'cze', 'projektový manažer', 'eng', 'project manager', '',
         'ProjectManager', ''],
        ['1', 'project-member', 'cze', 'člen projektu', 'eng', 'project member', 'rtm',
         'ProjectMember', ''],
        ['1', 'researcher', 'cze', 'výzkumník', 'eng', 'researcher', 'res', 'Researcher', ''],
        ['1', 'research-group', 'cze', 'výzkumná skupina', 'eng', 'research group', '',
         'ResearchGroup', ''],
        ['1', 'rights-holder', 'cze', 'majitel práv', 'eng', 'rights holder', 'asg', 'RightsHolder',
         ''], ['1', 'supervisor', 'cze', 'supervizor', 'eng', 'supervisor', '', 'Supervisor', ''],
        ['1', 'referee', 'cze', 'oponent', 'eng', 'referee', 'opn', '', ''],
        ['1', 'advisor', 'cze', 'vedoucí', 'eng', 'advisor', 'ths', '', ''],
        ['1', 'illustrator', 'cze', 'ilustrátor', 'eng', 'illustrator', 'ill', '', ''],
        ['1', 'exhibition-curator', 'cze', 'kurátor výstavy', 'eng', 'exhibition curator', '', '',
         ''], ['1', 'moderator', 'cze', 'moderátor', 'eng', 'moderator', 'mod', '', ''],
        ['1', 'translator', 'cze', 'překladatel', 'eng', 'translator', 'trl', '', ''],
        ['1', 'photographer', 'cze', 'fotograf', 'eng', 'photographer', 'pht', '', ''],
        ['1', 'reviewer', 'cze', 'recenzent', 'eng', 'reviewer', 'rev', '', ''],
        ['1', 'collaborator', 'cze', 'spolupracovník', 'eng', 'collaborator', 'clb', '', ''],
        ['1', 'artist', 'cze', 'umělec', 'eng', 'artist', 'art', '', ''],
        ['1', 'interviewee', 'cze', 'dotazovaný', 'eng', 'interviewee', 'ive', '', ''],
        ['1', 'interviewer', 'cze', 'dotazovatel', 'eng', 'interviewer', 'ivr', '', ''],
        ['1', 'organizer', 'cze', 'organizátor', 'eng', 'organizer', 'orm', '', ''],
        ['1', 'speaker', 'cze', 'spíkr', 'eng', 'speaker', 'spk', '', ''],
        ['1', 'panelist', 'cze', 'panelista', 'eng', 'panelist', 'pan', '', '']]


@pytest.fixture()
def taxonomy_data():
    return [['code', '@title lang', '@title value', '', '', '', '', '', ''],
            ['contributor-type', 'cs', 'Role přispěvatele', '', '', '', '', '', ''],
            ['', 'en', 'Contributor Type', '', '', '', '', '', '']]


def test_convert_data_to_dict(data):
    res = list(convert_data_to_dict(data))
    assert res[0] == {
        'dataCiteCode': 'ContactPerson',
        'level': '1',
        'slug': 'contact-person',
        'title': [{'lang': 'cze', 'value': 'kontaktní osoba'},
                  {'lang': 'eng', 'value': 'contact person'}]
    }


def test_convert_data_taxonomy(taxonomy_data):
    res = list(convert_data_to_dict(taxonomy_data))
    assert res == [{
        'code': 'contributor-type',
        'title': [{'lang': 'cs', 'value': 'Role přispěvatele'},
                  {'lang': 'en', 'value': 'Contributor Type'}]
    }]
