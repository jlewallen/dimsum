import dataclasses
import functools
from typing import Type, Optional, List, Dict, Any

import grammars
import transformers
from loggers import get_logger
from model import *
from finders import *
from tools import *
from plugins.actions import PersonAction
from plugins.editing import ModifyActivity
import scopes.carryable as carryable

log = get_logger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsDropped(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} dropped {self.render_entities(self.items)}"
            ]
        }


@event
@dataclasses.dataclass(frozen=True)
class ItemsHeld(StandardEvent):
    items: List[Entity]

    def render_tree(self) -> Dict[str, Any]:
        return {
            "lines": [
                f"{self.source.props.described} held {self.render_entities(self.items)}"
            ]
        }


@hooks.all.hold.target
def can_hold(person: Entity, entity: Entity) -> bool:
    return True


@hooks.all.drop.target
def can_drop(person: Entity, entity: Entity) -> bool:
    return True


@hooks.all.open.target
def can_open(person: Entity, entity: Entity) -> bool:
    return True


@hooks.all.close.target
def can_close(person: Entity, entity: Entity) -> bool:
    return True


class Drop(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        quantity: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.quantity = quantity if quantity else None
        self.item = item if item else None

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = None

        if self.item:
            item = await ctx.apply_item_finder(person, self.item)
            if not item:
                return Failure("Drop what?")

            if not can_drop(person, item):
                return Failure("Drop what?")

        area = await find_entity_area(person)

        with person.make(carryable.Containing) as contain:
            dropped, failure = contain.drop_here(
                area,
                item,
                quantity=self.quantity,
                creator=person,
                owner=person,
                ctx=ctx,
                condition=functools.partial(can_drop, person),
            )
            if dropped:
                area = await find_entity_area(person)
                await ctx.publish(
                    ItemsDropped(
                        source=person,
                        area=area,
                        heard=default_heard_for(area=area, excepted=[person]),
                        items=dropped,
                    )
                )
                return Success(
                    "You dropped %s" % (infl.join([e.describe() for e in dropped]),)
                )

            return Failure(failure)


class Hold(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        quantity: Optional[int] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.quantity = quantity

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Sorry, hold what?")

        if not can_hold(person, item):
            return Failure("Sorry, you can't hold that.")

        with person.make(carryable.Containing) as pockets:
            # This should happen after? What if there's more on the ground?
            if pockets.is_holding(item):
                return Failure("You're already holding that.")

            area = await find_entity_area(person)
            with area.make(carryable.Containing) as ground:
                if self.quantity:
                    with item.make(carryable.Carryable) as hands:
                        removed = hands.separate(
                            self.quantity, creator=person, owner=person, ctx=ctx
                        )
                        if hands.quantity == 0:
                            ctx.unregister(item)
                            ground.drop(item)
                    item = removed[0]
                else:
                    ground.unhold(item)

                after_hold = pockets.hold(item)
                if after_hold != item and item:
                    ctx.unregister(item)
                await ctx.publish(
                    ItemsHeld(
                        source=person,
                        area=area,
                        heard=default_heard_for(area=area, excepted=[person]),
                        items=[after_hold],
                    )
                )
                return Success(
                    "You picked up %s"
                    % (infl.join([e.describe() for e in [after_hold]]),)
                )


class Open(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Open what?")

        with item.make(carryable.Containing) as contain:
            if not contain.can_hold():
                return Failure("You can't open that.")

            if not can_open(person, item):
                return Failure("Huh, won't open.")

            if not contain.open():
                return Failure("Huh, won't open.")

        return Success("It opened.")


class Close(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Close what?")

        with item.make(carryable.Containing) as contain:
            if not contain.can_hold():
                return Failure("You can't open that.")

            if not can_close(person, item):
                return Failure("Huh, won't close.")

            if not contain.close():
                return Failure("It's got other plans.")

        return Success("Closed.")


class Lock(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        key: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        area = await find_entity_area(person)

        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("What?")

        maybe_key = await ctx.apply_item_finder(person, self.key, exclude=[item])

        with person.make(carryable.Containing) as hands:
            with item.make(carryable.Containing) as locking:
                locked_with = locking.lock(
                    key=maybe_key, creator=person, owner=person, **kwargs
                )
                if not locked_with:
                    return Failure("You can't seem to lock that.")

                assert locking.is_locked()
                hands.hold(locked_with)
                ctx.register(locked_with)

        return Success("Done, locked.")


class Unlock(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        key: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        area = await find_entity_area(person)

        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Unlock what?")

        log.info("finding key %s", self.key)
        maybe_key = await ctx.apply_item_finder(person, self.key, exclude=[item])
        log.info("maybe key: %s", maybe_key)

        with item.make(carryable.Containing) as unlocking:
            if unlocking.unlock(key=maybe_key, **kwargs):
                return Success("Done, unlocked.")

        return Failure("Nope, can't do.")


class PutInside(PersonAction):
    def __init__(
        self,
        container: Optional[ItemFinder] = None,
        item: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        area = await find_entity_area(person)

        container = await ctx.apply_item_finder(person, self.container)
        if not container:
            return Failure("What?")

        with container.make(carryable.Containing) as containing:
            if not containing.can_hold():
                return Failure("Inside... that?")

            item = await ctx.apply_item_finder(person, self.item)
            if not item:
                return Failure("What?")

            if containing.place_inside(item):
                with person.make(carryable.Containing) as pockets:
                    pockets.drop(item)
                return Success("Inside, done")

        return Failure("You can't do that.")


class TakeOut(PersonAction):
    def __init__(
        self,
        container: Optional[ItemFinder] = None,
        item: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        area = await find_entity_area(person)

        container = await ctx.apply_item_finder(person, self.container)
        if not container:
            return Failure("What?")

        with container.make(carryable.Containing) as containing:
            if not containing.can_hold():
                return Failure("Outside of... that?")

            item = await ctx.apply_item_finder(person, self.item)
            if not item:
                return Failure("What?")

            if not can_hold(person, item):
                return Failure("Sorry, you can't hold that.")

            if containing.take_out(item):
                with person.make(carryable.Containing) as pockets:
                    pockets.hold(item)
                return Success("Done, you're holding that now.")

        return Failure("It doesn't seem like you can.")


PourVerb = "pour"


class Pour(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        source: Optional[ItemFinder] = None,
        destination: Optional[ItemFinder] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.item = item
        assert source
        self.source = source
        assert destination
        self.destination = destination

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        source = await ctx.apply_item_finder(person, self.source)
        if not source:
            return Failure("From what?")

        destination = await ctx.apply_item_finder(
            person, self.destination, exclude=[source]
        )
        if not destination:
            return Failure("Into what?")

        with source.make(carryable.Containing) as produces:
            if not PourVerb in produces.produces:
                return Failure("You can't pour from that.")

            produced = produces.produce_into(
                PourVerb, destination, person=person, creator=person, owner=person
            )
            if produced:
                return Success("Done")

        return Failure("Oh no.")


class PourProducer(carryable.Producer):
    def __init__(self, template: Optional[MaybeItemOrRecipe] = None, **kwargs):
        super().__init__()
        assert template
        self.template: MaybeItemOrRecipe = template

    def produce_item(self, **kwargs) -> Entity:
        item = self.template.create_item(verb=PourVerb, **kwargs)
        with item.make(mechanics.Interactable) as inaction:
            inaction.link_activity(Drank)
        with item.make(carryable.Carryable) as carry:
            carry.loose = True
        return item


class ModifyPours(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        produces: Optional[MaybeItemOrRecipe] = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert produces
        self.produces = produces

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")

        log.info("modifying %s to produce %s", item, self.produces)

        item.try_modify()

        with item.make(carryable.Containing) as produces:
            produces.produces_when(PourVerb, PourProducer(template=self.produces))

        item.touch()

        return Success("Done.")


class ModifyCapacity(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, capacity=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert capacity
        self.capacity = capacity

    async def perform(
        self, world: World, area: Entity, person: Entity, ctx: Ctx, **kwargs
    ):
        item = await ctx.apply_item_finder(person, self.item)
        if not item:
            return Failure("Modify what?")
        item.try_modify()
        with item.make(carryable.Containing) as contain:
            if contain.adjust_capacity(self.capacity):
                return Success("Done.")

        return Failure("No way.")


class Transformer(transformers.Base):
    def drop(self, args):
        return Drop()

    def drop_quantity(self, args):
        return Drop(quantity=args[0], item=args[1])

    def drop_item(self, args):
        return Drop(item=args[0])

    def put_inside(self, args):
        return PutInside(container=args[1], item=args[0])

    def take_out(self, args):
        return TakeOut(container=args[1], item=args[0])

    def open_hands(self, args):
        return Open(item=args[0])

    def close_hands(self, args):
        return Close(item=args[0])

    def lock_new(self, args):
        return Lock(item=args[0], key=FindNone())

    def lock_with(self, args):
        return Lock(item=args[0], key=args[1])

    def unlock(self, args):
        return Unlock(item=args[0], key=AnyHeldItem())

    def unlock_with(self, args):
        return Unlock(item=args[0], key=args[1])

    def hold(self, args):
        return Hold(item=args[0])

    def hold_quantity(self, args):
        return Hold(item=args[1], quantity=args[0])

    def pour(self, args):
        return Pour(item=args[0], source=args[1], destination=FindHeldContainer())

    def pour_from(self, args):
        return Pour(source=args[0], destination=FindHeldContainer())

    def when_pours(self, args):
        return ModifyPours(item=AnyHeldItem(), produces=args[0])

    def modify_capacity(self, args):
        return ModifyCapacity(item=AnyHeldItem(), capacity=args[0])

    def when_opened(self, args):
        return ModifyActivity(item=AnyHeldItem(), activity=Opened, value=True)


@grammars.grammar()
class CarryingGrammar(grammars.Grammar):
    @property
    def transformer_factory(self) -> Type[transformers.Base]:
        return Transformer

    @property
    def lark(self) -> str:
        return """
        start:             verbs

        verbs:             drop | hold | put | take | lock | unlock | give | open | close | pour | modify

        give:              "give"

        take:              "take"                                  -> take
                         | "take" "bite" "of" noun                 -> take_bite
                         | "take" "sip" "of" noun                  -> take_sip
                         | "take" contained "out" "of" held        -> take_out

        put:               "put" held ("in") held                  -> put_inside

        open:              "open" held                             -> open_hands
        close:             "close" held                            -> close_hands

        lock:              "lock" held "with" held                 -> lock_with
                         | "lock" held                             -> lock_new

        unlock:            "unlock" held "with" held               -> unlock_with
                         | "unlock" held                           -> unlock

        hold:              "hold" unheld                           -> hold
                         | "hold" number unheld                    -> hold_quantity

        drop:              "drop"                                  -> drop
                         | "drop" number held                      -> drop_quantity
                         | "drop" held                             -> drop_item

        pour:              "pour" "from" noun                      -> pour_from
                         | "pour" noun ("from"|"on"|"over") noun   -> pour

        modify:            "modify" "capacity" number              -> modify_capacity
                         | "modify" "pours" makeable_noun          -> when_pours
                         | "modify" "when" "opened"                -> when_opened
                         | "modify" "when" "closed"                -> when_closed
"""
