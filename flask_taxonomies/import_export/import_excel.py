from invenio_db import db
from slugify import slugify

from flask_taxonomies.models import Taxonomy


def import_taxonomy(taxonomy_file, int_conversions):
    from openpyxl import load_workbook
    wb = load_workbook(filename=taxonomy_file)
    ws = wb.active

    data = list(ws.rows)

    taxonomy_header, row = read_block(data, 0)
    taxonomy_data, row = read_block(data, row)

    taxonomy = create_update_taxonomy(taxonomy_header)

    create_update_terms(taxonomy, taxonomy_data, int_conversions)


def create_update_terms(taxonomy, taxonomy_data, int_conversions):
    stack = [taxonomy]
    for term_dict in convert_data_to_dict(taxonomy_data, int_conversions):
        level = int(term_dict.pop('level'))
        slug = term_dict.pop('slug')
        while level < len(stack):
            stack.pop()
        if not slug:
            slug = slugify(next(filter(lambda x: x['lang'] == 'cs', term_dict['title']))['value'])

        term = taxonomy.get_term(slug)
        if term:
            term.update(term_dict)
        else:
            term = stack[-1].create_term(slug=slug, extra_data=term_dict)

        stack.append(term)
    db.session.commit()


def create_update_taxonomy(data):
    tax_dict = next(convert_data_to_dict(data))
    if 'code' not in tax_dict:
        raise ValueError('Taxonomy does not contain "code"')
    code = tax_dict.pop('code')
    taxonomy = Taxonomy.get(code=code)
    if taxonomy:
        merged_dict = taxonomy.extra_data
        merged_dict.update(tax_dict)
        taxonomy.update(extra_data=merged_dict)
    else:
        taxonomy = Taxonomy.create_taxonomy(code, tax_dict)
    db.session.commit()
    return taxonomy


def convert_data_to_dict(data, int_conversions={}):
    header = [x.split() if x else None for x in data[0]]
    for block in read_data_blocks(data[1:]):
        ret = {}
        for block_row in block:
            converted_row = {}
            for arridx, prop_path, val in zip(range(0, len(header)), header, block_row):
                if not prop_path:
                    continue

                if ' '.join(prop_path) in int_conversions:
                    val = int(val) if val else None

                for part in reversed(prop_path):
                    if part[0] == '@':
                        val = {part[1:]: [val]}
                    else:
                        val = {part: val}

                # merge converted_row with val, merge items in arrays
                piecewise_merge(converted_row, val,
                                list_update=lambda target, source: target[0].update(source[0]))

            # merge converted_row into ret, but handle arrays this time
            piecewise_merge(ret, converted_row,
                            list_update=lambda target, source: target.extend(source))
        yield ret


def piecewise_merge(target, source, list_update):
    if isinstance(target, list):
        list_update(target, source)
        return target
    elif isinstance(target, dict):
        for k, v in source.items():
            target[k] = piecewise_merge(target.get(k), v, list_update)
    else:
        if target and source:
            raise Exception(f'Trying to override {target} with {source}')
        if target:
            return target
        return source


def read_data_blocks(data):
    ret = []
    for row in data:
        if row[0]:
            if ret:
                yield ret
                ret = []
        ret.append(row)
    if ret:
        yield ret


def read_block(data, startrow):
    ret = []

    def convert(x):
        if x.value is None:
            return ''
        return str(x.value).strip()

    empty = False
    rowidx = startrow
    starting = True
    for row in data[startrow:]:
        rowidx += 1
        row = [convert(x) for x in row]
        for c in row:
            if c:
                break
        else:
            if starting:
                continue
            # all values empty
            if empty:
                break
            empty = True
            continue
        ret.append(row)
        empty = False
        starting = False

    return ret, rowidx
