from typing import Any, List, Optional

import os
import base64
import logging
import dataclasses

import model.entity as entity
import model.finders as finders
import model.properties as properties
import model.scopes.users as users
import model.scopes.movement as movement
import model.scopes.health as health
import model.scopes.mechanics as mechanics
import model.scopes.carryable as carryable
import model.scopes.apparel as apparel

from context import Ctx

from model.reply import *
from model.game import *
from model.things import *
from model.events import *
from model.world import *
from model.tools import *

from plugins.actions import *

MemoryAreaKey = "m:area"
log = logging.getLogger("dimsum")


@event
@dataclasses.dataclass(frozen=True)
class ItemsAppeared(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class ItemsDropped(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class ItemsWorn(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class ItemsUnworn(StandardEvent):
    items: List[entity.Entity]


@event
@dataclasses.dataclass(frozen=True)
class PlayerJoined(StandardEvent):
    pass


@event
@dataclasses.dataclass(frozen=True)
class ItemsHeld(StandardEvent):
    items: List[entity.Entity]


class Auth(PersonAction):
    def __init__(self, password=None, **kwargs):
        super().__init__(**kwargs)
        self.password = password

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        with person.make(users.Auth) as auth:
            auth.change(self.password)
            log.info(auth.password)
        return Success("done, https://mud.espial.me")


class Home(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        return await Go(area=world.welcome_area()).perform(
            world=world, area=area, person=person, ctx=ctx, **kwargs
        )


class AddItemArea(PersonAction):
    def __init__(self, item=None, area=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.area = area

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        with self.area.make(carryable.Containing) as ground:
            after_add = ground.add_item(self.item)
            ctx.register(after_add)

            # We do this after because we may consolidate this Item and
            # this keeps us from having to unregister the item.
            ctx.register(after_add)

        await ctx.publish(
            ItemsAppeared(
                living=person,
                area=self.area,
                heard=default_heard_for(area=area),
                items=[self.item],
            )
        )
        return Success("%s appeared" % (p.join([self.item]),))


class Wear(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("wear what?")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_worn():
                return Failure("you can't wear that")

        with person.make(carryable.Containing) as contain:
            assert contain.is_holding(item)

            with person.make(apparel.Apparel) as wearing:
                if wearing.wear(item):
                    contain.drop(item)

        await ctx.publish(
            ItemsWorn(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=[item],
            )
        )
        return Success("you wore %s" % (item))


class Remove(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("remove what?")

        with person.make(apparel.Apparel) as wearing:
            if not wearing.is_wearing(item):
                return Failure("you aren't wearing that")

            assert wearing.is_wearing(item)

            if wearing.unwear(item):
                with person.make(carryable.Containing) as contain:
                    contain.hold(item)

        await ctx.publish(
            ItemsUnworn(
                living=person,
                area=area,
                heard=default_heard_for(area=area),
                items=[item],
            )
        )
        return Success("you removed %s" % (item))


class Eat(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("dunno where that is")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_eaten():
                return Failure("you can't eat that")

        area = world.find_person_area(person)
        with person.make(health.Health) as p:
            await p.consume(item, area=area, ctx=ctx)

        return Success("you ate %s" % (item))


class Drink(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("dunno where that is")

        with item.make(mechanics.Interactable) as inaction:
            if not inaction.when_drank():
                return Failure("you can't drink that")

        area = world.find_person_area(person)
        with person.make(health.Health) as p:
            await p.consume(item, area=area, ctx=ctx)

        return Success("you drank %s" % (item))


class Join(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        ctx.register(person)
        with world.welcome_area().make(occupyable.Occupyable) as entering:
            await ctx.publish(
                PlayerJoined(
                    living=person,
                    area=entering.ourselves,
                    heard=default_heard_for(area=area),
                )
            )
            await entering.entered(person)
        return Success("welcome!")


class LookInside(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("inside what?")

        with item.make(carryable.Containing) as contain:
            if not contain.is_open():
                return Failure("you can't do that")

            return EntitiesObservation(contain.holding)


class LookFor(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("i can't seem to find that")

        with person.make(mechanics.Visibility) as vis:
            vis.add_observation(item.identity)

        with person.make(carryable.Containing) as contain:
            return EntitiesObservation([item])


class LookMyself(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        return PersonalObservation(person)


class LookDown(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        with person.make(carryable.Containing) as contain:
            return EntitiesObservation(contain.holding)


class Look(PersonAction):
    def __init__(self, item=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        if self.item:
            return DetailedObservation(ObservedItem(self.item))

        assert area
        return AreaObservation(area, person)


class Drop(PersonAction):
    def __init__(
        self,
        item: Optional[things.ItemFinder] = None,
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
        item: Optional[things.ItemFinder] = None,
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
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
        item: Optional[things.ItemFinder] = None,
        key: Optional[things.ItemFinder] = None,
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
        item: Optional[things.ItemFinder] = None,
        key: Optional[things.ItemFinder] = None,
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
        container: Optional[things.ItemFinder] = None,
        item: Optional[things.ItemFinder] = None,
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
        container: Optional[things.ItemFinder] = None,
        item: Optional[things.ItemFinder] = None,
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

            if containing.take_out(item):
                with person.make(carryable.Containing) as pockets:
                    pockets.hold(item)
                return Success("done, you're holding that now")

        return Failure("doesn't seem like you can")


class MovingAction(PersonAction):
    def __init__(
        self,
        area: Optional[entity.Entity] = None,
        finder: Optional[movement.FindsRoute] = None,
        **kwargs
    ):
        super().__init__(**kwargs)
        self.area = area
        self.finder = finder

    async def move(self, ctx: Ctx, world: World, person: entity.Entity):
        area = world.find_person_area(person)

        destination = self.area

        if self.finder:
            log.info("finder: {0}".format(self.finder))
            area = world.find_person_area(person)
            route = await self.finder.find_route(
                area, person, world=world, builder=world
            )
            if route:
                routed: Any = route.area
                destination = routed

        if destination is None:
            return Failure("where?")

        with destination.make(occupyable.Occupyable) as entering:
            with area.make(occupyable.Occupyable) as leaving:
                await leaving.left(person)
                await entering.entered(person)

        return AreaObservation(world.find_person_area(person), person)


class Go(MovingAction):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        return await self.move(ctx, world, person)


class Forget(PersonAction):
    def __init__(self, name=None, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        with person.make(mechanics.Memory) as brain:
            if self.name in brain.brain:
                brain.forget(self.name)
                return Success("oh wait, was that important?")
        return Failure("huh, seems i already have forgotten that!")


class Remember(PersonAction):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        area = world.find_person_area(person)
        with person.make(mechanics.Memory) as brain:
            brain.memorize(MemoryAreaKey, area)
        return Success("you'll be able to remember this place, oh yeah")


class ModifyHardToSee(PersonAction):
    def __init__(
        self, item: Optional[things.ItemFinder] = None, hard_to_see=False, **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        self.hard_to_see = hard_to_see

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
            return Failure("of what?")

        item.try_modify()

        with item.make(mechanics.Visibility) as vis:
            if self.hard_to_see:
                vis.make_hard_to_see()
            else:
                vis.make_easy_to_see()

        return Success("done")


class ModifyField(PersonAction):
    def __init__(self, item=None, field=None, value=None, **kwargs):
        super().__init__(**kwargs)
        self.item = item
        self.field = field
        self.value = value

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
            return Failure("of what?")

        item.try_modify()

        if self.field in health.NutritionFields:
            with item.make(health.Edible) as i:
                i.nutrition.properties[self.field] = self.value
        else:
            item.props.set(self.field, self.value)

        item.touch()

        return Success("done")


class ModifyActivity(PersonAction):
    def __init__(
        self,
        item: Optional[things.ItemFinder] = None,
        activity=None,
        value=None,
        **kwargs
    ):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert activity
        self.activity = activity
        assert value
        self.value = value

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
            return Failure("of what?")

        item.try_modify()
        with item.make(mechanics.Interactable) as inaction:
            inaction.link_activity(self.activity, self.value)
        item.props.set(self.activity, self.value)
        item.touch()
        return Success("done")


class ModifyServings(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, number=None, **kwargs):
        super().__init__(**kwargs)
        assert item
        self.item = item
        assert number
        self.number = number

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

        with item.make(health.Edible) as edible:
            edible.modify_servings(self.number)

        item.touch()

        return Success("done")


class ModifyCapacity(PersonAction):
    def __init__(
        self, item: Optional[things.ItemFinder] = None, capacity=None, **kwargs
    ):
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


PourVerb = "pour"


class Pour(PersonAction):
    def __init__(
        self,
        item: Optional[things.ItemFinder] = None,
        source: Optional[things.ItemFinder] = None,
        destination: Optional[things.ItemFinder] = None,
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
    def __init__(self, template: Optional[finders.MaybeItemOrRecipe] = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        assert template
        self.template: finders.MaybeItemOrRecipe = template

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
        item: Optional[things.ItemFinder] = None,
        produces: Optional[finders.MaybeItemOrRecipe] = None,
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


class Freeze(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("freeze what?")

        if not item.can_modify():
            return Failure("already frozen, pal")

        if not item.freeze(person.identity):
            return Failure("you can't do that!")

        return Success("frozen")


class Unfreeze(PersonAction):
    def __init__(self, item: Optional[things.ItemFinder] = None, **kwargs):
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
            return Failure("unfreeze what?")

        if item.can_modify():
            return Failure("why do that?")

        if not item.unfreeze(person.identity):
            return Failure("you can't do that! is that yours?")

        return Success("unfrozen")
