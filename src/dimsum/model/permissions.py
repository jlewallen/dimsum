import dataclasses
import logging
import enum
import copy
from typing import Optional, List, Dict, Any

log = logging.getLogger("dimsum")

EverybodyIdentity = "*"
SystemIdentity = "$system"
OwnerIdentity = "$owner"
CreatorIdentity = "$creator"
AdminIdentity = "$admin"
TrustedIdentity = "$trusted"
AclsKey = "acls"


class Permission:
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"


@dataclasses.dataclass
class Acl:
    perm: str  # TODO phantom type?
    keys: List[str]


@dataclasses.dataclass
class Acls:
    name: str = "<acls>"
    rules: List[Acl] = dataclasses.field(default_factory=list)

    def has(
        self, p: str, identity: str, mappings: Optional[Dict[str, str]] = None
    ) -> bool:
        for rule in self.rules:
            if rule.perm == p:
                if EverybodyIdentity in rule.keys:
                    return True
                mapped_keys = (
                    [self._expand_key(k, mappings) for k in rule.keys]
                    if mappings
                    else rule.keys
                )
                if identity in mapped_keys:
                    return True
        return False

    def _expand_key(self, key: str, mappings: Dict[str, str]) -> str:
        return mappings[key] if key in mappings else key

    def add(self, p: str, identity: str):
        self.rules.append(Acl(p, [identity]))
        return self


@dataclasses.dataclass
class SecurityCheck:
    acls: List[Acls] = dataclasses.field(default_factory=list)

    def passes(self, p: str, identity: str, mapping: Dict[str, str]) -> bool:
        for acl in self.acls:
            if acl.has(p, identity, mapping):
                return True
        return False


def _prepare_acl(d):
    if "py/object" in d:
        c = copy.copy(d)
        del c["py/object"]
        return c
    return d


def _walk_diff(original: Dict[str, Any], diff: Dict[str, Any]):
    log.debug("walking diff: %s", diff)

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
                acls.append(_prepare_acl(value[AclsKey]))
            return {
                key: walk_into(frame, key, value) + acls for key, value in value.items()
            }
        return value

    def walk_into(frame, key, value):
        if frame is None:
            # No more acls to dicsover if the frame is gone.
            return []
        try:
            if isinstance(frame, list) and isinstance(key, str):
                # We need to be indexed to get past one of these.
                return []

            acls = []
            if isinstance(frame, dict) and AclsKey in frame:
                acls.append(_prepare_acl(frame[AclsKey]))

            # If we can't find any more frame using this key then we
            # end. Notice this may contain a just now added acl.
            if isinstance(frame, dict) and key not in frame:
                return acls

            walked = walk(frame[key], value)
            if isinstance(walked, list):
                return acls + walked
            if isinstance(walked, dict):
                return acls + flatten([v for _, v in walked.items()])
            return acls
        except:
            logging.exception("security-check error", exc_info=True)
            logging.error("frame=%s (%s)", frame, type(frame))
            logging.error("key=%s (%s)", key, type(key))
            logging.error("value=%s", value)
            raise

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


def _walk_original(original: Dict[str, Any]):
    def walk(value, path: List[str]):
        if isinstance(value, str):
            return []
        if isinstance(value, list):
            u = {}
            for v, i in enumerate(value):
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


def flatten(l):
    return [item for sl in l for item in sl]
