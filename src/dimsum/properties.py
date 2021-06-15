from typing import Dict

import abc
import logging
import time
import re

log = logging.getLogger("dimsum")

Created = "created"
Touched = "touched"
Desc = "desc"
Worn = "worn"
Opened = "opened"
Eaten = "eaten"
Drank = "drank"


class FieldMergeStrategy:
    def __init__(self, name: str):
        self.name = name

    def merge(self, old_value, new_value):
        return old_value


class SumFields(FieldMergeStrategy):
    def merge(self, old_value, new_value):
        if not old_value:
            return new_value
        if not new_value:
            return old_value
        return float(old_value) + float(new_value)


def merge_dictionaries(left, right, fields):
    merged = {}
    for field in fields:
        old_value = left[field.name] if field.name in left else None
        new_value = right[field.name] if field.name in right else None
        merged[field.name] = field.merge(old_value, new_value)
    return merged


class Property:
    def __init__(self, value=None, **kwargs):
        self.__dict__ = kwargs
        self.value = value

    def set(self, value):
        self.value = value


class Map:
    def __init__(self, map: Dict[str, Property] = None):
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
                self.map[key] = Property(value)

    def update(self, changes):
        self.map.update(changes)

    def replace(self, **replacing):
        self.map = replacing

    def clone(self):
        return Map(self.map)

    def __str__(self):
        return "Map<{0}>".format(self.map)

    def __repr__(self):
        return str(self)


Name = "name"
Desc = "desc"
Created = "created"
Touched = "touched"
Owner = "owner"
Password = "password"


class Common(Map):
    def __init__(self, name: str = None, desc: str = None, **kwargs):
        super().__init__(kwargs)
        self.set(Name, name)
        self.set(Desc, desc if desc else name)
        self.set(Created, time.time())
        self.set(Touched, time.time())
        self.set(Owner, None)

    @property
    def name(self) -> str:
        return self[Name]

    @name.setter
    def name(self, value: str):
        self.set(Name, value)

    @property
    def desc(self) -> str:
        return self[Desc]

    @name.setter
    def desc(self, value: str):
        self.set(Desc, value)

    @property
    def owner(self):
        return self[Owner]

    @owner.setter
    def owner(self, value):
        assert value
        log.info("change-owner {0}".format(value))
        self.set(Owner, value)

    def clone(self) -> "Common":
        return Common(**self.map)  # type: ignore

    def touch(self):
        self.touched = time.time()
