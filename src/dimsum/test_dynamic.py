from typing import Callable

import sys
import logging
import pytest

import model.game as game
import model.properties as properties
import model.world as world

import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes.behavior as behavior
import model.scopes as scopes

import plugins.default.actions

import test

log = logging.getLogger("dimsum.tests")

import ast
from test_decoration import Hooks, Hello


@pytest.mark.asyncio
async def test_python_evaluate(caplog):
    tw = test.TestWorld()
    await tw.initialize()

    code = """
# Hello

# log.info("Hello!")
# for g in globals():
#    log.info("global: %s", g)

@link.wrap(Hello, Hello.yell)
def hello(name: str):
    log.info("saying Hello %s!", name)

# hello("inside")
"""

    linking = Hooks()
    gs = dict(log=log, link=linking, Hello=Hello)
    tree = ast.parse(code)
    compiled = compile(tree, filename="<ast>", mode="exec")
    eval(compiled, gs, dict())

    log.info("linking: %s", linking)
