import sqlalchemy as sa
from sqlalchemy import types
from sqlalchemy.sql.operators import custom_op
from sqlalchemy_utils import LtreeType, Ltree


class PostgresSlugType(LtreeType):
    class comparator_factory(types.Concatenable.Comparator):
        def ancestor_of(self, other):
            return self.op('@>')(Ltree(other.replace('/', '.')))

        def descendant_of(self, other):
            return self.op('<@')(Ltree(other.replace('/', '.')))

    def bind_processor(self, dialect):
        def process(value):
            if value:
                return value.replace('/', '.')

        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return self._coerce(value)

        return process

    def literal_processor(self, dialect):
        def process(value):
            value = value.replace('/', '.').replace("'", "''")
            return "'%s'" % value

        return process

    __visit_name__ = 'PostgresSlug'

    def _coerce(self, value):
        if value:
            return value.replace('.', '/')


ESCAPE_CHAR = '\x00'


class SlugType(types.TypeDecorator):
    impl = sa.UnicodeText()

    class Comparator(sa.UnicodeText.Comparator):
        def ancestor_of(self, other):
            return self.op('||')(ESCAPE_CHAR + '%').reverse_op('like')(other).op('or')(
                self.op('=')(other)
            )

        def descendant_of(self, other):
            return self.op('like')(other + ESCAPE_CHAR + '%').op('or')(self.op('=')(other))

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
