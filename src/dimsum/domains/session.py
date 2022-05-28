import dataclasses
import time
import functools
import pprint
import contextvars
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Sequence,
    Union,
    Tuple,
    cast,
)
from datetime import datetime

from model import (
    Entity,
    World,
    WorldKey,
    Event,
    Ctx,
    Reply,
    Failure,
    Permission,
    CompiledJson,
    MaterializeAndCreate,
    Registrar,
    MissingEntityException,
    EntityFrozen,
    find_entity_area_maybe,
    get_well_known_key,
    set_well_known_key,
    WelcomeAreaKey,
    get_current_gid,
    set_current_gid,
    generate_security_check_from_json_diff,
    SecurityContext,
    SecurityCheckException,
    Serialized,
    ExtendHooks,
    Unknown,
    Action,
)
from storage import EntityStorage
from loggers import get_logger
from bus import EventBus

import scopes.occupyable as occupyable
import scopes.movement as movement
import scopes.carryable as carryable
import scopes.behavior as behavior
import scopes.inbox as inbox
import scopes
import tools

import dynamic
import grammars
import serializing
import proxying

active_session: contextvars.ContextVar = contextvars.ContextVar("dimsum:session")
log = get_logger("dimsum.domains")


def infinite_reach(entity: Entity, depth: int):
    return 0


def default_reach(entity: Entity, depth: int):
    if entity.klass == scopes.AreaClass:
        if depth == 2:
            return -1
        return 1
    return 0


