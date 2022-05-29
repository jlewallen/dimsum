import copy
import dataclasses
from typing import Dict, List, Optional, Type, Any

import grammars, transformers, tools, logging
from loggers import get_logger
from model import *
from finders import *
import scopes
import scopes.behavior as behavior
from plugins.actions import PersonAction

log = get_logger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class EntityCreated(StandardEvent):
    entity: Entity

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} created {infl.join([self.entity.props.described])}"
            ]
        }


@event
@dataclasses.dataclass(frozen=True)
class ItemsMade(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} created {self.render_entities(self.items)}"
            ]
        }


@event
@dataclasses.dataclass(frozen=True)
class ItemsObliterated(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} obliterated {self.render_entities(self.items)}"
            ]
        }


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
            props=Common(name=self.name, desc=self.name),
        )
        with person.make(carryable.Containing) as contain:
            final_entity = created
            if self.klass in [scopes.ItemClass, scopes.LivingClass, scopes.ExitClass]:
                final_entity = contain.hold(created)
                # We do this after because we may consolidate this Item and
                # this keeps us from having to unregister the item.

            ctx.register(final_entity)
            final_entity.touch()

            return EntityCreated(
                source=person,
                area=area,
                entity=final_entity,
                heard=tools.default_heard_for(area, excepted=[person]),
            )


class Make(PersonAction):
    def __init__(
        self,
        template: Optional[ItemFactory] = None,
        item: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.template = template
        self.item = item

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        item: Optional[Entity] = None
        if self.item:
            item = await ctx.apply_item_finder(person, self.item)

        if self.template:
            item = self.template.create_item(
                person=person, creator=person, owner=person
            )

        if not item:
            return Failure("Make what?")

        with person.make(carryable.Containing) as contain:
            after_hold = contain.hold(item)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_hold)

        area = await find_entity_area(person)

        im = ItemsMade(
            source=person,
            area=area,
            heard=tools.default_heard_for(area=area, excepted=[person]),
            items=[after_hold],
        )

        await ctx.publish(im)

        return im


class DuplicateItem(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, fork: bool = False, **kwargs):
        assert item
        self.item = item
        self.fork = fork
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        area = await find_entity_area(person)
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Duplicate what?")

        duplicate = tools.duplicate(item, fork=self.fork)
        with person.make(carryable.Containing) as hands:
            after_hold = hands.hold(duplicate)
            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_hold)

        area = await find_entity_area(person)

        im = ItemsMade(
            source=person,
            area=area,
            heard=tools.default_heard_for(area=area, excepted=[person]),
            items=[after_hold],
        )

        await ctx.publish(im)


class ObliterateItem(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        assert item
        self.item = item
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        area = await find_entity_area(person)
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Obliterate what?")

        with person.make(carryable.Containing) as pockets:
            for item in [item]:
                pockets.drop(item)
                ctx.unregister(item)

        io = ItemsObliterated(
            source=person,
            area=area,
            heard=tools.default_heard_for(area=area, excepted=[person]),
            items=[item],
        )

        await ctx.publish(io)

        return io


class CallThis(PersonAction):
    def __init__(
        self,
        name: Optional[str] = None,
        item: Optional[ItemFinder] = None,
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
        area: Entity,
        person: Entity,
        ctx: Ctx,
        **kwargs,
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("You don't have anything.")

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
            "Cool, you'll be able to make another %s easier now." % (self.name,)
        )


@grammars.grammar()
class Grammar(grammars.Grammar):
    @property
    def order(self) -> int:
        return grammars.HIGHEST

    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:                  create | obliterate_item | duplicate_item | make | call

        obliterate_item:        "obliterate" noun                       -> obliterate_item

        duplicate_item:         "duplicate" noun                        -> duplicate_item
                              | "duplicate" "~fork" noun                -> duplicate_fork_item

        make:                   "make" makeable                         -> make
                              | "make" number makeable                  -> make_quantified

        create:                 "create" create_entity_kind string
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
        return Make(template=MaybeQuantifiedItem(args[1], quantity))

    def call(self, args):
        return CallThis(item=args[0], name=str(args[1]))

    def obliterate_item(self, args):
        return ObliterateItem(args[0])

    def duplicate_item(self, args):
        return DuplicateItem(args[0], fork=False)

    def duplicate_fork_item(self, args):
        return DuplicateItem(args[0], fork=True)
