import time
import dataclasses
import functools
import ast
import traceback
import sys
import inspect
from collections import ChainMap, abc
from typing import List, Dict, Any, Optional, Callable, Union

from loggers import get_logger
from model import (
    Entity,
    World,
    Event,
    context,
    All,
    Action,
    Unknown,
    AlwaysTrue,
    ArgumentTransformer,
    CronKey,
)
import tools
import grammars
import serializing
import scopes.inbox as inbox

from .core import (
    DynamicEntitySources,
    EntityBehavior,
    LibraryBehavior,
    LanguageHandler,
    EventHandler,
    CronHandler,
    Dynsum,
)
from .calls import DynamicCall
from .dynpost import DynamicPostService
from .language import SimplifiedTransformer
from .ldc import log_dynamic_call
from .conditions import bind_conditions
from .frames import _get_default_globals

log = get_logger("dimsum.dynamic")
errors_log = get_logger("dimsum.dynamic.errors")


@dataclasses.dataclass
class Logger:
    log: Callable

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        if type:
            self.log(
                ex=dict(
                    exception=str(type),
                    value=str(value),
                    traceback=traceback.format_exception(type, value, tb),
                )
            )
        else:
            self.log()
        return False


@functools.lru_cache
def _compile(sources: DynamicEntitySources, compiled_name: str) -> EntityBehavior:
    frame = _get_default_globals()
    started = time.time()

    def load_entity() -> Entity:
        """
        Loads the Entity owning the behavior as a parameter, aliased
        to 'this'. Parameters that are callable end up called as part
        of the resolution process. See CustomizeCallArguments
        """
        return context.get().find_by_key(sources.entity_key)

    def wrapper_factory(fn):
        """
        Creates a function call wrapper for functions declared in
        an Entity's dynamic behavior. This is done to allow for
        flexible call signatures and so that errors can be logged to
        the proper place and with debugging context.

        Synchronous and asynchronous functions are both supported, for
        now. Synchronous is on the chopping block.
        """

        def create_logger(lokals, fnargs, fnkw) -> Logger:
            log = functools.partial(
                log_dynamic_call,
                sources,
                fn.__name__,
                time.time(),
                frame=frame,
                lokals=lokals,
                fnargs=fnargs,
                fnkw=fnkw,
            )
            return Logger(log)

        def create_thunk_locals(args, kwargs) -> Dict[str, Any]:
            assert context.get()
            log.info("thunking: args=%s kwargs=%s", args, kwargs)
            actual_args = CustomizeCallArguments(dict(this=load_entity)).transform(
                fn, list(args), {**kwargs, **dict(ctx=context.get())}
            )
            return dict(thunk=(fn, actual_args, {}))

        def sync_thunk(*args, **kwargs):
            lokals = create_thunk_locals(args, kwargs)

            def aexec():
                exec(
                    """
def __ex(t=thunk):
    __thunk_ex = None
    try:
        return t[0](*t[1], **t[2])
    except Exception as e:
        __thunk_ex = e
        raise e
""",
                    frame,
                    lokals,
                )
                return lokals["__ex"]()

            with create_logger(lokals, args, kwargs):
                return aexec()

        async def async_thunk(*args, **kwargs):
            lokals = create_thunk_locals(args, kwargs)

            async def aexec():
                exec(
                    """
async def __ex(t=thunk):
    __thunk_ex = None
    try:
        return await t[0](*t[1], **t[2])
    except Exception as e:
        __thunk_ex = e
        raise e
""",
                    frame,
                    lokals,
                )
                return await lokals["__ex"]()

            with create_logger(lokals, args, kwargs):
                return await aexec()

        return async_thunk if inspect.iscoroutinefunction(fn) else sync_thunk

    try:
        # Start by compiling the code, if this fails we can bail right
        # away before creating soem of the heavier objects.
        log.info("compiling %s %s", compiled_name, sources)
        tree = ast.parse(sources.behaviors[0].source)
        evaluating = compile(tree, filename=compiled_name, mode="exec")

        # This is also assed to the script in the globals as `ds` and
        # exposes the Dynsum interface.
        compiled = CompiledEntityBehavior(
            entity_key=sources.entity_key,
            wrapper_factory=wrapper_factory,
            entity_hooks=All(wrapper_factory=wrapper_factory),
        )

        # Wish we could use ChainMap here, instead update globals with
        # the wrapper that's used to remember and direct dynamic
        # calls and with conditonal partials.
        frame.update(**dict(ds=compiled))

        # Also provide partial ctors for a few conditions, local to
        # this entity. This provides Held and Ground, for example.
        frame.update(**compiled.conditions())

        # We squash any declarations left in locals into our
        # globals so they're available in future calls via a
        # rebinding in our thunk factory above. I'm pretty sure
        # this is the only way to get this to behave.
        eval(evaluating, frame, compiled.declarations)

        # Merge local declarations into global frame. This will be all
        # the useful classes and globals the user's module defines.
        frame.update(**compiled.declarations)

        # Return compiled behavior, declarations is used for deserializing.
        return compiled
    except:
        errors_log.exception("dynamic:compile", exc_info=True)
        log_dynamic_call(sources, ":compile:", started, frame=frame, exc_info=True)
        raise