@dataclasses.dataclass
class Session(MaterializeAndCreate):
    store: EntityStorage
    calls_saver: Callable = dataclasses.field(repr=False)
    ctx_factory: Callable = dataclasses.field(repr=False)
    handlers: List[Any] = dataclasses.field(default_factory=list, repr=False)
    registrar: Registrar = dataclasses.field(default_factory=Registrar, repr=False)
    world: Optional[World] = None
    created: float = dataclasses.field(default_factory=lambda: time.time())
    failed: bool = False

    @functools.cached_property
    def bus(self):
        return EventBus(handlers=self.handlers or [])

    def rollback(self):
        self.failed = True

    def find_by_key(self, key: str) -> Entity:
        e = self.registrar.find_by_key(key)
        assert e
        return e

    async def save(
        self,
        create_security_context: Optional[Callable[[Entity], SecurityContext]] = None,
    ) -> List[str]:
        log.info("saving %s", self.store)

        # Make sure that we haven't been marked for failure by an
        # earlier exception or issue.
        assert not self.failed

        # If we materialized the world, then make sure we update the
        # gid we're on.
        if self.world:
            assert self.world
            set_current_gid(self.world, self.registrar.number)

        # Make sure every modified entity also has its described name
        # updated to reflect its latest state.
        for key, mod in self.registrar.modified().items():
            mod.props.described = mod.describe()

        # Compile all of the changes that are being attempted in this
        # session, including changes that weren't explicitly touched
        # by the developer.
        compiled = serializing.for_update(self.registrar.entities.values())
        modified = self.registrar.filter_modified(compiled)

        # Security check.
        sec_log = get_logger("dimsum.security")
        updating: Dict[str, CompiledJson] = {}
        for key, c in modified.items():
            entity = self.registrar.find_by_key(key)
            assert entity
            assert c.saving
            if c.diff:
                sec_log.debug("security(%s) %s", entity, c.key)
                check = generate_security_check_from_json_diff(
                    c.saving.compiled, c.diff
                )
                sec_log.debug("%s diff=%s", key, c.diff)
                sec_log.debug("%s acls=%s", key, check.acls)
                if create_security_context:
                    try:
                        sc = create_security_context(entity)
                        sec_log.info("verifying %s %s %s", c.key, entity, sc)
                        await check.verify(Permission.WRITE, sc)
                    except SecurityCheckException as sce:
                        raise DiffSecurityException(entity, c.diff, sce)
            updating[key] = c.saving

        # Update the entities and return their new state, which should
        # only be different by the updated version number.
        updated = await self.store.update(updating)

        # Patch versions in loaded entities to reflect reality. This
        # isn't the prettiest code by any means but it does work and
        # it's much faster than reloading completely from the store or
        # fully unpickling the entity.
        for key, cu in updated.items():
            new_version = cu.compiled["version"]["i"]  # UGLY
            loaded = self.registrar.find_by_key(key)
            assert loaded
            loaded.version.i = new_version

        return [key for key, _ in updated.items()]

    def __enter__(self) -> "Session":
        active_session.set(self)
        return self

    def __exit__(self, type, value, traceback) -> Literal[False]:
        active_session.set(None)
        finished = time.time()
        elapsed = finished - self.created
        self.registrar.log_summary()
        log.info("session:elapsed %fms", elapsed * 1000)
        return False

    def register(self, entity: Entity) -> Entity:
        return self.registrar.register(entity)

    def unregister(self, entity: Entity) -> Entity:
        return self.registrar.unregister(entity)

    async def try_materialize_key(self, key: str) -> Optional[Entity]:
        maybe = await self.try_materialize(key=key)
        return maybe.maybe_one()

    async def try_materialize(
        self,
        key: Optional[str] = None,
        gid: Optional[int] = None,
        json: Optional[List[Serialized]] = None,
        reach=None,
        refresh=None,
        migrate=None,
    ) -> serializing.Materialized:
        materialized = await serializing.materialize(
            registrar=self.registrar,
            store=self.store,
            key=key,
            gid=gid,
            json=json,
            reach=reach if reach else default_reach,
            proxy_factory=proxying.create,
            refresh=refresh,
            migrate=migrate,
        )

        for updated_world in [e for e in materialized.all() if e.key == WorldKey]:
            assert isinstance(updated_world, World)
            self.world = updated_world

        return materialized

    async def materialize(self, **kwargs) -> Entity:
        materialized = await self.try_materialize(**kwargs)
        return materialized.one()

    async def prepare(self, reach=None):
        if self.world:
            return self.world

        maybe_world = await self.try_materialize(
            key=WorldKey, reach=reach if reach else None
        )

        if maybe_world.maybe_one():
            self.world = cast(World, maybe_world.one())
            assert isinstance(self.world, World)

        if self.world:
            self.registrar.number = get_current_gid(self.world)
            return self.world

        log.info("creating new world")
        self.world = World()
        self.register(self.world)
        return self.world

    def ctx(self, **kwargs) -> Ctx:
        return self.ctx_factory(session=self, calls_saver=self.calls_saver, **kwargs)

    async def execute(self, person: Entity, command: str):
        assert self.world
        log.info("executing: '%s'", command)

        with self.ctx(person=person) as ctx:
            contributing = tools.get_contributing_entities(self.world, person)
            async with dynamic.Behavior(self.calls_saver(self), contributing) as db:
                log.info("hooks: %s", db.dynamic_hooks)
                evaluator = grammars.PrioritizedEvaluator(
                    [db.lazy_evaluator] + grammars.create_static_evaluators()
                )
                with ExtendHooks(db.dynamic_hooks):
                    log.debug("evaluator: '%s'", evaluator)
                    action = await evaluator.evaluate(
                        command, world=self.world, person=person
                    )
                    action = action or Unknown()
                    assert isinstance(action, Action)
                    roles = action.gather_roles()
                    return await self.perform(action, person)

    async def perform(
        self,
        action,
        person: Optional[Entity] = None,
        dynamic_behavior: Optional["dynamic.Behavior"] = None,
        **kwargs,
    ) -> Reply:

        log.info("perform %s", action)

        world = await self.prepare()

        area = await find_entity_area_maybe(person) if person else None

        with self.ctx(person=person, **kwargs) as ctx:
            try:
                reply = await action.perform(
                    world=world,
                    area=area,
                    person=person,
                    ctx=ctx,
                    say=ctx.say,
                    post=await ctx.post(),
                )
                await ctx.complete()
                return reply
            except EntityFrozen:
                return Failure("whoa, that's frozen")

    async def _notify_entity(self, key: str, ev: Event, **kwargs):
        # Materialize from the target entity to ensure we have
        # enough in memory to carry out its behavior.
        entity = await self.materialize(key=key, refresh=True)
        with entity.make(behavior.Behaviors) as behave:
            if behave.get_default():
                log.info("notifying: %s", entity)
                with self.ctx(entity=entity) as ctx:
                    await ctx.notify(
                        ev, area=tools.area_of(entity), post=await ctx.post(), **kwargs
                    )
                    await ctx.complete()

    async def everywhere(self, ev: Event, **kwargs):
        assert self.world

        log.info("everywhere:%s %s", ev, kwargs)
        everything: List[str] = []
        with self.world.make(behavior.BehaviorCollection) as world_behaviors:
            everything = world_behaviors.entities.keys()
            removing: List[str] = []
            for key in everything:
                log.info("everywhere: %s", key)
                try:
                    await self._notify_entity(key, ev)
                except MissingEntityException as e:
                    log.exception("missing entity", exc_info=True)
                    removing.append(key)
            for key in removing:
                log.warning("removing %s from world behaviors", key)
                del world_behaviors.entities[key]

    async def add_area(
        self, area: Entity, depth=0, seen: Optional[Dict[str, str]] = None
    ):
        await self.prepare()

        assert area
        assert self.world

        if seen is None:
            seen = {}

        if area.key in seen:
            return

        occupied = area.make(occupyable.Occupyable).occupied
        wa_key = get_well_known_key(self.world, WelcomeAreaKey)
        if not wa_key:
            set_well_known_key(self.world, WelcomeAreaKey, area.key)
        else:
            existing = await self.materialize(key=wa_key)
            assert existing
            existing_occupied = existing.make_and_discard(
                occupyable.Occupyable
            ).occupied
            if len(existing_occupied) < len(occupied):
                log.info("updating welcome-area")
                assert area
                set_well_known_key(self.world, WelcomeAreaKey, area.key)

        seen[area.key] = area.key

        log.debug("add-area:%d %s %s", depth, area.key, area)

        self.registrar.register(area)

        for entity in area.make(occupyable.Occupyable).occupied:
            self.registrar.register(entity)

        for entity in area.make(carryable.Containing).holding:
            self.registrar.register(entity)

        for item in area.make(carryable.Containing).holding:
            maybe_area = item.make(movement.Exit).area
            if maybe_area:
                log.debug("linked-via-ex[%s] %s", depth, maybe_area)
                await self.add_area(maybe_area, depth=depth + 1, seen=seen)

            for linked in item.make(movement.Movement).adjacent():
                log.debug("linked-via-item[%d]: %s (%s)", depth, linked, item)
                await self.add_area(linked, depth=depth + 1, seen=seen)

        for linked in area.make(movement.Movement).adjacent():
            log.debug("linked-adj[%d]: %s", depth, linked)
            await self.add_area(linked, depth=depth + 1, seen=seen)

        log.debug("area-done:%d %s", depth, area.key)

    def create_item(
        self, quantity: Optional[float] = None, initialize=None, register=True, **kwargs
    ) -> Entity:
        initialize = initialize if initialize else {}
        if quantity:
            initialize = {carryable.Carryable: dict(quantity=quantity)}
        created = scopes.item(initialize=initialize, **kwargs)
        if register:
            return self.register(created)
        return created


@dataclasses.dataclass
class DiffSecurityException(Exception):
    entity: Entity
    diff: Dict[str, Any]
    sce: SecurityCheckException

    def __str__(self):
        return """
Entity: {2}

Diff:
{0}

SecurityException:
{1}
""".format(
            pprint.pformat(self.diff), self.sce, self.entity
        )
