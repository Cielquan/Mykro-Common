# ======================================================================================
# Copyright (c) 2020 Christian Riedel
#
# This file 'api_utils.py' created 2020-02-22
# is part of the project/program 'Mykro-Users'.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
#
# Github: https://github.com/Cielquan/
# ======================================================================================
"""
    api_utils
    ~~~~~~~~~

    API utilities

    :copyright: (c) 2020 Christian Riedel
    :license: GPLv3, see LICENSE for more details
"""
#: Concept based on https://www.youtube.com/watch?v=1ByQhAM5c1I
from functools import update_wrapper

from flask import Flask, Response, json, request
from voluptuous import Invalid  # type: ignore


def get_headers(self, basic_auth=None, token_auth=None):
    """Return the headers to include in the request."""
    headers = {"Accept": "application/json", "Content-Type": "application/json"}
    if basic_auth is not None:
        headers["Authorization"] = "Basic " + base64.b64encode(
            basic_auth.encode("utf-8")
        ).decode("utf-8")
    if token_auth is not None:
        headers["Authorization"] = "Bearer " + token_auth
    return headers


class ApiFlask(Flask):
    """Flask subclass to allow api responses"""

    def make_response(self, rv):
        if isinstance(rv, ApiResult):
            return rv.to_response()
        return Flask.make_response(self, rv)


class ApiResult:  # pylint: disable=R0903
    """API response structure"""

    def __init__(self, payload, status=200, headers=None):
        """Init API response

        :param payload: Payload of the response
        :param status: HTTP status code of the response
        """
        self.payload = payload
        self.status = status
        self.headers = headers

    def to_response(self):
        """Make API response"""
        rv = Response(
            json.dumps(self.value), status=self.status, mimetype="application/json"
        )
        if self.headers is not None:
            for header in self.headers:
                rv.headers[header] = self.headers[header]
        return rv


class ApiException(Exception):
    """API exception structure"""

    def __init__(self, message, status=400, headers=None):  # pylint: disable=W0231
        """Init API exception

        :param message: API error message
        :param status: HTTP status code
        """
        self.message = message
        self.status = status
        self.headers = headers

    def to_result(self):
        """Make API exception response"""
        return ApiResult(
            {"message": self.message}, status=self.status, headers=self.headers
        )


def dataschema(schema):
    """Decorator for validating incoming data for API calls

    :param schema: Schema to use for validation
    """

    def decorator(function):
        """Decorator function"""

        def new_func(*args, **kwargs):
            """Decorator logic"""
            try:
                kwargs.update(schema(request.get_json()))
            except Invalid as err:
                raise ApiException(
                    f"Invalid data {err.msg} (path '{'.'.join(err.path)}')"
                )
            return function(*args, **kwargs)

        return update_wrapper(new_func, function)

    return decorator


# from werkzeug.urls import url_join
# class ApiResult:  # pylint: disable=R0903
#     """API response structure"""
#
#     def __init__(self, value, status=200, *, next_page=None):
#         """Init API response
#
#         :param value: Payload of the response
#         :param status: HTTP status code of the response
#         :param next_page: Link to next page (pagination)
#         """
#         self.value = value
#         self.status = status
#         self.next_page = next_page
#
#     def to_response(self):
#         """Make API response"""
#         rv = Response(
#             json.dumps(self.value), status=self.status, mimetype="application/json"
#         )
#         if self.next_page is not None:
#             rv.headers[
#                 "Link"
#             ] = f"<{url_join(request.url, self.next_page)}>; rel='next'"
#         return rv
