import copy
import logging
import re
import time
from typing import Dict, Optional, Optional

from .permissions import Acls
from .crypto import Identity
from .kinds import Kind

log = logging.getLogger("dimsum.model")

GlobalId = "gid"
Name = "name"
Described = "described"
Desc = "desc"
Created = "created"
Touched = "touched"
Frozen = "frozen"
Destroyed = "destroyed"
Related = "related"

# TODO remove
Worn = "worn"
Opened = "opened"
Eaten = "eaten"
Drank = "drank"


class Property:
    def __init__(self, value=None, name=None):
        self.value = value
        self.acls = Acls(name)

    def set(self, value):
        self.value = value

    def __repr__(self):
        return "Property<{0}>".format(self.value)


class Map:
    def __init__(self, map: Optional[Dict[str, Property]] = None):
        self.map = map if map else {}

    def __contains__(self, key):
        return key in self.map

    def __getitem__(self, key):
        if key in self.map:
            return self.map[key].value
        raise KeyError("invalid property: {0}".format(key))

    def __setitem__(self, key, value):
        self.set(key, value)

    @property
    def keys(self):
        return self.map.keys()

    def keys_matching(self, pattern: str):
        return [k for k in self.map.keys() if re.match(pattern, k)]

    def set(self, key: str, value):
        if key in self.map:
            self.map[key].set(value)
        else:
            if isinstance(value, Property):
                self.map[key] = value
            else:
                self.map[key] = Property(value, name=key)

    def update(self, changes):
        for key, value in changes.items():
            self.set(key, value)

    def replace(self, **replacing):
        self.map = replacing

    def clone(self):
        return Map(self.map)

    def __str__(self):
        return "Map<{0}>".format(self.map)

    def __repr__(self):
        return str(self)


class Common(Map):
    def __init__(
        self,
        name: Optional[str] = None,
        desc: Optional[str] = None,
        described: Optional[str] = None,
        **kwargs
    ):
        super().__init__(kwargs)
        self.set(GlobalId, -1)
        self.set(Name, name)
        self.set(Described, described or name)
        self.set(Desc, desc if desc else name)
        self.set(Created, time.time())
        self.set(Touched, time.time())
        self.set(Frozen, None)
        self.set(Destroyed, None)
        self.set(Related, {})

    @property
    def gid(self) -> int:
        return self[GlobalId]

    @gid.setter
    def gid(self, value: int):
        self.set(GlobalId, value)

    @property
    def name(self) -> str:
        return self[Name]

    @name.setter
    def name(self, value: str):
        self.set(Name, value)

    @property
    def described(self) -> str:
        return self[Described]

    @described.setter
    def described(self, value: str):
        self.set(Described, value)

    @property
    def desc(self) -> str:
        return self[Desc]

    @desc.setter
    def desc(self, value: str):
        self.set(Desc, value)

    @property
    def destroyed(self) -> Optional[Identity]:
        return self[Destroyed]

    @destroyed.setter
    def destroyed(self, value: Optional[Identity]):
        self.set(Destroyed, value)

    @property
    def frozen(self) -> Optional[Identity]:
        return self[Frozen]

    @frozen.setter
    def frozen(self, value: Optional[Identity]):
        self.set(Frozen, value)

    @property
    def related(self) -> Dict[str, Kind]:
        return self[Related]

    @related.setter
    def related(self, value: Dict[str, Kind]):
        self.set(Related, value)

    def clone(self) -> "Common":
        cloned = Common(**copy.deepcopy(self.map))  # type: ignore
        cloned.set(GlobalId, -1)
        return cloned

    def touch(self):
        self[Touched] = time.time()
