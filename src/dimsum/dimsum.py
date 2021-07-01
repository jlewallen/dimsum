#!env/bin/python3

import logging
import ariadne.asgi
import schema as schema_factory
import config
import bus


def app():
    cfg = config.get(None)
    schema = schema_factory.create()
    subscriptions = bus.SubscriptionManager()
    return ariadne.asgi.GraphQL(
        schema, context_value=schema_factory.context(cfg, subscriptions), debug=True
    )
