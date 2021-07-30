from dataclasses import dataclass, field
from typing import (
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Union,
    Callable,
    Coroutine,
    Awaitable,
)

from loggers import get_logger
from model import (
    Entity,
    Scope,
    Common,
    Identity,
    generate_entity_identity,
    Kind,
    Acls,
    context,
)

log = get_logger("dimsum.scopes")


@dataclass
class Key(Scope):
    acls: Acls = field(default_factory=Acls.owner_writes)
    patterns: Dict[str, Identity] = field(default_factory=dict)

    def has_pattern(self, pattern: Identity):
        return pattern.public in self.patterns


@dataclass
class Lockable(Scope):
    acls: Acls = field(default_factory=Acls.owner_writes)
    pattern: Optional[Identity] = None
    locked: bool = False

    def is_locked(self) -> bool:
        return self.locked

    def lock(self, key: Optional[Entity] = None, identity=None, **kwargs):
        assert not self.locked

        identity = identity if identity else self.ourselves.identity

        if not key:
            # Only way this works is if we don't have a secret yet.
            if self.pattern:
                raise Exception("already have a secret, need key")

            self.pattern = generate_entity_identity()
            self.locked = True
            self.ourselves.touch()

            patterns = {}
            patterns[self.pattern.public] = self.pattern
            key = context.get().create_item(props=Common("Key"), **kwargs)
            assert key
            with key.make(Key) as keying:
                keying.patterns = patterns
            log.info("new key:%s %s", key, patterns)
            return key

        assert self.pattern

        # Key should fit us.
        with key.make(Key) as inspecting:
            if not inspecting.has_pattern(self.pattern):
                log.info("wrong pattern on held held key:%s", key)
                return False

        self.locked = True
        self.ourselves.touch()

        return key

    def unlock(self, key: Optional[Entity] = None, **kwargs):
        assert key
        assert self.locked

        if not self.pattern:
            raise Exception("no pattern, not locked")

        with key.make(Key) as inspecting:
            if not inspecting.has_pattern(self.pattern):
                log.info("wrong key: %s vs %s", inspecting.patterns, self.pattern)
                return False

        self.locked = False
        self.ourselves.touch()

        log.info("unlcoked")

        return True


class OpenClose:
    def is_open(self):
        raise NotImplementedError

    def open(self):
        raise NotImplementedError

    def close(self):
        raise NotImplementedError


class Closed(OpenClose):
    def is_open(self):
        return False

    def open(self):
        return Opened()


class Opened(OpenClose):
    def is_open(self):
        return True

    def close(self):
        return Closed()


class UnknownOpenClose(OpenClose):
    def is_open(self):
        return False

    def open(self):
        return Opened()


class Openable(Lockable):
    def __init__(self, openable: Optional[OpenClose] = None, **kwargs):
        super().__init__(**kwargs)
        self.openable = openable if openable else UnknownOpenClose()

    def is_open(self):
        return self.openable.is_open()

    def open(self, **kwargs):
        if self.is_locked():
            log.info("openable:locked")
            return False
        if self.openable.is_open():
            log.info("openable:is-open")
            return False
        log.info("openable:opening")
        self.openable = self.openable.open()
        self.ourselves.touch()
        return True

    def close(self, **kwargs):
        if self.openable.is_open():
            self.openable = self.openable.close()
            self.ourselves.touch()
            return True
        return False


@dataclass
class Carryable(Scope):
    kind: Kind = field(
        default_factory=lambda: Kind(identity=generate_entity_identity())
    )
    quantity: float = 1
    loose: bool = False

    def increase_quantity(self, q: float):
        self.quantity += q
        return self

    def decrease_quantity(self, q: float):
        if q < 1:
            raise Exception("too few to separate")

        if q > self.quantity:
            raise Exception("too many to separate")

        self.quantity -= q
        return self

    def separate(self, quantity: float, **kwargs) -> List[Entity]:
        self.decrease_quantity(quantity)
        self.ourselves.touch()

        item = context.get().create_item(
            props=self.ourselves.props.clone(),
            initialize={Carryable: dict(quantity=quantity, kind=self.kind)},
            **kwargs,
        )

        context.get().register(item)

        return [item]


class Producer:
    def produce_item(self, **kwargs) -> Entity:
        raise NotImplementedError


@dataclass
class Location(Scope):
    acls: Acls = field(default_factory=Acls.owner_writes)
    container: Optional[Entity] = None


