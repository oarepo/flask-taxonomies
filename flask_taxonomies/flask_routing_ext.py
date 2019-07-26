import functools

from flask import request
from werkzeug.exceptions import NotAcceptable
from functools import partial


# extended from https://github.com/di/flask-accept
#
# The MIT License (MIT)
#
# Copyright (c) 2015 Dustin Ingram
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


class HeaderRouter(object):
    handled_values = []
    header_accessor = None
    use_fallback = False

    def __init__(self, func):
        """Initialize a new HeaderRouter and create the accept handlers

        :param func: the endpoint function to fall back upon
        """
        self.fallback = func
        self.handlers = {
            value: func for value in self.handled_values
        }
        functools.update_wrapper(self, func)

    def __call__(self, *args, **kwargs):
        """Select a handler function to respond to the preferred mediatypes."""

        for value in self._request_values():
            if value in self.handlers:
                return self.handlers[value](*args, **kwargs)

        if self.use_fallback:
            return self.fallback(*args, **kwargs)

        supported_values = ', '.join(self.handlers)
        description = '{} Supported entities are: {}'.format(
            NotAcceptable.description, supported_values)
        raise NotAcceptable(description)

    def _request_values(self):
        if callable(self.header_accessor):
            return self.header_accessor(request)
        data = getattr(request, self.header_accessor, [])
        if not isinstance(data, list) and not isinstance(data, tuple):
            data = (data,)
        return data

    def __get__(self, instance, owner):
        func = partial(self.__call__, instance)

        # flask-restplus use doc and apidoc for swagger document
        func.__doc__ = self.fallback.__doc__
        if '__apidoc__' in self.fallback.__dict__:
            func.__apidoc__ = self.fallback.__apidoc__

        return func

    def support(self, *values):
        """Register an additional mediatype handler on an existing HeaderRouter."""

        def decorator(func):
            for value in values:
                self.handlers[value] = func
            return func

        return decorator


def accept(_header_accessor, *args):
    """Decorator to explictly allows multiple mediatypes

    :param args: the accepted mediatypes, as strings
    :returns: an HeaderRouter class to be initialized
    """

    class ExplicitHeaderRouter(HeaderRouter):
        handled_values = args
        header_accessor = _header_accessor

    return ExplicitHeaderRouter


def accept_fallback(_header_accessor):
    """Decorator to specify a fallback endpoint function.

    :param func: the endpoint function to fall back upon
    :returns: an HeaderRouter class to be initialized
    """

    class FallbackHeaderRouter(HeaderRouter):
        use_fallback = True
        header_accessor = _header_accessor

    return FallbackHeaderRouter
