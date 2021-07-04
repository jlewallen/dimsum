from typing import Any, List, Type, Dict, Optional

import logging
import dataclasses
import copy

import model.properties as properties
import model.scopes as scopes

import grammars
import transformers

from model.entity import *
from model.world import *
from model.events import *
from model.things import *
from model.game import *
from model.reply import *
from model.finders import *

from plugins.actions import *

from context import *

log = logging.getLogger("dimsum")


@dataclasses.dataclass
class EntityCreated(StandardEvent):
    entity: Entity

    def render_string(self) -> Dict[str, str]:
        return {"text": f"{self.living.props.name} created '{self.entity.props.name}'"}


def default_heard_for(area: Optional[entity.Entity] = None) -> List[entity.Entity]:
    if area:
        with area.make_and_discard(occupyable.Occupyable) as here:
            return here.occupied
    return []


class Create(PersonAction):
    def __init__(
        self,
        klass: Type[EntityClass],
        name: Optional[str] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert klass
        assert name
        self.klass = klass
        self.name = name

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        log.info("creating '%s' klass=%s", self.name, self.klass)
        created = scopes.create_klass(
            self.klass,
            creator=person,
            props=properties.Common(name=self.name, desc=self.name),
        )
        with person.make(carryable.Containing) as contain:
            after_hold = contain.hold(created)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_hold)
            return EntityCreated(
                area=area,
                living=person,
                entity=after_hold,
                heard=default_heard_for(area),
            )


@dataclasses.dataclass
class ItemsMade(StandardEvent):
    items: List[entity.Entity]


class Make(PersonAction):
    def __init__(
        self,
        template: Optional[things.ItemFactory] = None,
        item: Optional[things.ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template = template
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs,
    ):
        item: Optional[entity.Entity] = None
        if self.item:
            item = await world.apply_item_finder(person, self.item)

        if self.template:
            item = self.template.create_item(
                person=person, creator=person, owner=person
            )

        if not item:
            return Failure("make what now?")

        with person.make(carryable.Containing) as contain:
            after_hold = contain.hold(item)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_hold)

        area = world.find_person_area(person)
        await ctx.publish(
            ItemsMade(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=[after_hold],
            )
        )
        return Success("you're now holding %s" % (after_hold,))


@dataclasses.dataclass
class ItemsObliterated(StandardEvent):
    items: List[entity.Entity]


class Obliterate(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs,
    ):
        area = world.find_person_area(person)
        items = None
        with person.make(carryable.Containing) as pockets:
            items = pockets.drop_all()
        if len(items) == 0:
            return Failure("you're not holding anything")

        for item in items:
            ctx.unregister(item)

        await ctx.publish(
            ItemsObliterated(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=items,
            )
        )

        await ctx.extend(obliterate=items).hook("obliterate:after")

        return Success("you obliterated %s" % (p.join(list(map(str, items))),))


class CallThis(PersonAction):
    def __init__(
        self,
        name: Optional[str] = None,
        item: Optional[things.ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert name
        self.name = name

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs,
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("you don't have anything")

        item.try_modify()

        # Copy all of the base props from the item. Exclude stamps.
        # TODO This looks like it's been broken.
        template = item
        recipe = scopes.item(
            creator=person,
            owner=person,
            props=item.props.clone(),
            behaviors=item.make(behavior.Behaviors).behaviors,
            kind=item.make(carryable.Carryable).kind,
        )
        with recipe.make(Recipe) as makes:
            # TODO Clone
            updated = copy.deepcopy(template.__dict__)
            updated.update(
                key=None, identity=None, version=None, props=template.props.clone()
            )
            cloned = scopes.item(**updated)
            makes.template = cloned
            log.info("registering template: %s", cloned.key)
            ctx.register(cloned)

        ctx.register(recipe)
        with person.make(mechanics.Memory) as brain:
            brain.memorize("r:" + self.name, recipe)
        person.touch()

        return Success(
            "cool, you'll be able to make another %s easier now" % (self.name,)
        )


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:                  create | obliterate | make | call

        obliterate:             "obliterate"
        make:                   "make" makeable                         -> make
                              | "make" number makeable                  -> make_quantified

        create:                 "create" create_entity_kind TEXT
        create_entity_kind:     "thing" -> create_entity_kind_thing
                              | "area" -> create_entity_kind_area
                              | "exit" -> create_entity_kind_exit
                              | "living" -> create_entity_kind_living

        call:                    "call" this NAME

"""


class Transformer(transformers.Base):
    def create(self, args):
        log.info("create: %s", args[0])
        return Create(args[0], str(args[1]))

    def create_entity_kind_thing(self, args):
        return scopes.ItemClass

    def create_entity_kind_area(self, args):
        return scopes.AreaClass

    def create_entity_kind_exit(self, args):
        return scopes.ExitClass

    def create_entity_kind_living(self, args):
        return scopes.LivingClass

    def make(self, args):
        return Make(template=args[0])

    def make_quantified(self, args):
        quantity = args[0]
        return Make(template=things.MaybeQuantifiedItem(args[1], quantity))

    def call(self, args):
        return CallThis(item=args[0], name=str(args[1]))

    def obliterate(self, args):
        return Obliterate()
