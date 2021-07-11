#!env/bin/python3

import ariadne.asgi
import logging
import config
import schema as schema_factory

log = logging.getLogger("dimsum")


def app():
    log.info("starting")
    cfg = config.get(None)
    schema = schema_factory.create()
    domain = cfg.make_domain()
    return ariadne.asgi.GraphQL(
        schema,
        context_value=schema_factory.context(cfg, domain),
        debug=True,
    )
