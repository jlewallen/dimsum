import logging
import dataclasses
from typing import Type, Optional, List

from context import Ctx
from model.game import *
from model.reply import *
from model.world import *
from model.events import *
from finders import *
from tools import *
from plugins.actions import PersonAction
from plugins.editing import ModifyActivity
import model.hooks as hooks
import scopes.carryable as carryable
import grammars
import transformers

log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsDropped(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class ItemsHeld(StandardEvent):
    items: List[entity.Entity]


@hooks.all.hold.target
def can_hold(person: entity.Entity, entity: entity.Entity) -> bool:
    return True


class Drop(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        quantity: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.quantity = quantity if quantity else None
        self.item = item if item else None

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = None

        if self.item:
            item = await world.apply_item_finder(person, self.item)
            if not item:
                return Failure("drop what?")

        area = world.find_person_area(person)

        with person.make(carryable.Containing) as contain:
            dropped, failure = contain.drop_here(
                area,
                item,
                quantity=self.quantity,
                creator=person,
                owner=person,
                ctx=ctx,
            )
            if dropped:
                area = world.find_person_area(person)
                await ctx.publish(
                    ItemsDropped(
                        living=person,
                        area=area,
                        heard=default_heard_for(area=area),
                        items=dropped,
                    )
                )
                return Success("you dropped %s" % (p.join(dropped),))

            return Failure(failure)


class Hold(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        quantity: Optional[int] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.quantity = quantity

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("sorry, hold what?")

        if not can_hold(person, item):
            return Failure("sorry, you can't hold that")

        with person.make(carryable.Containing) as pockets:
            # This should happen after? What if there's more on the ground?
            if pockets.is_holding(item):
                return Failure("you're already holding that")

            area = world.find_person_area(person)
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
                        living=person,
                        area=area,
                        heard=default_heard_for(area=area),
                        items=[after_hold],
                    )
                )
                return Success("you picked up %s" % (after_hold,))


class Open(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("open what?")

        with item.make(carryable.Containing) as contain:
            if not contain.can_hold():
                return Failure("you can't open that")

            if not contain.open():
                return Failure("huh, won't open")

        return Success("opened")


class Close(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("close what?")

        with item.make(carryable.Containing) as contain:
            if not contain.can_hold():
                return Failure("you can't open that")

            if not contain.close():
                return Failure("it's got other plans")

        return Success("closed")


class Lock(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        key: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        area = world.find_person_area(person)

        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("what?")

        maybe_key = await world.apply_item_finder(person, self.key, exclude=[item])

        with person.make(carryable.Containing) as hands:
            with item.make(carryable.Containing) as locking:
                locked_with = locking.lock(
                    key=maybe_key, creator=person, owner=person, **kwargs
                )
                if not locked_with:
                    return Failure("can't seem to lock that")

                assert locking.is_locked()
                hands.hold(locked_with)
                ctx.register(locked_with)

        return Success("done")


class Unlock(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        key: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert key
        self.key = key

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        area = world.find_person_area(person)

        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("unlock what?")

        log.info("finding key %s", self.key)
        maybe_key = await world.apply_item_finder(person, self.key, exclude=[item])
        log.info("maybe key: %s", maybe_key)

        with item.make(carryable.Containing) as unlocking:
            if unlocking.unlock(key=maybe_key, **kwargs):
                return Success("done")

        return Failure("nope")


class PutInside(PersonAction):
    def __init__(
        self,
        container: Optional[ItemFinder] = None,
        item: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        area = world.find_person_area(person)

        container = await world.apply_item_finder(person, self.container)
        if not container:
            return Failure("what?")

        with container.make(carryable.Containing) as containing:
            if not containing.can_hold():
                return Failure("inside... that?")

            item = await world.apply_item_finder(person, self.item)
            if not item:
                return Failure("what?")

            if containing.place_inside(item):
                with person.make(carryable.Containing) as pockets:
                    pockets.drop(item)
                return Success("inside, done")

        return Failure("you can't do that")


class TakeOut(PersonAction):
    def __init__(
        self,
        container: Optional[ItemFinder] = None,
        item: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert container
        self.container = container
        assert item
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        area = world.find_person_area(person)

        container = await world.apply_item_finder(person, self.container)
        if not container:
            return Failure("what?")

        with container.make(carryable.Containing) as containing:
            if not containing.can_hold():
                return Failure("outside of... that?")

            item = await world.apply_item_finder(person, self.item)
            if not item:
                return Failure("what?")

            if not can_hold(person, item):
                return Failure("sorry, you can't hold that")

            if containing.take_out(item):
                with person.make(carryable.Containing) as pockets:
                    pockets.hold(item)
                return Success("done, you're holding that now")

        return Failure("doesn't seem like you can")


PourVerb = "pour"


class Pour(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        source: Optional[ItemFinder] = None,
        destination: Optional[ItemFinder] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.item = item
        assert source
        self.source = source
        assert destination
        self.destination = destination

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        source = await world.apply_item_finder(person, self.source)
        if not source:
            return Failure("from what?")

        destination = await world.apply_item_finder(
            person, self.destination, exclude=[source]
        )
        if not destination:
            return Failure("into what?")

        with source.make(carryable.Containing) as produces:
            if not PourVerb in produces.produces:
                return Failure("you can't pour from that")

            produced = produces.produce_into(
                PourVerb, destination, person=person, creator=person, owner=person
            )
            if produced:
                return Success("done")

        return Failure("oh no")


class PourProducer(carryable.Producer):
    def __init__(self, template: Optional[MaybeItemOrRecipe] = None, **kwargs):
        super().__init__()
        assert template
        self.template: MaybeItemOrRecipe = template

    def produce_item(self, **kwargs) -> entity.Entity:
        item = self.template.create_item(verb=PourVerb, **kwargs)
        with item.make(mechanics.Interactable) as inaction:
            inaction.link_activity(properties.Drank)
        with item.make(carryable.Carryable) as carry:
            carry.loose = True
        return item


class ModifyPours(PersonAction):
    def __init__(
        self,
        item: Optional[ItemFinder] = None,
        produces: Optional[MaybeItemOrRecipe] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert produces
        self.produces = produces

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("nothing to modify")

        log.info("modifying %s to produce %s", item, self.produces)

        item.try_modify()

        with item.make(carryable.Containing) as produces:
            produces.produces_when(PourVerb, PourProducer(template=self.produces))

        item.touch()

        return Success("done")


class ModifyCapacity(PersonAction):
    def __init__(self, item: Optional[ItemFinder] = None, capacity=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert capacity
        self.capacity = capacity

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        item = await world.apply_item_finder(person, self.item)
        if not item:
            return Failure("nothing to modify")
        item.try_modify()
        with item.make(carryable.Containing) as contain:
            if contain.adjust_capacity(self.capacity):
                return Success("done")
        return Failure("no way")


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
        return ModifyActivity(
            item=AnyHeldItem(), activity=properties.Opened, value=True
        )


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
