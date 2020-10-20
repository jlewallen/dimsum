from typing import List, Tuple, Dict, Sequence, Optional

import logging
import abc
import entity
import context

log = logging.getLogger("dimsum")


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
    def separate(self, quantity: int, ctx: context.Ctx = None, **kwargs):
        pass


class ContainingMixin:
    def __init__(self, holding=None, **kwargs):
        super().__init__(**kwargs)
        self.holding = holding if holding else []

    def contains(self, e: CarryableMixin) -> bool:
        return e in self.holding

    def unhold(self, e: CarryableMixin, **kwargs) -> CarryableMixin:
        self.holding.remove(e)
        return e

    def add_item(self, item: CarryableMixin) -> CarryableMixin:
        for h in self.holding:
            if item.kind.same(h.kind):
                h.quantity += item.quantity

                # We return, which skips the append to holding below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return h

        self.holding.append(item)
        return item

    def find(self, q: str) -> Optional[CarryableMixin]:
        for e in self.holding:
            if e.describes(q):
                return e
        return None

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

    def hold(self, item: CarryableMixin, quantity: int = None):
        # See if there's a kind already in inventory.
        for already in self.holding:
            if item.kind.same(already.kind):
                # This will probably need more protection haha
                already.quantity += item.quantity
                already.touch()

                # We return, which skips the append to containing below,
                # and that has the effect of obliterating the item we
                # picked up, merging with the one in our hands.
                return already
        self.holding.append(item)
        item.touch()
        return item

    def drop_here(
        self,
        area: "ContainingMixin",
        item: CarryableMixin = None,
        quantity: int = None,
        ctx: context.Ctx = None,
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

            dropped = item.separate(quantity, ctx=ctx, **kwargs)
            if item.quantity == 0:
                assert ctx
                ctx.registrar().unregister(item)
                self.drop(item)
        else:
            if item:
                dropped = self.drop(item)
            else:
                dropped = self.drop_all()

        for item in dropped:
            after_add = area.add_item(item)
            if after_add != item:
                assert ctx
                ctx.registrar().unregister(item)

        return dropped, None

    def drop(self, item: CarryableMixin) -> List[CarryableMixin]:
        if item in self.holding:
            self.holding.remove(item)
            item.touch()
            return [item]
        return []


class CarryingMixin(ContainingMixin):
    pass
