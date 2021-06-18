from typing import Any, List, Tuple, Dict, Sequence, Optional, Union, cast

import logging
import abc
import properties
import crypto
import kinds
import entity
import context

log = logging.getLogger("dimsum")


class KeyMixin(entity.Spawned):
    def __init__(self, patterns: Dict[str, crypto.Identity] = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.patterns = patterns if patterns else {}

    def has_pattern(self, pattern: crypto.Identity):
        return pattern.public in self.patterns


class Lockable:
    def __init__(self, pattern: crypto.Identity = None, locked=None, **kwargs):
        super().__init__(*kwargs)
        log.info("lockable %s", locked)
        self.pattern = pattern if pattern else None
        self.locked = locked if locked else False

    def is_locked(self) -> bool:
        return self.locked

    def lock(self, key: entity.Entity = None, identity=None, **kwargs):
        assert identity
        assert not self.locked

        if not key:
            # Only way this works is if we don't have a secret yet.
            if self.pattern:
                raise Exception("already have a secret, need key")

            self.pattern = crypto.generate_identity()
            self.locked = True

            patterns = {}
            patterns[self.pattern.public] = self.pattern
            key = context.get().create_item(props=properties.Common("Key"), **kwargs)
            assert key
            with key.make(KeyMixin) as keying:
                keying.patterns = patterns
            log.info("new key:%s %s", key, patterns)
            return key

        assert self.pattern

        # Key should fit us.
        with key.make(KeyMixin) as inspecting:
            if not inspecting.has_pattern(self.pattern):
                log.info("wrong pattern on held held key:%s", key)
                return False

        self.locked = True

        return key

    def unlock(self, key: entity.Entity = None, **kwargs):
        assert key
        assert self.locked

        if not self.pattern:
            raise Exception("no pattern, not locked")

        with key.make(KeyMixin) as inspecting:
            if not inspecting.has_pattern(self.pattern):
                log.info("wrong key: %s vs %s", inspecting.patterns, self.pattern)
                return False

        self.locked = False

        log.info("unlcoked")

        return True


class LockableMixin(entity.Spawned):
    def __init__(self, lockable=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.lockable = lockable if lockable else Lockable()

    def lock(self, **kwargs):
        return self.lockable.lock(identity=self.ourselves.identity, **kwargs)

    def unlock(self, **kwargs):
        return self.lockable.unlock(**kwargs)

    def is_locked(self):
        return self.lockable.is_locked()


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


class OpenableMixin(LockableMixin):
    def __init__(self, openable: OpenClose = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
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
        return True

    def close(self, **kwargs):
        if self.openable.is_open():
            self.openable = self.openable.close()
            return True
        return False


class CarryableMixin(entity.Spawned):
    def __init__(
        self,
        kind: kinds.Kind = None,
        quantity: int = None,
        loose: bool = False,
        **kwargs,
    ):
        super().__init__(**kwargs)  # type: ignore
        self.kind = kind if kind else kinds.Kind()
        self.quantity = quantity if quantity else 1
        self.loose = loose

    def increase_quantity(self, q: int):
        self.quantity += q
        return self

    def decrease_quantity(self, q: int):
        if q < 1:
            raise Exception("too few to separate")

        if q > self.quantity:
            raise Exception("too many to separate")

        self.quantity -= q
        return self

    def separate(
        self, quantity: int, ctx: context.Ctx = None, **kwargs
    ) -> List["entity.Entity"]:
        assert ctx
        log.info("separating")
        self.decrease_quantity(quantity)
        item = context.get().create_item(
            kind=self.ourselves.kind,
            props=self.ourselves.props.clone(),
            # behaviors=self.behaviors,
            **kwargs
        )
        with item.make(CarryableMixin) as carry:
            carry.quantity = quantity
        # TODO Move to caller
        ctx.registrar().register(item)
        return [item]


CarryableType = Union[entity.Entity, CarryableMixin]


class Producer:
    def produce_item(self, **kwargs) -> entity.Entity:
        raise NotImplementedError


class ContainingMixin(OpenableMixin):
    def __init__(self, holding=None, capacity=None, produces=None, **kwargs):
        super().__init__(**kwargs)
        self.holding: List[CarryableMixin] = holding if holding else []
        self.capacity = capacity if capacity else None
        self.produces: Dict[str, Producer] = produces if produces else {}

    def produces_when(self, verb: str, item: Producer):
        self.produces[verb] = item

    def produce_into(self, verb: str, container: "entity.Entity", **kwargs):
        with container.make(ContainingMixin) as into:
            if not into.is_open():
                log.info("produce_into: unopened")
                return False
            if verb not in self.produces:
                log.info("produce_into: nothing for %s", verb)
                return False

            producer = self.produces[verb]
            log.info("%s produces %s", self, producer)
            item = cast(CarryableMixin, producer.produce_item(**kwargs))
            context.get().registrar().register(item)
            return into.hold(item)

    def adjust_capacity(self, capacity):
        self.capacity = capacity
        log.info("opening %s", self)
        self.open()
        log.info("opening %s", self.is_open())
        return True

    def can_hold(self) -> bool:
        if self.capacity is None:
            return False
        return True

    def contains(self, e: CarryableMixin) -> bool:
        return e in self.holding

    def unhold(self, e: CarryableMixin, **kwargs) -> CarryableMixin:
        self.holding.remove(e)
        return e

    def place_inside(self, item: CarryableMixin, **kwargs):
        if self.is_open():
            return self.hold(item, **kwargs)
        return False

    def take_out(self, item: CarryableMixin, **kwargs):
        if self.is_open():
            if item in self.holding:
                return self.unhold(item, **kwargs)
        return False

    def hold(self, item: CarryableMixin, quantity: int = None, **kwargs):
        log.info("holding %s", item)
        return self.add_item(item, **kwargs)

    def add_item(self, item: CarryableMixin, **kwargs) -> CarryableMixin:
        for already in self.holding:
            log.info("adding %s already = %s", item.kind, already.kind)
            log.info("adding %s already = %s", item, already)
            if item.kind.same(already.kind):
                with cast(entity.Entity, already).make(CarryableMixin) as additional:
                    with cast(entity.Entity, item).make(CarryableMixin) as coming:
                        additional.quantity += coming.quantity

                # We return, which skips the append to holding below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return already

        self.holding.append(item)
        return item

    def drop_all(self) -> List[CarryableMixin]:
        dropped = []
        while len(self.holding) > 0:
            item = self.holding[0]
            self.drop(item)
            dropped.append(item)
        return dropped

    def is_holding(self, item: CarryableMixin):
        return item in self.holding

    def drop_here(
        self,
        area: "ContainingMixin",
        item: CarryableMixin = None,
        quantity: int = None,
        **kwargs,
    ):
        if len(self.holding) == 0:
            return None, "nothing to drop"

        dropped: List[CarryableMixin] = []
        if quantity:
            if not item:
                return None, "please specify what?"

            with cast(entity.Entity, item).make(CarryableMixin) as dropping:
                if quantity > dropping.quantity or quantity < 1:
                    return None, "you should check how many you have"

                dropped = dropping.separate(quantity, **kwargs)
                log.info("separated: %s (%d)", dropped, quantity)
                assert dropped
                if dropping.quantity == 0:
                    context.get().registrar().unregister(item)
                    self.drop(item)
        else:
            if item:
                dropped = self.drop(item)
                assert dropped
            else:
                dropped = self.drop_all()
                assert dropped

        for item in dropped:
            with cast(entity.Entity, area).make(ContainingMixin) as ground:
                after_add = ground.add_item(item)
                if after_add != item:
                    context.get().registrar().unregister(item)

        return dropped, None

    def drop(self, item: CarryableMixin) -> List[CarryableMixin]:
        if item in self.holding:
            self.holding.remove(item)
            return [item]
        return []


def expected(maybes: List[Any]) -> List[CarryableMixin]:
    return [cast(CarryableMixin, e) for e in maybes]
