import re

from marshmallow import EXCLUDE, Schema, utils
from marshmallow.fields import Field, Integer, String
from werkzeug.http import parse_options_header

from flask_taxonomies.models import DEFAULT_REPRESENTATION, Representation

RETURN_PREFIX = 'return='


class PreferHeaderField(Field):
    default_error_messages = {
        "invalid": "Not a valid string.",
        "invalid_utf8": "Not a valid utf-8 string.",
    }

    def _serialize(self, value, attr, obj, **kwargs):
        raise NotImplementedError()

    def _deserialize(self, value, attr, data, **kwargs) -> [Representation, None]:
        if not isinstance(value, (str, bytes)):
            raise self.make_error("invalid")
        try:
            value = utils.ensure_text_type(value)
        except UnicodeDecodeError as error:
            raise self.make_error("invalid_utf8") from error
        value = parse_options_header(value)
        command, _options = value
        if not command.startswith(RETURN_PREFIX):
            return None
        representation = command[len(RETURN_PREFIX):]
        options = {}
        for k, v in _options.items():
            if k in ('include', 'exclude', 'select'):
                options[k] = set((v or '').strip().split())
            else:
                options[k] = (v or '').strip()

        return Representation(
            representation,
            include=options.pop('include', None),
            exclude=options.pop('exclude', None),
            select=options.pop('select', None),
            options=options
        )


class PreferQueryField(Field):
    default_error_messages = {
        "invalid": "Not a valid string.",
        "invalid_utf8": "Not a valid utf-8 string.",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def _serialize(self, value, attr, obj, **kwargs):
        raise NotImplementedError()

    def _deserialize(self, value, attr, data, **kwargs) -> [Representation, None]:
        if not isinstance(value, (str, bytes)):
            raise self.make_error("invalid")
        try:
            value = utils.ensure_text_type(value)
        except UnicodeDecodeError as error:
            raise self.make_error("invalid_utf8") from error
        value = [x.strip() for x in re.split(r'[ ,]', value)]
        return value


class HeaderSchema(Schema):
    prefer = PreferHeaderField(missing=DEFAULT_REPRESENTATION)

    class Meta:
        unknown = EXCLUDE


class MoveHeaderSchema(HeaderSchema):
    destination = String()
    rename = String()

    class Meta:
        unknown = EXCLUDE


class QuerySchema(Schema):
    include = PreferQueryField(missing=None, data_key='representation:include')
    exclude = PreferQueryField(missing=None, data_key='representation:exclude')
    select = PreferQueryField(missing=None, data_key='representation:select')
    levels = Integer(missing=None, data_key='representation:levels')
    q = String(missing=None, data_key='q')

    class Meta:
        unknown = EXCLUDE


class PaginatedQuerySchema(QuerySchema):
    size = Integer(missing=None)
    page = Integer(missing=1)

    class Meta:
        unknown = EXCLUDE
