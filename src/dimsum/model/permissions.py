import dataclasses
import logging
import enum
from typing import Optional, List, Dict, Any

log = logging.getLogger("dimsum")

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


@dataclasses.dataclass
class SecurityCheck:
    acls: List[Acl] = dataclasses.field(default_factory=list)


AclsKey = "acls"


def _walk_diff(original: Dict[str, Any], diff: Dict[str, Any]):
    log.info("walking diff: %s", diff)

    def prepare_acl(d):
        del d["py/object"]
        return d

    def walk(frame, value):
        # Maybe we only consider the Acls nearest to the editing
        # position, or should we consider all of them. It's easier
        # to just do all of them for now.
        if isinstance(value, str):
            return []
        if isinstance(value, list):
            return []
        if isinstance(value, dict):
            acls = []
            if AclsKey in value:
                acls.append(prepare_acl(value[AclsKey]))
            return {
                key: walk_into(frame, key, value) + acls for key, value in value.items()
            }
        return value

    def walk_into(frame, key, value):
        acls = []
        if AclsKey in frame:
            acls.append(prepare_acl(frame[AclsKey]))
        walked = walk(frame[key], value)
        if isinstance(walked, list):
            return acls + walked
        if isinstance(walked, dict):
            return acls + flatten([v for _, v in walked.items()])
        return acls

    walked = walk(original, diff)
    acl_maps = flatten([v for _, v in walked.items()])
    return [Acls(**v) for v in acl_maps]


def generate_security_check_from_json_diff(
    original: Dict[str, Any], diff: Dict[str, Any]
) -> SecurityCheck:
    """
    Walks the given jsondiff and pulls Acl objects from the original
    json along the way.
    """
    return SecurityCheck(_walk_diff(original, diff))


def flatten(l):
    return [item for sl in l for item in sl]
