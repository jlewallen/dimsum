import logging
import inflect
from typing import Optional

from model import Entity, World, Hooks, install_hooks, Hooks, hooks

import scopes as scopes
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.mechanics as mechanics

import plugins.chatting  # noqa
import plugins.creation  # noqa
import plugins.digging  # noqa
import plugins.editing  # noqa
import plugins.fallback  # noqa
import plugins.admin  # noqa
import plugins.looking  # noqa
import plugins.moving  # noqa
import plugins.clothing  # noqa
import plugins.dining  # noqa
import plugins.carrying  # noqa

p = inflect.engine()

log = logging.getLogger("dimsum")


class EntityHooks(Hooks):
    def describe(self, entity: Entity) -> str:
        if entity.klass == scopes.LivingClass:
            return "{0} (#{1})".format(entity.props.name, entity.props.gid)
        if entity.klass == scopes.AreaClass:
            return "{0} (#{1})".format(entity.props.name, entity.props.gid)
        if entity.has(carryable.Carryable):
            with entity.make_and_discard(carryable.Carryable) as carry:
                if carry.quantity > 1:
                    return "{0} {1} (#{2})".format(
                        carry.quantity,
                        p.plural(entity.props.name, carry.quantity),
                        entity.props.gid,
                    )
        return "{0} (#{1})".format(p.a(entity.props.name), entity.props.gid)

    def cleanup(self, entity: Entity, world: Optional[World] = None, **kwargs):
        assert world
        if world.has(behavior.BehaviorCollection):
            log.info("cleanup %s", entity)
            with world.make(behavior.BehaviorCollection) as collection:
                if entity in collection.entities:
                    collection.entities.remove(entity)
                    world.touch()


install_hooks(EntityHooks())


@hooks.all.observed.hook
def hide_invisible_entities(resume, entity: Entity):
    if entity.make_and_discard(mechanics.Visibility).is_invisible:
        return []
    return resume(entity)
