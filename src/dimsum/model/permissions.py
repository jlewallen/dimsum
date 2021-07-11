import dataclasses
import logging
import enum
from typing import Optional, List, Dict

EverybodyIdentity = "*"


class Permission(enum.Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclasses.dataclass
class Acl:
    perm: Permission
    keys: List[str]


@dataclasses.dataclass
class Acls:
    name: str = "<acls>"
    rules: List[Acl] = dataclasses.field(default_factory=list)

    def has(self, p: Permission, identity: str, **kwargs) -> bool:
        for rule in self.rules:
            if rule.perm == p:
                if identity in rule.keys or EverybodyIdentity in rule.keys:
                    return True
        return False

    def add(self, p: Permission, identity: str):
        self.rules.append(Acl(p, [identity]))
        return self
