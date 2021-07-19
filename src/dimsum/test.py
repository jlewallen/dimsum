import base64
import io
import json
import logging
import re
import functools
from typing import Any, Callable, Dict, Optional, Union

import domains
import serializing
import everything  # noqa
from model import *
from plugins.actions import Join
from scopes.ownership import set_owner
import scopes as scopes
import scopes.behavior as behavior
import scopes.carryable as carryable
import scopes.movement as movement
import scopes.users as users

log = logging.getLogger("dimsum.tests")


def create_empty_world():
    return World()


class TestWorld:
    def __init__(self, handlers=None):
        self.domain = domains.Domain(handlers=handlers)
        self.carla_key: Optional[str] = None
        self.jacob_key: Optional[str] = None
        self.tomi_key: Optional[str] = None

    async def to_json(self):
        capture = io.StringIO()
        await self.domain.store.write(capture)  # type:ignore
        return pretty_json(capture.getvalue())

    async def add_carla(self):
        if self.carla_key:
            return self.carla_key

        log.info("adding carla")
        with self.domain.session() as session:
            world = await session.prepare()

            carla = scopes.alive(
                creator=world,
                props=Common("Carla", desc="Chief Salad Officer."),
            )
            set_owner(carla, carla)

            await session.perform(Join(), carla)
            await session.save()
            self.carla_key = carla.key
            return carla

    async def add_tomi(self):
        if self.tomi_key:
            return self.tomi_key

        log.info("adding tomi")
        with self.domain.session() as session:
            world = await session.prepare()

            tomi = scopes.alive(
                creator=world,
                props=Common("Tomi", desc="Chief Crying Officer."),
            )
            set_owner(tomi, tomi)

            await session.perform(Join(), tomi)
            await session.save()
            self.tomi_key = tomi.key
            return tomi

    async def add_jacob(self):
        if self.jacob_key:
            return self.jacob_key

        log.info("adding jacob")
        with self.domain.session() as session:
            world = await session.prepare()

            jacob = scopes.alive(
                creator=world,
                props=Common("Jacob", desc="Curly haired bastard."),
            )
            set_owner(jacob, jacob)

            await session.perform(Join(), jacob)
            await session.save()
            self.jacob_key = jacob.key
            return jacob

    async def initialize(self, world=None, area=None, **kwargs):
        log.info("initialize")
        with self.domain.session() as session:
            if world:
                self.world = world
            else:
                world = await session.prepare()

            if not area:
                area = scopes.area(creator=world, props=Common("Living room"))

            await session.add_area(area)
            await session.save()

        await self.add_jacob()

    async def add_item_to_welcome_area(self, item, session=None):
        assert session
        session.register(item)

        wa_key = get_well_known_key(session.world, WelcomeAreaKey)
        assert wa_key
        welcome_area = await session.materialize(key=wa_key)
        with welcome_area.make(carryable.Containing) as ground:
            ground.add_item(item)
        return item

    def dumps(self, item) -> Optional[str]:
        return serializing.serialize(item, indent=4)

    async def execute(self, command: str, person=None, **kwargs):
        with self.domain.session() as session:
            world = await session.prepare()

            assert self.jacob_key
            person = await session.materialize(
                key=self.jacob_key if person is None else person
            )

            log.info("=" * 100)

            response = await session.execute(person, command)

            log.info("response: %s" % (response,))
            if isinstance(response, Failure):
                log.info("unsaved!")
            else:
                await session.save()

            if isinstance(response, Renderable):
                log.info("response: %s", response.render_tree())

            return response

    async def success(self, *commands: str, **kwargs):
        for command in commands:
            r = await self.execute(command, **kwargs)
            if not isinstance(r, Failure):
                return r
            log.error("reply: %s", r)
            assert not isinstance(r, Failure)

    async def failure(self, command: str, **kwargs):
        r = await self.execute(command, **kwargs)
        assert isinstance(r, Failure)
        return r

    async def add_behaviored_thing(self, tw: "TestWorld", name: str, python: str):
        with tw.domain.session() as session:
            world = await session.prepare()

            item = await tw.add_item_to_welcome_area(
                scopes.item(creator=world, props=Common(name)),
                session=session,
            )

            with item.make(behavior.Behaviors) as behave:
                behave.add_behavior(world, python=python)

            await session.save()

            return item  # TODO return key


