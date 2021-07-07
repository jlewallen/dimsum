#!env/bin/python3

import ariadne.asgi
import config
import schema as schema_factory


def app():
    cfg = config.get(None)
    schema = schema_factory.create()
    domain = cfg.make_domain()
    return ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, domain),
        debug=True,
    )
