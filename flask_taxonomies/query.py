import sqlalchemy
from luqum.parser import parser
from luqum.tree import (
    AndOperation,
    Group,
    Not,
    OrOperation,
    Phrase,
    SearchField,
    UnknownOperation,
    Word,
)
from sqlalchemy import cast, func
from sqlalchemy.orm import Query as SQLAlchemyQuery


class TaxonomyQuery:
    def __init__(self, is_simple, query, taxonomy_code):
        self.is_simple = is_simple
        self.query = query
        self.taxonomy_code = taxonomy_code


class TaxonomyQueryNotSupported(Exception):
    def __init__(self, message):
        super().__init__(message)


def default_query_parser(q: str, taxonomy_code=None) -> TaxonomyQuery:
    """
    A parser for the query language

    :param q:   the query in stringified form
    :param taxonomy_code:    set to taxonomy code if terms are searched for.
                            Left None if taxonomies are searched for
    :return:    an instance of TaxonomyQuery
    """
    try:
        parsed_query = parser.parse(q)
    except Exception as e:
        raise TaxonomyQueryNotSupported(str(e))

    if isinstance(parsed_query, (Word, UnknownOperation)):
        return TaxonomyQuery(is_simple=True, query=q, taxonomy_code=taxonomy_code)
    if isinstance(parsed_query, Phrase):
        return TaxonomyQuery(is_simple=True, query=q.strip('"').strip("'"), taxonomy_code=taxonomy_code)
    return TaxonomyQuery(is_simple=False, query=parsed_query, taxonomy_code=taxonomy_code)


def default_query_executor(session, query: SQLAlchemyQuery,
                           model, taxonomy_query: TaxonomyQuery) -> SQLAlchemyQuery:
    """
    Modifies sqlalchemy query with the query

    :param session:  sqlalchemy session
    :param query:    the sqlalchemy query
    :param taxonomy_query: parsed query from default_query_parser
    :return:            modified sqlalchemy query
    :raises: TaxonomyQueryNotSupported if the query is too complicated to be executed
    """
    if taxonomy_query.is_simple:
        return query.filter(
            func.lower(cast(model.extra_data, sqlalchemy.String)).contains(taxonomy_query.query.lower()))

    if session.bind.dialect.name != 'postgresql':
        raise TaxonomyQueryNotSupported('Complex query not supported on database %s' % session.bind.dialect.name)

    return query.filter(convert_to_postgresql(model.extra_data, taxonomy_query.query))


def convert_to_postgresql(column, query):
    if isinstance(query, SearchField):
        name = query.name
        if isinstance(query.expr, Phrase):
            value = query.expr.value.strip('"')
        else:
            value = query.expr.value
        field = column
        for n in name.split('.'):
            field = field[n]
        field = func.jsonb_extract_path_text(column, *name.split('.'))
        return func.lower(field) == value.lower()
    if isinstance(query, OrOperation):
        return sqlalchemy.or_(convert_to_postgresql(column, query.operands[0]),
                              convert_to_postgresql(column, query.operands[1]))
    if isinstance(query, AndOperation):
        return sqlalchemy.and_(convert_to_postgresql(column, query.operands[0]),
                               convert_to_postgresql(column, query.operands[1]))
    if isinstance(query, Group):
        return convert_to_postgresql(column, query.expr)
    if isinstance(query, Not):
        return sqlalchemy.not_(convert_to_postgresql(column, query.a))

    raise TaxonomyQueryNotSupported(
        'Conversion of `%s` to database query is not yet supported. Please file an issue if needed.' % repr(query))
