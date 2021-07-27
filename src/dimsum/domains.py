import time
import dataclasses
import functools
import pprint
import contextvars
from croniter import croniter
from datetime import datetime
from typing import Any, cast, Dict, List, Literal, Optional, Union, Callable, Tuple

import dynamic
import grammars
import handlers
import tools
import proxying
import saying
import serializing
import storage
from loggers import get_logger
from bus import EventBus, SubscriptionManager
from model import (
    Entity,
    World,
    CompiledJson,
    Registrar,
    Serialized,
    WorldKey,
    Event,
    Action,
    Permission,
    TickEvent,
    EntityFrozen,
    Failure,
    Comms,
    Reply,
    ExtendHooks,
    Condition,
    cleanup_entity,
    Ctx,
    MaterializeAndCreate,
    context,
    find_entity_area,
    find_entity_area_maybe,
    get_well_known_key,
    set_well_known_key,
    WelcomeAreaKey,
    get_current_gid,
    set_current_gid,
    MissingEntityException,
    SecurityCheckException,
)
from model.permissions import generate_security_check_from_json_diff, SecurityContext
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.movement as movement
import scopes.occupyable as occupyable
import scopes.inbox as inbox
import scopes as scopes

log = get_logger("dimsum.domains")
active_session: contextvars.ContextVar = contextvars.ContextVar("dimsum:session")
scopes.set_proxy_factory(proxying.create)  # TODO cleanup


def _finding_log():
    return get_logger("dimsum.domain.finding")


def _notify_log():
    return get_logger("dimsum.domain.notify")


def _get() -> "Session":
    session = active_session.get()
    assert session
    return session


def infinite_reach(entity: Entity, depth: int):
    return 0


def default_reach(entity: Entity, depth: int):
    if entity.klass == scopes.AreaClass:
        if depth == 2:
            return -1
        return 1
    return 0


@dataclasses.dataclass
class DiffSecurityException(Exception):
    entity: Entity
    diff: Dict[str, Any]
    sce: SecurityCheckException

    def __str__(self):
        return """
Entity: '{2}'

Diff:
{0}

SecurityException:
{1}
""".format(
            pprint.pformat(self.diff), self.sce, self.entity
        )


@dataclasses.dataclass
class SaveDynamicCalls(dynamic.DynamicCallsListener):
    domain: "Domain"
    session: "Session"

    @property
    def log(self):
        return get_logger("dimsum.dynamic.calls")

    async def _update_in_session(
        self, session: "Session", calls: List[dynamic.DynamicCall], executable
    ):
        for call in calls:
            entity = await session.materialize(key=call.entity_key)
            assert entity
            self.log.info("calls: %s key=%s", entity, entity.key)
            self.log.info("calls: %s %s", entity, call)
            dynamic.log_behavior(
                entity,
                dict(
                    context=call.context,
                    logs=call.logs,
                    exceptions=call.exceptions,
                    success=not call.exceptions,
                    time=call.time,
                    elapsed=call.elapsed,
                ),
                executable=executable,
            )

    async def save_dynamic_calls_after_success(self, calls: List[dynamic.DynamicCall]):
        self.log.info("success: saving calls using existing session")
        await self._update_in_session(self.session, calls, True)

    async def save_dynamic_calls_after_failure(self, calls: List[dynamic.DynamicCall]):
        self.log.info("failure: saving calls using pristine session")
        pristine = await self.domain.reload()
        with pristine.session() as session:
            await self._update_in_session(session, calls, False)
            await session.save()

        # Ensure no attempt is made.
        session.rollback()


@dataclasses.dataclass
class FutureTask:
    when: datetime


@dataclasses.dataclass
class WhenCron(FutureTask):
    crons: List[dynamic.Cron]


@dataclasses.dataclass
class QueuedTask(FutureTask):
    entity_key: str
    message: str


@dataclasses.dataclass
class CronTab:
    crons: List[dynamic.Cron]

    def get_future_task(self) -> Optional[WhenCron]:
        wc: Optional[WhenCron] = None
        base = datetime.now()
        log.debug("summarize: %s", base)
        curr: Optional[Tuple[datetime, List[dynamic.Cron]]] = None
        for cron in self.crons:
            iter = croniter(cron.spec, base)
            when = iter.get_next(datetime)
            if curr is None or when < curr[0]:
                curr = (when, [])
            if when == curr[0]:
                curr[1].append(cron)
            log.debug("%s iter=%s curr=%s", cron, when, curr)
        if curr:
            return WhenCron(curr[0], curr[1])
        return None


