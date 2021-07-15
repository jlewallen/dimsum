import dataclasses
import logging
import enum
import copy
import pprint
import functools
from itertools import groupby
from typing import Optional, List, Dict, Any, Union

log = logging.getLogger("dimsum")


class SecurityMappings:
    Everybody = "*"
    System = "$system"
    Owner = "$owner"
    Creator = "$creator"
    Admin = "$admin"
    Trusted = "$trusted"


AclsKey = "acls"


class Permission:
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclasses.dataclass(frozen=True)
class SecurityContext:
    identity: str
    mappings: Dict[str, str] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Acl:
    perm: str  # TODO phantom type?
    keys: List[str]


@dataclasses.dataclass
class Acls:
    rules: List[Union[Acl, Dict[str, Any]]] = dataclasses.field(default_factory=list)

    @property
    def hydrated(self) -> List[Acl]:
        return self._rules

    @property
    def _rules(self) -> List[Acl]:
        def prepare(v: Union[Acl, Dict[str, Any]]) -> Acl:
            if isinstance(v, Acl):
                return v
            c = copy.copy(v)
            del c["py/object"]
            return Acl(**c)

        return [prepare(acl) for acl in self.rules]

    def has(self, p: str, sc: SecurityContext) -> bool:
        for rule in self._rules:
            if rule.perm == p:
                if SecurityMappings.Everybody in rule.keys:
                    return True
                mapped_keys = (
                    [self._expand_key(k, sc.mappings) for k in rule.keys]
                    if sc.mappings
                    else rule.keys
                )
                if sc.identity in mapped_keys:
                    return True
        return False

    def _expand_key(self, key: str, mappings: Dict[str, str]) -> str:
        return mappings[key] if key in mappings else key

    def add(self, p: str, identity: str):
        self.rules.append(Acl(p, [identity]))
        return self

    def __repr__(self) -> str:
        return str(self)

    def __str__(self) -> str:
        grouped = {
            key: flatten([g.keys for g in group])
            for key, group in groupby(self._rules, lambda r: r.perm)
        }
        return f"Acls<{grouped}>"

    @staticmethod
    def make_permissions(default_readers=None, default_writers=None):
        return

    @staticmethod
    def owner_writes() -> "Acls":
        return Acls().add(Permission.WRITE, SecurityMappings.Owner)

    @staticmethod
    def everybody_writes() -> "Acls":
        return Acls().add(Permission.WRITE, SecurityMappings.Everybody)

    @staticmethod
    def system_writes() -> "Acls":
        return Acls().add(Permission.WRITE, SecurityMappings.System)


@dataclasses.dataclass
class SecurityCheckException(Exception):
    permission: str
    context: SecurityContext
    acls: Dict[str, Acls]

    def __str__(self):
        return """Permission: {0}

Context:
{1}

Acls:
{2}
""".format(
            self.permission,
            self.context,
            pprint.pformat(self.acls),
        )


@dataclasses.dataclass
class SecurityCheck:
    acls: Dict[str, Acls] = dataclasses.field(default_factory=dict)

    async def verify(self, p: str, sc: SecurityContext):
        for key, acl in self.acls.items():
            if acl.has(p, sc):
                return True
        raise SecurityCheckException(p, sc, self.acls)


def _prepare_acl(d):
    if "py/object" in d:
        c = copy.copy(d)
        del c["py/object"]
        return c
    return d


def _walk_original(original: Dict[str, Any]):
    def walk(value, path: List[str]):
        if isinstance(value, str):
            return []
        if isinstance(value, list):
            u = {}
            for i, v in enumerate(value):
                u.update(walk(v, path + [str(i)]))
            return u
        if isinstance(value, dict):
            u = {}
            if AclsKey in value:
                u[".".join(path)] = Acls(**_prepare_acl(value[AclsKey]))
            for key, value in value.items():
                u.update(walk(value, path + [key]))
            return u
        return {}

    return walk(original, [])


def find_all_acls(original: Dict[str, Any]) -> Dict[str, Acls]:
    return _walk_original(original)


def _walk_diff(diff: Dict[str, Any]):
    def walk(value, path: List[str]):
        log.debug("walking diff: %s", value)

        if value is None:
            return {}
        if isinstance(value, str):
            return {".".join(path): True}
        if isinstance(value, int) or isinstance(value, float):
            return {".".join(path): True}
        if isinstance(value, list) or isinstance(value, tuple):
            rv = {}
            for key, v in enumerate(value):
                rv.update(walk(v, path + [str(key)]))
            return rv
        if isinstance(value, dict):
            rv = {}
            if "py/object" in value:
                return {".".join(path): True}
            for key, v in value.items():
                rv.update(walk(v, path + [str(key)]))
            return rv

        log.warning("unhandled: %s %s", type(value), value)

        return {}

    return walk(diff, [])


def generate_security_check_from_json_diff(
    original: Dict[str, Any], diff: Dict[str, Any]
) -> SecurityCheck:
    """
    Walks the given jsondiff and pulls Acl objects from the original
    json along the way.
    """
    acls = find_all_acls(original)
    log.debug("security-check: acls=%s", acls)
    modified_nodes = _walk_diff(diff)
    log.debug("security-check: %s=%s", diff, modified_nodes)
    for node in modified_nodes.keys():
        matched: Dict[str, Acls] = {}
        for key, child in acls.items():
            if key and node.startswith(key + ".") or not key and node.startswith(key):
                matched[key] = child
        log.info("security-check(%s): %s", node, matched)
    return SecurityCheck(matched)


def flatten(l):
    return [item for sl in l for item in sl]
