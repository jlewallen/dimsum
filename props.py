import time
import re


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


class PropertyMap:
    def __init__(self, **kwargs):
        self.__dict__ = kwargs

    @property
    def map(self):
        return self.__dict__

    @property
    def keys(self):
        return self.__dict__.keys()

    def keys_matching(self, pattern: str):
        return [k for k in self.__dict__.keys() if re.match(pattern, k)]

    def set(self, key, value):
        self.__dict__[key] = value

    def update(self, changes):
        self.__dict__.update(changes)

    def replace(self, replacing):
        self.__dict__ = replacing

    def clone(self):
        return PropertyMap(self.map)


class Details(PropertyMap):
    def __init__(self, name: str = "", **kwargs):
        super().__init__(**kwargs)
        self.name = name
        self.desc = kwargs["desc"] if "desc" in kwargs else name
        self.presence = ""
        self.created = time.time()
        self.touched = time.time()

    @staticmethod
    def from_base(base):
        details = Details()
        details.__dict__ = base
        details.created = time.time()
        details.touched = time.time()
        return details

    @staticmethod
    def from_map(map):
        details = Details()
        details.__dict__ = map
        return details

    def to_base(self):
        base = self.map.copy()
        if "created" in base:
            del base["created"]
        if "touched" in base:
            del base["touched"]
        return base

    def clone(self):
        return Details(self.name, desc=self.desc)

    def when_eaten(self):
        return self.map["eaten"] if "eaten" in self.map else False

    def when_drank(self):
        return self.map["drank"] if "drank" in self.map else False

    def touch(self):
        self.touched = time.time()

    def __str__(self):
        return str(self.map)