@dataclasses.dataclass
class Session(MaterializeAndCreate):
    store: storage.EntityStorage
    schedule: Callable[[FutureTask], None] = dataclasses.field(repr=False)
    calls_saver: Callable = dataclasses.field(repr=False)
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
                sec_log.info("security(%s) %s", entity, c.key)
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

    async def execute(self, person: Entity, command: str):
        assert self.world
        log.info("executing: '%s'", command)

        with WorldCtx(session=self, person=person, calls_saver=self.calls_saver) as ctx:
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
                    assert action
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

        with WorldCtx(
            session=self, person=person, calls_saver=self.calls_saver, **kwargs
        ) as ctx:
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
                with WorldCtx(
                    session=self,
                    calls_saver=self.calls_saver,
                    entity=entity,
                ) as ctx:
                    await ctx.notify(
                        ev, area=tools.area_of(entity), post=await ctx.post(), **kwargs
                    )
                    await ctx.complete()

    async def service(self, now: datetime, scheduled: Optional[FutureTask] = None):
        assert self.world

        log.info("service now=%s", now)
        if scheduled:
            log.info("scheduled: %s", scheduled)
            if isinstance(scheduled, WhenCron):
                for cron in scheduled.crons:
                    event = dynamic.CronEvent(cron.entity_key, cron.spec)
                    await self._notify_entity(event.entity_key, event)

        post_service = await inbox.create_post_service(self, self.world)
        queued = await post_service.service(now)
        for qm in queued:
            try:
                await self._notify_entity(qm.entity_key, qm.message)
            except MissingEntityException as e:
                log.exception("missing entity", exc_info=True)

        log.info("service loading crons")

        removing: List[str] = []

        async def _get_crons(key: str):
            try:
                entity = await self.materialize(
                    key=key
                )  # NOTE refresh intentionally False
                with entity.make(behavior.Behaviors) as behave:
                    if behave.get_default():
                        with WorldCtx(
                            session=self,
                            calls_saver=self.calls_saver,
                            entity=entity,
                        ) as ctx:
                            crons = await ctx.find_crons()
                            assert crons is not None
                            return crons
            except MissingEntityException as e:
                log.exception("missing entity", exc_info=True)
                removing.append(key)
                return []

        with self.world.make(behavior.BehaviorCollection) as servicing:
            everything = servicing.entities.keys()
            crons = flatten([await _get_crons(key) for key in everything])

            tab = CronTab(crons)
            future_task = tab.get_future_task()
            if future_task:
                log.info("crons: %s", future_task)
                self.schedule(future_task)
            for key in removing:
                log.warning("removing %s from world behaviors", key)
                del servicing.entities[key]
                self.world.touch()

        log.debug("service crons loaded")

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


class Domain:
    def __init__(
        self,
        store: Optional[storage.EntityStorage] = None,
        subscriptions: Optional[SubscriptionManager] = None,
        **kwargs,
    ):
        super().__init__()
        self.store = store if store else storage.SqliteStorage(":memory:")
        self.subscriptions = subscriptions if subscriptions else SubscriptionManager()
        self.comms: Comms = self.subscriptions
        self.handlers = [handlers.create(self.subscriptions)]
        self.scheduled: Optional[FutureTask] = None

    def session(self) -> "Session":
        log.info("session:new")

        def different_crons(lh: FutureTask, rh: FutureTask) -> bool:
            if isinstance(lh, WhenCron) and isinstance(rh, WhenCron):
                lh_specs = [cs.key() for cs in lh.crons]
                rh_specs = [cs.key() for cs in rh.crons]
                return lh_specs != rh_specs
            return False

        def schedule(value: FutureTask):
            logger = get_logger("dimsum.schedule")

            if value and self.scheduled:
                if (
                    value.when >= self.scheduled.when
                    and self.scheduled.when > datetime.now()
                ):
                    if value.when == self.scheduled.when:
                        if not different_crons(value, self.scheduled):
                            logger.debug(
                                "ignored(crons): %s vs %s", value, self.scheduled
                            )
                            return
                    else:
                        logger.debug("ignored(later): %s vs %s", value, self.scheduled)
                        return
            if self.scheduled != value:
                logger.info("scheduled: %s", value)
            self.scheduled = value

        return Session(
            store=self.store,
            handlers=self.handlers,
            schedule=schedule,
            calls_saver=self.create_calls_saver,
        )

    def create_calls_saver(self, session: "Session"):
        return SaveDynamicCalls(self, session)

    async def reload(self):
        return Domain(empty=True, store=self.store)


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
        self.calls_saver: Callable[
            [], dynamic.DynamicCallsListener
        ] = functools.partial(calls_saver, session)

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
        async with dynamic.Behavior(self.calls_saver(), self.entities) as db:
            await db.notify(ev, say=self.say, session=self.session, **kwargs)

    async def find_crons(self):
        assert self.world
        _notify_log().debug("find-crons: entities=%s", self.entities)
        async with dynamic.Behavior(dynamic.ErrorOnDynamicCall(), self.entities) as db:
            return await db.find_crons()

    async def complete(self):
        post = await self.post()
        pending = await post.peek()
        if pending:
            self.session.schedule(QueuedTask(*pending))
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
                has = [e.has(scope) for scope in scopes]
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


def flatten(l):
    return [item for sl in l for item in sl]
