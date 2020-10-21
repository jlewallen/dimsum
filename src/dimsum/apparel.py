from typing import List

import abc


class Wearable:
    @abc.abstractmethod
    def touch(self):
        pass


class ApparelMixin:
    def __init__(self, wearing=None, **kwargs):
        super().__init__(**kwargs)
        self.wearing: List[Wearable] = wearing if wearing else []

    def is_wearing(self, item: Wearable) -> bool:
        return item in self.wearing

    def wear(self, item: Wearable) -> bool:
        self.wearing.append(item)
        item.touch()
        return True

    def unwear(self, item: Wearable, **kwargs) -> bool:
        self.wearing.remove(item)
        item.touch()
        return True