async def make_simple_domain(
    password: Optional[str] = None, store=None
) -> domains.Domain:
    domain = domains.Domain(store=store)
    with domain.session() as session:
        world = await session.prepare()

        welcome = scopes.area(
            key="welcome",
            props=Common(name="welcome"),
            creator=world,
        )
        jacob = scopes.alive(props=Common(name="Jacob"), creator=world)
        jacob_key = jacob.key

        if password:
            with jacob.make(users.Auth) as auth:
                auth.change(password)

        await session.add_area(welcome)
        session.register(jacob)
        await users.register_username(world, "jlewallen", jacob_key)
        await session.perform(Join(), jacob)
        await session.save()

    return domain


def expand_json(obj: Dict[str, Any]) -> Dict[str, Any]:
    def expand(value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except:
                return value
        if isinstance(value, dict):
            return {key: expand(value) for key, value in value.items()}
        if isinstance(value, list):
            return [expand(v) for v in value]
        return value

    return expand(obj)


def make_deterministic(obj: Dict[str, Any]) -> Dict[str, Any]:
    # "key": "XCCf383KvgvJ7erVa2gxd8",
    # "public": "qigxTieZXLSVokwOYHqlXO1QUKrUaaiSEFR1nREDcWs=",
    # "value": 1626034498.0281904

    key_re = re.compile("[A-Za-z0-9]{22}")

    counter = 0
    cache: Dict[str, str] = {}

    # @functools.cache
    def sequential(key: str) -> str:
        nonlocal counter
        nonlocal cache
        if key in cache:
            return cache[key]
        counter += 1
        k = "D#{0}".format(counter)
        cache[key] = k
        return k

    def fix_key(key: str) -> str:
        if key_re.match(key):
            return sequential(key)
        return key

    def fix(value, key=None, keys=None):
        if isinstance(value, str):
            if keys:
                if keys[-1] == "key" or keys[-1] == "welcomeArea":
                    return "<deterministic>"
                if keys[-1] == "public" or keys[-1] == "private":
                    return "<deterministic>"
                if keys[-1] == "info" and keys[-2] == "context":
                    return "<deterministic>"
                if keys[-1] == "domain" and keys[-2] == "context":
                    return "<deterministic>"
            return value
        if isinstance(value, float):
            if keys:
                if keys[-2] == "created":
                    return "0"
                if keys[-2] == "touched":
                    return "0"
            return value
        if isinstance(value, dict):
            return {
                fix_key(key): fix(value, key=key, keys=(keys or []) + [key])
                for key, value in value.items()
            }
        if isinstance(value, list):
            return [fix(v) for v in value]
        return value

    return fix(obj)


def pretty_json(obj: Union[Dict[str, Any], Optional[str]], deterministic=False) -> str:
    if obj is None:
        return json.dumps(None)

    if isinstance(obj, str):
        return pretty_json(json.loads(obj))

    expanded = expand_json(obj)
    if deterministic:
        expanded = make_deterministic(expanded)

    return json.dumps(expanded, indent=4)


class Deterministic:
    def __init__(self):
        super().__init__()
        self.i = 0
        self.previous_keys: Optional[Callable] = None
        self.previous_identities: Optional[Callable] = None

    def __enter__(self):
        self.previous_keys = set_entity_keys_provider(self.generate_key)
        self.previous_identities = set_entity_identities_provider(
            self.generate_identity
        )

    def __exit__(self, type, value, traceback):
        assert self.previous_identities
        set_entity_identities_provider(self.previous_identities)
        assert self.previous_keys
        set_entity_keys_provider(self.previous_keys)

    def generate_key(self) -> str:
        self.i += 1
        return str(self.i)

    def generate_identity(self, creator=None) -> Identity:
        self.i += 1
        return Identity(str(self.i), str(self.i), str(self.i))
