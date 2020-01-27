from marshmallow import ValidationError
from marshmallow import __version_info__ as marshmallow_version


def marshmallow_load(schema, data):
    ret = schema.load(data)
    if marshmallow_version[0] >= 3:
        return ret
    if ret[1] != {}:
        raise ValidationError(message=ret[1])
    return ret[0]
