from typing import Any

import os
import base64

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


MemoryAreaKey = "m:area"
log = logging.getLogger("dimsum")


class PersonAction(Action):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        raise NotImplementedError


class Unknown(PersonAction):
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
        log.warning("{0} performed".format(self))
        return Failure("sorry, i don't understand")


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
        await ctx.extend().hook("home:before")
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

        await ctx.publish(ItemsAppeared(area=self.area, items=[self.item]))
        await ctx.extend(area=self.area, appeared=[self.item]).hook("appeared:after")
        return Success("%s appeared" % (p.join([self.item]),))


class Make(PersonAction):
    def __init__(
        self,
        template: finders.MaybeItemOrRecipe = None,
        item: things.ItemFinder = None,
        **kwargs
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
        **kwargs
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
        await ctx.publish(ItemsMade(person=person, area=area, items=[after_hold]))
        return Success("you're now holding %s" % (after_hold,), item=after_hold)


class Wear(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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

        # TODO Publish
        await ctx.extend(wear=[item]).hook("wear:after")
        return Success("you wore %s" % (item))


class Remove(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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

        await ctx.extend(remove=[item]).hook("remove:after")
        return Success("you removed %s" % (item))


class Eat(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
        await ctx.extend(eat=item).hook("eat:after")

        return Success("you ate %s" % (item))


class Drink(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
        await ctx.extend(eat=item).hook("drink:after")

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
        await ctx.publish(PlayerJoined(person=person))
        await ctx.hook("entered:before")
        with world.welcome_area().make(occupyable.Occupyable) as entering:
            log.info("welcome area: %s", world.welcome_area())
            await entering.entered(person)
        await ctx.hook("entered:after")
        return Success("welcome!")


class LookInside(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
            await ctx.extend(holding=contain.holding, item=item).hook("look-for")
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
        await ctx.hook("look-myself")
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
        await ctx.hook("look-down")
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
    def __init__(self, item: things.ItemFinder = None, quantity: int = None, **kwargs):
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
                    ItemsDropped(person=person, area=area, dropped=dropped)
                )
                await ctx.extend(dropped=dropped).hook("drop:after")
                return Success("you dropped %s" % (p.join(dropped),))

            return Failure(failure)


class Hold(PersonAction):
    def __init__(self, item: things.ItemFinder = None, quantity: int = None, **kwargs):
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
                await ctx.publish(ItemHeld(person=person, area=area, hold=[after_hold]))
                await ctx.extend(hold=[after_hold]).hook("hold:after")
                return Success("you picked up %s" % (after_hold,), item=after_hold)


class Open(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
        self, item: things.ItemFinder = None, key: things.ItemFinder = None, **kwargs
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
        self, item: things.ItemFinder = None, key: things.ItemFinder = None, **kwargs
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
        container: things.ItemFinder = None,
        item: things.ItemFinder = None,
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
        container: things.ItemFinder = None,
        item: things.ItemFinder = None,
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
        self, area: entity.Entity = None, finder: movement.FindsRoute = None, **kwargs
    ):
        super().__init__(**kwargs)
        self.area = area
        self.finder = finder

    async def move(
        self, ctx: Ctx, world: World, person: entity.Entity, verb=DefaultMoveVerb
    ):
        area = world.find_person_area(person)

        destination = self.area

        if self.finder:
            log.info("finder: {0}".format(self.finder))
            area = world.find_person_area(person)
            route = await self.finder.find_route(
                area, person, world=world, verb=verb, builder=world
            )
            if route:
                routed: Any = route.area
                destination = routed

        if destination is None:
            return Failure("where?")

        with destination.make(occupyable.Occupyable) as entering:
            with area.make(occupyable.Occupyable) as leaving:
                await ctx.extend(area=area).hook("left:before")
                await leaving.left(person)
                await ctx.extend(area=area).hook("left:after")
                await ctx.extend(area=destination).hook("entered:before")
                await entering.entered(person)
                await ctx.extend(area=destination).hook("entered:after")

        return AreaObservation(world.find_person_area(person), person)


class Climb(MovingAction):
    async def perform(
        self,
        world: World,
        area: entity.Entity,
        person: entity.Entity,
        ctx: Ctx,
        **kwargs
    ):
        # If climb ever becomes a string outside of this function, rethink.
        return await self.move(ctx, world, person, verb="climb")


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


class Obliterate(PersonAction):
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
        items = None
        with person.make(carryable.Containing) as pockets:
            items = pockets.drop_all()
        if len(items) == 0:
            return Failure("you're not holding anything")

        item: Any = None  # TODO Carryable to Entity

        for item in items:
            item.try_modify()

        for item in items:
            ctx.unregister(item)
            await ctx.publish(ItemObliterated(person=person, area=area, item=item))

        await ctx.extend(obliterate=items).hook("obliterate:after")

        return Success("you obliterated %s" % (p.join(list(map(str, items))),))


class CallThis(PersonAction):
    def __init__(self, name: str = None, item: things.ItemFinder = None, **kwargs):
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
        **kwargs
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
            updated = copy.deepcopy(template.__dict__)
            updated.update(key=None, identity=None, props=template.props.clone())
            log.info("updated = %s", updated)
            cloned = scopes.item(**updated)
            makes.template = cloned
            ctx.register(cloned)

        ctx.register(recipe)
        with person.make(mechanics.Memory) as brain:
            brain.memorize("r:" + self.name, recipe)
        return Success(
            "cool, you'll be able to make another %s easier now" % (self.name,)
        )


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
    def __init__(self, item: things.ItemFinder = None, hard_to_see=False, **kwargs):
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
        self, item: things.ItemFinder = None, activity=None, value=None, **kwargs
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
        return Success("done")


class ModifyServings(PersonAction):
    def __init__(self, item: things.ItemFinder = None, number=None, **kwargs):
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
        return Success("done")


class ModifyCapacity(PersonAction):
    def __init__(self, item: things.ItemFinder = None, capacity=None, **kwargs):
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
        item: things.ItemFinder = None,
        source: things.ItemFinder = None,
        destination: things.ItemFinder = None,
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
    def __init__(self, template: finders.MaybeItemOrRecipe = None, **kwargs):
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
        item: things.ItemFinder = None,
        produces: finders.MaybeItemOrRecipe = None,
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

        return Success("done")


class ItemsAppeared(Event):
    pass


class Freeze(PersonAction):
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
    def __init__(self, item: things.ItemFinder = None, **kwargs):
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
