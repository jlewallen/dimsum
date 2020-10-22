from typing import List, Tuple, Dict, Sequence, Optional, Union, cast

import logging
import abc
import props
import crypto
import entity
import context

log = logging.getLogger("dimsum")


class KeyMixin:
    def __init__(self, patterns: Dict[str, crypto.Identity] = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.patterns = patterns if patterns else {}

    def has_pattern(self, pattern: crypto.Identity):
        return pattern.public in self.patterns


class Lockable:
    def __init__(self, pattern: crypto.Identity = None, locked=None, **kwargs):
        super().__init__(*kwargs)
        self.pattern = pattern if pattern else None
        self.locked = locked if locked else False

    def lock(self, key: KeyMixin = None, identity=None, **kwargs):
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
            key = cast(
                KeyMixin,
                context.get().create_item(
                    details=props.Details("Key"), patterns=patterns, **kwargs
                ),
            )
            log.info("new key:%s %s", key, patterns)
            return key

        assert self.pattern

        # Key should fit us.
        if not key.has_pattern(self.pattern):
            log.info("wrong pattern on held held key:%s", key)
            return False

        self.locked = True

        return key

    def unlock(self, key: KeyMixin = None, **kwargs):
        assert key
        assert isinstance(key, KeyMixin)  # This is usually true, anyway.
        assert self.locked

        if not self.pattern:
            raise Exception("no pattern, not locked")

        if not key.has_pattern(self.pattern):
            log.info("wrong key: %s vs %s", key.patterns, self.pattern)
            return False

        self.locked = False

        log.info("unlcoked")

        return True


class LockableMixin:
    def __init__(self, lockable=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.lockable = lockable if lockable else Lockable()

    def lock(self, **kwargs):
        return self.lockable.lock(identity=self.identity, **kwargs)

    def unlock(self, **kwargs):
        return self.lockable.unlock(**kwargs)

    def is_locked(self):
        return self.lockable.us_locked()


class OpenableMixin(LockableMixin):
    def __init__(self, openenable=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.openable = {}

    def open(self, **kwargs):
        return True

    def close(self, **kwargs):
        return False


class CarryableMixin:
    def __init__(self, kind: entity.Kind = None, quantity: int = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.kind = kind if kind else entity.Kind()
        self.quantity = quantity if quantity else 1

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

    @abc.abstractmethod
    def touch(self):
        pass

    @abc.abstractmethod
    def separate(self, quantity: int, **kwargs):
        pass


CarryableType = Union[entity.Entity, CarryableMixin]


class ContainingMixin(OpenableMixin):
    def __init__(self, holding=None, **kwargs):
        super().__init__(**kwargs)
        self.holding = holding if holding else []

    def contains(self, e: CarryableMixin) -> bool:
        return e in self.holding

    def unhold(self, e: CarryableMixin, **kwargs) -> CarryableMixin:
        self.holding.remove(e)
        return e

    def place_inside(self, item: CarryableMixin, **kwargs):
        return self.hold(item, **kwargs)

    def take_out(self, item: CarryableMixin, **kwargs):
        return self.unhold(item, **kwargs)

    def hold(self, item: CarryableMixin, quantity: int = None, **kwargs):
        return self.add_item(item, **kwargs)

    def add_item(self, item: CarryableMixin, **kwargs) -> CarryableMixin:
        for already in self.holding:
            if item.kind.same(already.kind):
                already.quantity += item.quantity

                # We return, which skips the append to holding below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return already

        self.holding.append(item)
        return item

    def find_item_under(self, **kwargs) -> Optional[CarryableMixin]:
        return find_item_under(candidates=self.holding, **kwargs)

    def drop_all(self) -> List[CarryableMixin]:
        dropped = []
        while len(self.holding) > 0:
            item = self.holding[0]
            self.drop(item)
            item.touch()
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

            if quantity > item.quantity or quantity < 1:
                return None, "you should check how many you have"

            dropped = item.separate(quantity, **kwargs)
            if item.quantity == 0:
                context.get().registrar().unregister(item)
                self.drop(item)
        else:
            if item:
                dropped = self.drop(item)
            else:
                dropped = self.drop_all()

        for item in dropped:
            after_add = area.add_item(item)
            if after_add != item:
                context.get().registrar().unregister(item)

        return dropped, None

    def drop(self, item: CarryableMixin) -> List[CarryableMixin]:
        if item in self.holding:
            self.holding.remove(item)
            item.touch()
            return [item]
        return []


class CarryingMixin(ContainingMixin):
    pass


def find_item_under(
    q: str = None, candidates=None, exclude=None, **kwargs
) -> Optional[CarryableMixin]:
    log.info("find-item-under: '%s' candidates=%s exclude=%s", q, candidates, exclude)
    for e in candidates:
        if not exclude or e not in exclude:
            if q:
                if e.describes(q):
                    return e
            else:
                return e

    return None
