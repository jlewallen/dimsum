from typing import Dict, Any, Optional
import logging
import abc
import props

log = logging.getLogger("dimsum")


class InteractableMixin:
    def __init__(self, interactions: Dict[str, Any] = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.interactions = interactions if interactions else {}

    def link_activity(self, name: str, activity=True):
        self.interactions[name] = activity

    def when_activity(self, name: str) -> bool:
        return self.interactions[name] if name in self.interactions else False

    def when_worn(self) -> bool:
        return self.when_activity(props.Worn)

    def when_eaten(self) -> bool:
        return self.when_activity(props.Eaten)

    def when_drank(self) -> bool:
        return self.when_activity(props.Drank)


class Visible:
    def __init__(self):
        self.hidden = False


class VisibilityMixin:
    def __init__(self, visible: Visible = None, **kwargs):
        super().__init__()
        self.visible: Visible = visible if visible else Visible()

    def make_visible(self):
        self.visible.hidden = False

    def make_invisible(self):
        self.visible.hidden = True

    @property
    def is_invisible(self) -> bool:
        return self.visible.hidden


class Memorable:
    @abc.abstractmethod
    def describes(self, q: str) -> bool:
        pass


class MemoryMixin:
    def __init__(self, memory: Dict[str, Memorable] = None, **kwargs):
        super().__init__()
        self.memory = memory if memory else {}

    def find_memory(self, q: str) -> Optional[Memorable]:
        for name, entity in self.memory.items():
            if q.lower() in name.lower():
                return entity
        for name, entity in self.memory.items():
            if entity.describes(q):
                return entity
        return None