class Containing(Openable):
    def __init__(self, holding=None, capacity=None, produces=None, **kwargs):
        super().__init__(**kwargs)
        self.holding: List[Entity] = holding if holding else []
        self.capacity = capacity if capacity else None
        self.produces: Dict[str, Producer] = produces if produces else {}
        self.acls = Acls.everybody_writes()

    def produces_when(self, verb: str, item: Producer):
        self.produces[verb] = item

    def produce_into(self, verb: str, container: Entity, **kwargs):
        with container.make(Containing) as into:
            if not into.is_open():
                log.info("produce_into: unopened")
                return False
            if verb not in self.produces:
                log.info("produce_into: nothing for %s", verb)
                return False

            producer = self.produces[verb]
            log.info("%s produces %s", self, producer)
            item = producer.produce_item(**kwargs)
            context.get().register(item)
            return into.hold(item)

    def adjust_capacity(self, capacity):
        self.capacity = capacity
        log.info("opening %s", self)
        self.open()
        log.info("opening %s", self.is_open())
        self.ourselves.touch()
        return True

    def can_hold(self) -> bool:
        if self.capacity is None:
            return False
        return True

    def contains(self, e: Entity) -> bool:
        return e.key in [f.key for f in self.holding]

    def unhold(self, e: Entity, **kwargs) -> Entity:
        removed = [f for f in self.holding if f.key == e.key]
        for r in removed:
            self.holding.remove(r)
        assert removed
        self.ourselves.touch()
        with e.make(Location) as location:
            location.container = None
        return e

    def place_inside(self, item: Entity, **kwargs):
        if self.is_open():
            return self.hold(item, **kwargs)
        return False

    def take_out(self, item: Entity, **kwargs):
        if self.is_open():
            if item in self.holding:
                return self.unhold(item, **kwargs)
        return False

    def hold(self, item: Entity, quantity: Optional[float] = None, **kwargs):
        log.debug("%s holding %s", self.ourselves, item)
        return self.add_item(item, **kwargs)

    def add_item(self, item: Entity, **kwargs) -> Entity:
        for already in self.holding:
            with already.make(Carryable) as additional:
                with item.make(Carryable) as coming:
                    if additional.kind.same(coming.kind):
                        additional.quantity += coming.quantity

                        already.touch()

                        # We return, which skips the append to holding below,
                        # and that has the effect of obliterating the item we
                        # picked up, merging with the one in our hands.
                        return already

                # It's possible this item wasn't Carryable and we just
                # added that scope, so discard if we ended up ignoring
                # the item.
                additional.discard()

        self.ourselves.touch()
        self.holding.append(item)

        with item.make(Location) as location:
            location.container = self.ourselves
            item.touch()
        return item

    async def drop_all(
        self, condition: Optional[Callable[[Entity], Awaitable[bool]]] = None
    ) -> List[Entity]:
        dropped = []
        for item in self.holding:
            if not condition or await condition(item):
                self.drop(item)
                dropped.append(item)
        if len(dropped) > 0:
            self.ourselves.touch()
        return dropped

    def is_holding(self, item: Entity):
        return item in self.holding

    async def drop_here(
        self,
        area: Entity,
        item: Optional[Entity] = None,
        quantity: Optional[float] = None,
        condition: Optional[Callable[[Entity], Awaitable[bool]]] = None,
        **kwargs,
    ):
        if len(self.holding) == 0:
            return None, "nothing to drop"

        dropped: List[Entity] = []
        if quantity:
            if not item:
                return None, "of what, though?"

            with item.make(Carryable) as dropping:
                if quantity > dropping.quantity or quantity < 1:
                    return None, "you should check how many you have"

                dropped = dropping.separate(quantity, **kwargs)
                log.info("separated: %s (%d)", dropped, quantity)
                assert dropped
                if dropping.quantity == 0:
                    context.get().unregister(item)
                    self.drop(item)
                    self.ourselves.touch()
        else:
            if item:
                dropped = self.drop(item)
                assert dropped
            else:
                dropped = await self.drop_all(condition=condition)
                assert dropped

        for item in dropped:
            with area.make(Containing) as ground:
                after_add = ground.add_item(item)
                if after_add != item:
                    context.get().unregister(item)

        return dropped, None

    def drop(self, e: Entity) -> List[Entity]:
        if e in self.holding:
            self.holding.remove(e)
            self.ourselves.touch()
            with e.make(Location) as location:
                location.container = None
            e.touch()
            return [e]
        return []

    def entities(self) -> List[Entity]:
        return self.holding

    def entities_named(self, of: str):
        return [e for e in self.entities() if e.describes(q=of)]

    def entities_of_kind(self, kind: Kind):
        return [
            e
            for e in self.entities()
            if e.make(Carryable).kind and e.make(Carryable).kind.same(kind)
        ]

    def number_of_named(self, of: str) -> float:
        return sum([e.quantity for e in self.entities_named(of)])

    def number_of_kind(self, kind: Kind) -> float:
        return sum([e.make(Carryable).quantity for e in self.entities_of_kind(kind)])
