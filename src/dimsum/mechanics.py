from typing import List, Dict, Any, Optional
import logging
import datetime
import abc
import crypto
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


def get_now() -> datetime.datetime:
    return datetime.datetime.now()


class Observation:
    def __init__(self, time=None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.time = time if time else get_now()

    def memorable(self) -> bool:
        age = get_now() - self.time
        return age.total_seconds() < 60 * 60


class Observer:
    @abc.abstractmethod
    def observe(self, identity: crypto.Identity):
        raise NotImplementedError


class Visible:
    def __init__(
        self,
        hidden=None,
        hard_to_see=False,
        observations: Dict[str, List[Observation]] = None,
        **kwargs
    ):
        super().__init__()
        self.hidden = hidden
        self.hard_to_see = hard_to_see
        self.observations = observations if observations else {}

    def add_observation(self, identity: crypto.Identity):
        if identity.public not in self.observations:
            self.observations[identity.public] = []
        self.observations[identity.public].append(Observation())

    def can_see(self, identity: crypto.Identity) -> bool:
        if not identity.public in self.observations:
            return False

        obs = self.observations[identity.public]
        if not obs:
            return False

        return obs[-1].memorable()


class VisibilityMixin:
    def __init__(self, visible: Visible = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.visible: Visible = visible if visible else Visible()

    def make_visible(self):
        self.visible.hidden = False

    def make_invisible(self):
        self.visible.hidden = True

    def can_see(self, identity: crypto.Identity) -> bool:
        return self.visible.can_see(identity)

    def make_easy_to_see(self):
        self.visible.hard_to_see = False

    def make_hard_to_see(self):
        self.visible.hard_to_see = True

    def add_observation(self, identity: crypto.Identity):
        return self.visible.add_observation(identity)

    @property
    def is_invisible(self) -> bool:
        return self.visible.hidden


class Memorable:
    @abc.abstractmethod
    def describes(self, q: str) -> bool:
        pass


class Physics:
    def __init__(self, mass=None, **kwargs):
        super().__init__()
        self.mass = mass


class PhysicsMixin:
    def __init__(self, physics: Physics = None, **kwargs):
        super().__init__(**kwargs)  # type: ignore
        self.physics = physics if physics else Physics()


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


class Wind:
    def __init__(self, magnitude: float = 0.0, **kwargs):
        super().__init__()
        self.magnitude = magnitude


class Weather:
    def __init__(self, wind: Wind = None, **kwargs):
        super().__init__()
        self.wind = wind


class WeatherMixin:
    def __init__(self, weather: Weather = None, **kwargs):
        super().__init__()
        self.weather = weather if weather else Weather()

    def add_weather(self, weather: Weather):
        self.weather = weather
