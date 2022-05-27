import dataclasses
import functools
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Sequence,
    Union,
    Tuple,
    TYPE_CHECKING,
)

from loggers import get_logger
from model import Entity, World, Event, Ctx, find_entity_area, cleanup_entity, context
import scopes.inbox as inbox
import tools
import saying

from dynamic import DynamicCallsListener, Behavior

from .session import Session

log = get_logger("dimsum.domains")


class WorldCtx(Ctx):
    def __init__(
        self,
        session: Optional[Session] = None,
        calls_saver: Optional[Callable] = None,
        person: Optional[Entity] = None,
        entity: Optional[Entity] = None,
        **kwargs,
    ):
        super().__init__()
        assert session and session.world
        assert calls_saver
        self.session = session
        self.person = person
        self.previous: Optional[Ctx] = None
        self.reference = person or entity
        self.bus = session.bus
        self.entities: tools.EntitySet = self._get_default_entity_set(entity)
        self.say = saying.Say()
        self._post: Optional[inbox.PostService] = None
        self.calls_saver: Callable[[], DynamicCallsListener] = functools.partial(
            calls_saver, session
        )

    @property
    def world(self) -> World:
        assert self.session.world
        return self.session.world

    async def post(self):
        if self._post:
            return self._post
        self._post = await inbox.create_post_service(self, self.world)
        return self._post

    def _get_default_entity_set(self, entity: Optional[Entity]) -> tools.EntitySet:
        assert self.world
        entitySet = tools.EntitySet()
        if self.person:
            entitySet = tools.get_contributing_entities(self.world, self.person)
        else:
            entitySet.add(tools.Relation.WORLD, self.world)
        if entity:
            entitySet.add(tools.Relation.OTHER, entity)
        return entitySet

    def __enter__(self):
        self.previous = context.maybe_get()
        context.set(self)
        return self

    def __exit__(self, type, value, traceback):
        context.set(self.previous)
        return False

    def extend(self, **kwargs) -> "WorldCtx":
        for key, l in kwargs.items():
            log.info("extend '%s' %s", key, l)
            if isinstance(l, list):
                for e in l:
                    self.entities.add(tools.Relation.OTHER, e)
            else:
                self.entities.add(tools.Relation.OTHER, l)
        return self

    def register(self, entity: Entity) -> Entity:
        return self.session.register(entity)

    def unregister(self, destroyed: Entity) -> Entity:
        cleanup_entity(destroyed, world=self.world)
        return self.session.unregister(destroyed)

    def find_by_key(self, key: str) -> Entity:
        return self.session.find_by_key(key)

    async def standard(self, klass, *args, **kwargs):
        assert self.world
        if self.person:
            assert self.person
            area = await find_entity_area(self.person)
            a = (self.person, area, []) + args
            await self.publish(klass(*a, **kwargs))

    async def notify(self, ev: Event, **kwargs):
        assert self.world
        _notify_log().info("notify: %s entities=%s", ev, self.entities)
        async with Behavior(self.calls_saver(), self.entities) as db:
            await db.notify(ev, say=self.say, session=self.session, **kwargs)

    async def find_crons(self):
        assert self.world
        _notify_log().debug("find-crons: entities=%s", self.entities)
        async with Behavior(self.calls_saver(), self.entities) as db:
            return await db.find_crons()

    async def complete(self):
        assert self.reference
        await self.say.publish(self.reference)

    async def publish(self, ev: Event):
        assert self.world
        await self.bus.publish(ev)
        await self.notify(ev)

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, register=True, **kwargs
    ) -> Entity:
        return self.session.create_item(
            quantity=quantity, initialize=initialize, register=register, **kwargs
        )

    async def find_item(
        self, candidates=None, scopes=[], exclude=None, number=None, **kwargs
    ) -> Optional[Entity]:
        _finding_log().info(
            "find-item: gid=%s candidates=%s exclude=%s scopes=%s kw=%s",
            number,
            candidates,
            exclude,
            scopes,
            kwargs,
        )

        if number is not None:
            maybe_by_gid = await self.session.try_materialize(gid=number)
            if maybe_by_gid.empty():
                return None
            return maybe_by_gid.one()

        if len(candidates) == 0:
            return None

        found: Optional[Entity] = None

        for e in candidates:
            if exclude and e in exclude:
                continue

            if scopes:
                has = [scope for scope in scopes if e.has(scope)]
                if len(has) == 0:
                    continue

            if e.describes(**kwargs):
                return e
            else:
                if "q" in kwargs:
                    found = None
                else:
                    found = e

        return found

    async def apply_item_finder(
        self, person: Entity, finder, **kwargs
    ) -> Optional[Entity]:
        assert person
        assert finder
        area = await find_entity_area(person)
        _finding_log().info("applying finder:%s %s", finder, kwargs)
        found = await finder.find_item(area=area, person=person, world=self, **kwargs)
        if found:
            _finding_log().info("found: {0}".format(found))
        else:
            _finding_log().info("found: nada")
        return found

    async def try_materialize_key(self, key: str) -> Optional[Entity]:
        return await self.session.try_materialize_key(key)


def _notify_log():
    return get_logger("dimsum.domain.notify")


def _finding_log():
    return get_logger("dimsum.domain.finding")
