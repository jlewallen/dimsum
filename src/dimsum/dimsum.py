#!env/bin/python3

import ariadne.asgi

import config
import schema as schema_factory
from loggers import get_logger

log = get_logger("dimsum")


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