@dataclasses.dataclass
class CompiledEntityBehavior(EntityBehavior, Dynsum):
    entity_key: str
    entity_hooks: All
    wrapper_factory: Callable = dataclasses.field(repr=False)
    prose_handlers: List[LanguageHandler] = dataclasses.field(default_factory=list)
    event_handlers: List[EventHandler] = dataclasses.field(default_factory=list)
    cron_handlers: List[CronHandler] = dataclasses.field(default_factory=list)
    evaluator_override: Optional[grammars.CommandEvaluator] = None
    declarations: Dict[str, Any] = dataclasses.field(default_factory=dict)

    def language(self, prose: str, condition=None):
        def wrap(fn):
            log.info("prose: '%s' %s", prose, fn)
            self.prose_handlers.append(
                LanguageHandler(
                    prose=prose,
                    fn=self.wrapper_factory(fn),
                    condition=condition or AlwaysTrue(),
                )
            )
            return fn

        return wrap

    def cron(self, spec: str):
        def wrap(fn):
            log.info("cron: '%s' %s", spec, fn)
            self.cron_handlers.append(
                CronHandler(
                    entity_key=self.entity_key, spec=spec, fn=self.wrapper_factory(fn)
                )
            )
            self.event_handlers.append(
                EventHandler(
                    name=spec,
                    fn=self.wrapper_factory(fn),
                    condition=AlwaysTrue(),
                )
            )
            return fn

        return wrap

    def received(self, hook: Union[type, str], condition=None):
        def wrap(fn):
            if isinstance(hook, str):
                h = hook
            else:
                h = hook.__name__
            log.info("hook: '%s' %s", h, fn)
            self.event_handlers.append(
                EventHandler(
                    name=h,
                    fn=self.wrapper_factory(fn),
                    condition=condition or AlwaysTrue(),
                )
            )
            return fn

        return wrap

    @property
    def hooks(self) -> All:
        return self.entity_hooks

    @property
    def crons(self) -> List[CronKey]:
        return [h.key() for h in self.cron_handlers]

    def evaluators(self, evaluators: List[grammars.CommandEvaluator]):
        self.evaluator_override = grammars.PrioritizedEvaluator(evaluators)

    def behaviors(self, behaviors: List[LibraryBehavior]):
        for b in behaviors:
            b.create(self)

    def conditions(self):
        return bind_conditions(self.entity_key)

    async def evaluate(
        self,
        command: str,
        world: Optional[World] = None,
        person: Optional[Entity] = None,
        **kwargs,
    ) -> Optional[Action]:
        assert person

        entity = await context.get().try_materialize_key(self.entity_key)
        assert entity

        log.debug("%s evaluate %s", self, entity)

        for registered in [r for r in self.prose_handlers if r.condition.applies()]:

            def transformer_factory(**kwargs):
                assert world and person and entity
                return SimplifiedTransformer(
                    registered=registered,
                    world=world,
                    person=person,
                    entity=entity,
                )

            log.debug("%s evaluate '%s'", self, command)
            log.debug("%s prose=%s", self, registered.prose)

            evaluator = grammars.GrammarEvaluator(
                grammars.DYNAMIC, registered.prose, transformer_factory
            )

            action = await evaluator.evaluate(command)
            if action:
                return action

        if self.evaluator_override is not None:
            action = await self.evaluator_override.evaluate(
                command, world=world, person=person, **kwargs
            )
            if action:
                return action
            return Unknown()

        return None

    @functools.singledispatchmethod
    async def _notify(self, ev: Event, **kwargs):
        entity = await context.get().try_materialize_key(self.entity_key)
        assert entity

        for handler in self.event_handlers:
            if ev.name == handler.name:
                await handler.fn(this=entity, ev=ev, **kwargs)

    @_notify.register
    async def _notify_dict(self, ev: dict, **kwargs):
        decoded = serializing.deserialize_non_entity(
            ev, classes=list(self._get_declared_classes())
        )
        if not decoded or isinstance(decoded, dict):
            log.error(
                "deserialize-failed: %s declared=%s", ev, self._get_declared_classes()
            )
            raise DeserializationFailedException()
        log.debug("notify: %s declared=%s", decoded, self._get_declared_classes())
        return await self._notify(decoded, **kwargs)

    async def notify(self, ev: Event, **kwargs):
        try:
            await self._notify(ev, **kwargs)
        except:
            errors_log.exception("notify:exception", exc_info=True)
            raise

    def _get_declared_classes(self):
        return [
            value for value in self.declarations.values() if isinstance(value, type)
        ]


class DeserializationFailedException(Exception):
    pass


class DynamicParameterException(Exception):
    pass


@dataclasses.dataclass
class CustomizeCallArguments(ArgumentTransformer):
    extra: Dict[str, Any] = dataclasses.field(default_factory=dict)

    @functools.singledispatchmethod
    def transform_arg(self, arg: Any):
        return arg

    @transform_arg.register
    def transform_post_service(self, arg: inbox.PostService):
        return DynamicPostService(arg)

    @transform_arg.register
    def transform_callable(self, arg: abc.Callable):
        return arg()

    def transform(self, fn: Callable, args: List[Any], kwargs: Dict[str, Any]):
        lookup: ChainMap = ChainMap(kwargs, self.extra)

        def _get_arg(name: str):
            if name in lookup:
                return self.transform_arg(lookup[name])
            if args:
                return args.pop(0)
            raise DynamicParameterException("'%s' calling '%s'" % (name, fn))

        signature = inspect.signature(fn)
        return [_get_arg(p) for p in signature.parameters]


def flatten(l):
    return [item for sl in l for item in sl]
