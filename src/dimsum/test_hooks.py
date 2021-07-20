import inspect
import logging
import wrapt
import pytest

from model import *
import scopes

log = logging.getLogger("dimsum.tests")


@pytest.mark.asyncio
async def test_simple_hook_one_arg():
    h = hooks.All()

    @h.observed.target
    def observe(entity: Entity):
        log.info("observe")
        return [entity]

    @h.observed.hook
    def hide_invisible_entities(fn, entity: Entity):
        log.info("hiding invisible: %s", fn)
        return fn(entity)

    @h.observed.hook
    def hide_randomly(fn, entity: Entity):
        log.info("hiding randomly: %s", fn)
        return fn(entity)

    jacob = scopes.alive(props=Common("Jacob"))

    observe(jacob)
