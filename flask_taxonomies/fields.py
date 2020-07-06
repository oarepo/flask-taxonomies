import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import ColumnElement
from sqlalchemy.sql.elements import Grouping
from sqlalchemy.sql.operators import custom_op
from sqlalchemy_utils import LtreeType


class Ancestor(ColumnElement):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs


class Descendant(ColumnElement):
    def __init__(self, lhs, rhs):
        self.lhs = lhs
        self.rhs = rhs


@compiles(Descendant)
def compile_descendant(element, compiler, **kw):
    expr = Grouping(element.lhs.op('like')(element.rhs + ESCAPE_CHAR + '%').op('or')(element.lhs.op('=')(element.rhs)))
    return compiler.visit_grouping(expr)


@compiles(Descendant, 'postgresql')
def compile_descendant(element, compiler, **kw):
    lhs = element.lhs
    rhs = element.rhs
    if isinstance(rhs, str):
        rhs = rhs.replace('/', '.').replace('-', '_')
    expr = Grouping(lhs.op('<@')(rhs))
    return compiler.visit_grouping(expr)


@compiles(Ancestor)
def compile_ancestor(element, compiler, **kw):
    expr = Grouping(element.lhs.op('||')(ESCAPE_CHAR + '%').reverse_op('like')(element.rhs).op('or')(
        element.lhs.op('=')(element.rhs)
    ))
    return compiler.visit_grouping(expr)


@compiles(Ancestor, 'postgresql')
def compile_ancestor(element, compiler, **kw):
    lhs = element.lhs
    rhs = element.rhs
    if isinstance(rhs, str):
        rhs = rhs.replace('/', '.').replace('-', '_')
    expr = Grouping(lhs.op('@>')(rhs))
    return compiler.visit_grouping(expr)


# postgresql ltree does not allow for hyphens in path, so need to change them to _
class PostgresSlugType(LtreeType):
    class comparator_factory(types.Concatenable.Comparator):
        def ancestor_of(self, other):
            return Ancestor(self, other)

        def descendant_of(self, other):
            return Descendant(self, other)

    def bind_processor(self, dialect):
        def process(value):
            if value and isinstance(value, str):
                return value.replace('/', '.').replace('-', '_')

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return self._coerce(value)

        return process

    def literal_processor(self, dialect):
        def process(value):
            value = value.replace('/', '.').replace("'", "''").replace('-', '_')
            return "'%s'" % value

        return process

    __visit_name__ = 'LTREE'

    def _coerce(self, value):
        if value:
            return value.replace('.', '/').replace('_', '-')


ESCAPE_CHAR = '\x01'  # as low as possible, \x00 is handled incorrectly in sqlite3


class SlugType(types.TypeDecorator):
    impl = sa.UnicodeText()

    class Comparator(sa.UnicodeText.Comparator):
        def ancestor_of(self, other):
            return Ancestor(self, other)

        def descendant_of(self, other):
            return Descendant(self, other)

        def reverse_op(self, opstring, precedence=0, is_comparison=False, return_type=None):
            operator = custom_op(opstring, precedence, is_comparison, return_type)

            def against(other):
                return operator(self, other, reverse=True)

            return against

    comparator_factory = Comparator

    def process_bind_param(self, value, dialect):
        if value is not None:
            return value.replace('/', ESCAPE_CHAR)

    def process_result_value(self, value, dialect):
        if value is not None:
            return value.replace(ESCAPE_CHAR, '/')


@compiles(sa.UnicodeText, 'postgresql')
@compiles(sa.UnicodeText, 'postgresql')
def compile_slug(element, compiler, **kw):
    if 'type_expression' in kw:
        column = kw['type_expression']
        try:
            if isinstance(column.type.impl, SlugType):
                return 'LTREE'
        except:
            pass
    return compiler.visit_unicode(element, **kw)
