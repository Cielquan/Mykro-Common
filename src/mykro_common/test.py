"""Common tools for unit testing

Based on mircoflack_common/test.py by Miguel Grinberg.
Source: https://github.com/miguelgrinberg/microflack_common/blob/v0.4/microflack_common/test.py
License: https://github.com/miguelgrinberg/microflack_common/blob/v0.4/LICENSE
"""
import base64
import json
import pytest
from .auth import generate_token


class Client:
    """A wrapper class for the flask test client's HTTP request calls for testing."""

    def __init__(self, app):
        """Init test client"""
        self.client = app.test_client()

    def get_headers(self, token_auth=None):
        """Return the headers to include in the request."""
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if token_auth is not None:
            headers["Authorization"] = "Bearer " + token_auth
        return headers

    @staticmethod
    def _rv_parser(rv):
        """Parse request reponses"""
        body = rv.get_data(as_text=True)  # TODO: rv.data.decode() ?
        if body is not None and body != "":
            try:
                body = json.loads(body)
            except:
                pass
        return body, rv.status_code, rv.headers

    def get(self, url, token_auth=None):
        """Send a GET request through the Flask test client."""
        rv = self.client.get(url, headers=self.get_headers(token_auth))
        return self._rv_parser(rv)

    def post(self, url, data=None, token_auth=None):
        """Send a POST request through the Flask test client."""
        _data = data if data is None else json.dumps(data)
        rv = self.client.post(url, data=_data, headers=self.get_headers(token_auth))
        return self._rv_parser(rv)

    def put(self, url, data=None, token_auth=None):
        """Send a PUT request through the Flask test client."""
        _data = data if data is None else json.dumps(data)
        rv = self.client.put(url, data=_data, headers=self.get_headers(token_auth))
        return self._rv_parser(rv)

    def delete(self, url, token_auth=None):
        """Send a DELETE request through the Flask test client."""
        rv = self.client.delete(url, headers=self.get_headers(token_auth))
        return self._rv_parser(rv)


@pytest.fixture(scope="session")
def client(app):
    """Pytest fixture returning a custom flask test client"""
    return Client(app)


@pytest.fixture(scope="class")
def client_class(request, client):
    """Pytest fixture adding the client fixture to classes' attributes"""
    if request.cls is not None:
        request.cls.client = client


@pytest.fixture
def token_admin(request):
    """Pytest fixture returning JWT and adding it to classes' attributes

    generating JWT for user ID 1 with 'admin' role
    """
    token = generate_token(1, {"roles": ["admin"]})
    if request.cls is not None:
        request.cls.token_admin = token
    return token


@pytest.fixture
def token_roleless(request):
    """Pytest fixture returning JWT and adding it to classes' attributes

    generating JWT for user ID 1 with no roles
    """
    token = generate_token(1)
    if request.cls is not None:
        request.cls.token_roleless = token
    return token
