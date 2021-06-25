#!env/bin/python3

import logging
import asyncio
import time
import sys
import os

import sshd

import ariadne.asgi
import ariadne

import schema as schema_factory
import config

cfg = config.get(None)
schema = schema_factory.create()
app = ariadne.asgi.GraphQL(
    schema, context_value=schema_factory.context(cfg), debug=True
)
