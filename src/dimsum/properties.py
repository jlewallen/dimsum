import time
import re

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

    def set(self, key: str, value):
        if key in self.__dict__:
            self.__dict__[key].set(value)
        else:
            if isinstance(value, Property):
                self.__dict__[key] = value
            else:
                self.__dict__[key] = Property(value)

    def update(self, changes):
        self.__dict__.update(changes)

    def replace(self, **replacing):
        self.__dict__ = replacing

    def __contains__(self, key):
        return key in self.__dict__

    def __getitem__(self, key):
        if key in self.__dict__:
            return self.__dict__[key].value
        return None

    def __setitem__(self, key, value):
        self.set(key, value)

    def clone(self):
        return PropertyMap(self.map)

    def __str__(self):
        return "properties<{0}>".format(self.map)

    def __repr__(self):
        return str(self)


Name = "name"
Desc = "desc"
Created = "created"
Touched = "touched"


class Details(PropertyMap):
    def __init__(self, name: str = "", desc: str = None, **kwargs):
        super().__init__(**kwargs)
        self.set(Name, name)
        self.set(Desc, desc if desc else name)
        self.set(Created, time.time())
        self.set(Touched, time.time())

    @property
    def name(self) -> str:
        return self[Name]

    @name.setter
    def name(self, value: str):
        self.set(Name, value)

    def clone(self):
        return Details(self.name, desc=self.desc)

    def touch(self):
        self.touched = time.time()
