from typing import List

import abc


class WearableMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @abc.abstractmethod
    def touch(self):
        pass


class ApparelMixin:
    def __init__(self, wearing=None, **kwargs):
        super().__init__(**kwargs)
        self.wearing: List[WearableMixin] = wearing if wearing else []

    def is_wearing(self, item: WearableMixin) -> bool:
        return item in self.wearing

    def wear(self, item: WearableMixin) -> bool:
        self.wearing.append(item)
        item.touch()
        return True

    def unwear(self, item: WearableMixin, **kwargs) -> bool:
        self.wearing.remove(item)
        item.touch()
        return True
