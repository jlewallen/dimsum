import inspect
import logging

import pytest
import wrapt

import model.entity as entity
import model.properties as properties
import model.hooks as hooks
import scopes

log = logging.getLogger("dimsum.tests")


@pytest.mark.asyncio
async def test_simple_hook_one_arg():
    h = hooks.All()

    @h.observed.target
    def observe(entity: entity.Entity):
        log.info("observe")
        return [entity]

    @h.observed.hook
    def hide_invisible_entities(fn, entity: entity.Entity):
        log.info("hiding invisible")
        return fn(entity)

    jacob = scopes.alive(props=properties.Common("Jacob"))

    observe(jacob)
