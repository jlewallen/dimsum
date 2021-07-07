#!env/bin/python3

import logging
import ariadne.asgi
import schema as schema_factory
import config


def app():
    cfg = config.get(None)
    schema = schema_factory.create()
    domain = cfg.make_domain()
    return ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, domain),
        debug=True,
    )
