from flask import _request_ctx_stack, current_app, jsonify, url_for as _url_for

from mykro_common import requests


def url_for(*args, **kwargs):
    """url_for replacement that works even when there is no request context."""
    if "_external" not in kwargs:
        kwargs["_external"] = False
    reqctx = _request_ctx_stack.top
    if reqctx is None:
        if kwargs["_external"]:
            raise RuntimeError(
                "Cannot generate external URLs without a request context."
            )
        with current_app.test_request_context():
            return _url_for(*args, **kwargs)
    return _url_for(*args, **kwargs)


def register_endpoints(app):
    """Function registering all endpoints

    Registers all endpoints from the given app to the 'MS-Endpoint-Registry' service.

    :param app: Flask's app object"""

    def create_rules_list():
        rules_list = []
        for rule in app.url_map.iter_rules():
            rules_list.append(
                {
                    "server_name": app.config["SERVER_NAME"],
                    "app_root": app.config["APPLICATION_ROOT"],
                    "subdomain": rule.subdomain,
                    "rule": rule.rule,
                    "api_url": True if "/api/" in rule.rule else False,
                    "arguments": [arg for arg in rule.arguments],
                    "defaults": rule.defaults,
                    "methods": [
                        meth
                        for meth in rule.methods
                        if meth != "HEAD" and meth != "OPTIONS"
                    ],
                    "endpoint": rule.endpoint,
                }
            )
        return rules_list

    reg_rul = "/api/endpoint_registry"
    payload = jsonify(create_rules_list())

    r = requests.post(reg_rul, json=payload)

    if r.status_code != 204:
        raise
