import abc
import datetime
import enum
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from loggers import get_logger
from model import Entity, Scope, Identity, Worn, Eaten, Drank, Acls

log = get_logger("dimsum.scopes")


@dataclass
class Interactable(Scope):
    interactions: Dict[str, bool] = field(default_factory=dict)

    def link_activity(self, name: str, activity=True):
        self.interactions[name] = activity

    def when_activity(self, name: str) -> bool:
        return self.interactions[name] if name in self.interactions else False

    def when_worn(self) -> bool:
        return self.when_activity(Worn)

    def when_eaten(self) -> bool:
        return self.when_activity(Eaten)

    def when_drank(self) -> bool:
        return self.when_activity(Drank)


def get_now() -> datetime.datetime:
    return datetime.datetime.now()


class Observation:
    def __init__(self, time=None, **kwargs):
        super().__init__()
        self.time = time if time else get_now()

    def memorable(self) -> bool:
        age = get_now() - self.time
        return age.total_seconds() < 60 * 60


class Observer:
    @abc.abstractmethod
    def observe(self, identity: Identity):
        raise NotImplementedError


@dataclass
class Presence:
    distinct: bool = False
    inline: Optional[str] = None

    Distinct = lambda: Presence(distinct=True)
    InlineShort = lambda: Presence(inline="short")
    InlineLong = lambda: Presence(inline="long")


class Visible:
    def __init__(
        self,
        hidden: bool = False,
        hard_to_see: bool = False,
        presence: Optional[Presence] = None,
        observations: Optional[Dict[str, List[Observation]]] = None,
        **kwargs
    ):
        super().__init__()
        self.hidden = hidden
        self.hard_to_see = hard_to_see
        self.presence = presence if presence else Presence.Distinct()
        self.observations = observations if observations else {}

    def add_observation(self, identity: Identity):
        if identity.public not in self.observations:
            self.observations[identity.public] = []
        self.observations[identity.public].append(Observation())

    def can_see(self, identity: Identity) -> bool:
        if not identity.public in self.observations:
            return False

        obs = self.observations[identity.public]
        if not obs:
            return False

        return obs[-1].memorable()


@dataclass
class Visibility(Scope):
    acls: Acls = field(default_factory=Acls.owner_writes)
    visible: Visible = field(default_factory=Visible)

    def make_visible(self):
        if self.visible.hidden:
            self.ourselves.touch()
        self.visible.hidden = False

    def make_invisible(self):
        if not self.visible.hidden:
            self.ourselves.touch()
        self.visible.hidden = True

    def can_see(self, identity: Identity) -> bool:
        return self.visible.can_see(identity)

    def make_easy_to_see(self):
        if self.visible.hard_to_see:
            self.ourselves.touch()
        self.visible.hard_to_see = False

    def make_hard_to_see(self):
        if not self.visible.hard_to_see:
            self.ourselves.touch()
        self.visible.hard_to_see = True

    def add_observation(self, identity: Identity):
        self.ourselves.touch()
        return self.visible.add_observation(identity)

    @property
    def is_invisible(self) -> bool:
        return self.visible.hidden


class Physics:
    def __init__(self, mass=None, **kwargs):
        super().__init__()
        self.mass = mass


@dataclass
class Memory(Scope):
    memory: Dict[str, Entity] = field(default_factory=dict)

    def memorize(self, q: str, thing: Entity):
        self.memory[q] = thing

    def forget(self, q: str):
        del self.memory[q]

    def find_memory(self, q: str) -> Optional[Entity]:
        for name, entity in self.memory.items():
            if q.lower() in name.lower():
                return entity
        for name, entity in self.memory.items():
            if entity.describes(q=q):
                return entity
        return None


class Wind:
    def __init__(self, magnitude: float = 0.0, **kwargs):
        super().__init__()
        self.magnitude = magnitude


class Weather(Scope):
    def __init__(self, wind: Optional[Wind] = None, **kwargs):
        super().__init__(**kwargs)
        self.wind = wind
