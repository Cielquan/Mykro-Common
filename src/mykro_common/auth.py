"""Module containing functions for generating and verifying JWT tokens."""

from datetime import datetime, timedelta

from typing import Any, Dict, Optional, Union, List
from .api_utils import ApiException
from flask import current_app, g, jsonify

import jwt
from functools import update_wrapper
from flask import request, g
import re


def generate_token(
    user_id: int,
    payload: Optional[Dict[str, Any]] = None,
    token_type: str = "access",
    *,
    expires_in: Optional[int] = None,
) -> str:
    """Generates JWT tokens

    :param user_id: the user owning the token
    :param payload: addtional payload
    :param token_type: token type [access|refresh]; defaults to 'access'
    :param expires_in: expiration time in sec; defaults to time for :param token_type:

    :return JWT token
    """
    if payload is None:
        payload = dict()

    if expires_in is None:
        if token_type == "refresh":
            expires_in = current_app.config["REFRESH_TOKEN_EXPIRATION"]
        else:
            expires_in = current_app.config["ACCESS_TOKEN_EXPIRATION"]

    payload["sub"] = user_id
    payload["exp"] = datetime.utcnow() + timedelta(seconds=expires_in)
    payload["iat"] = datetime.utcnow()

    secret_key = current_app.config["JWT_SECRET_KEY"]

    return jwt.encode(payload, secret_key, algorithm="HS256").decode("utf-8")


def verify_token(token: str) -> bool:
    """Token verification & add payload to g"""
    # for revoking tokens
    # # this inner function checks if a token appears in the revoked token list
    # # the ttl_cache decorator from the cachetools package saves the revoked
    # # status for a token for one minute, to avoid lots of duplicated calls to
    # # the etcd service.
    # from cachetools.func import ttl_cache
    # from etcd import EtcdKeyNotFound
    #
    # @ttl_cache(ttl=60)
    # def is_token_revoked(token):
    #     try:
    #         etcd_client().read("/revoked-tokens/" + token)
    #     except EtcdKeyNotFound:
    #         return False
    #     return True
    #
    # if not current_app.config["TESTING"] and is_token_revoked(token):
    #     return False
    g.token_payload = dict()
    try:
        g.token_payload = jwt.decode(
            token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"]
        )
    except Exception as err:
        # Any error means token is invalid.
        g.token_error = err
        return False
    return True


class JWTAuth:
    """Class with decorators for JWT based authentication and authorization"""
    @staticmethod
    def _error_handler(exception=None):
        """Raise ApiException"""
        if exception is None:
            exception = ApiException(
                message="authentication required",
                status=401,
                header={"WWW-Authenticate": 'Bearer realm="Authentication Required"'},
            )
        raise exception

    @staticmethod
    def _get_token():
        """Get token from authorization header

        Header style: 'Bearer JWT'
        """
        token = re.findall(
            r"^Bearer ([a-zA-Z0-9-]+\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-]+)$",
            request.headers.get("Authorization", ""),
        )
        return None if not token else token[0]

    def _authenticate(self, optional=False):
        """Authenticate token"""
        token = self._get_token()

        if token is None:
            if optional:
                return True
            return False

        if verify_token(token):
            return True
        return False

    def login_required(self, function):
        """Flask view decorator for token authentication"""

        @wraps(function)
        def new_func(*args, **kwargs):
            """Decorator logic"""
            # Flask normally handles OPTIONS requests on its own, but in the
            # case it is configured to forward those to the application, we
            # need to ignore authentication headers and let the request through
            # to avoid unwanted interactions with CORS.
            if request.method != "OPTIONS":  # pragma: no cover
                if not self._authenticate(optional=False):
                    # Clear TCP receive buffer of any pending data
                    request.data
                    return self._error_handler()

            return function(*args, **kwargs)

        return new_func

    def login_optional(self, function):
        """Flask view decorator for optional token authentication"""

        @wraps(function)
        def new_func(*args, **kwargs):
            """Decorator logic"""
            if request.method != "OPTIONS":  # pragma: no cover
                if not self._authenticate(optional=True):
                    # Clear TCP receive buffer of any pending data
                    request.data
                    return self._error_handler()

            return function(*args, **kwargs)

        return new_func

    def _authorize(*roles: Union[str, List[str]]) -> bool:
        """Check user roles"""
        if len(roles) == 0:
            return True

        user_roles: List[str] = g.token_payload.get("roles")

        if user_roles is None:
            return False

        for role in roles:
            if isinstance(role, str):
                if not role in user_roles:
                    return False
            else:
                subrole_ok = False

                for subrole in role:
                    if subrole in user_roles:
                        subrole_ok = True
                        break

                if not subrole_ok:
                    return False

        return True

    def roles_required(self, *roles: Union[str, List[str]]):
        """Flask view decorator for validating user roles

        Based on:
        https://flask-user.readthedocs.io/en/latest/authorization.html
        Section : Simple AND/OR operations

        The @roles_required decorator accepts one or more role names.
        Each argument given to the decorator has to be either a role or a list of roles.
        The user must have the role of each given argument (AND operation).
        If the argument is a list the user must have at least of the list's roles
        (OR operation)

        In the example below, the user must always have the 'Starving' role, AND either
        the 'Artist' role OR the 'Programmer' role:

        ```
        # Ensures that the user is ('Starving' AND (an 'Artist' OR a 'Programmer'))
        @roles_required('Starving', ['Artist', 'Programmer'])
        ```

        Note: Deeper nesting is not supported.
        """

        def decorator(function):
            """Decorator function"""

            def new_func(*args, **kwargs):
                """Decorator logic"""
                if request.method != "OPTIONS":  # pragma: no cover
                    if not self._authenticate(optional=False):
                        # Clear TCP receive buffer of any pending data
                        request.data
                        return self._error_handler()

                    if not self._authorize(*roles):
                        # Clear TCP receive buffer of any pending data
                        request.data
                        return self._error_handler(
                            ApiException(message="authorization required", status=403)
                        )

                return function(*args, **kwargs)

            return update_wrapper(new_func, function)

        return decorator
