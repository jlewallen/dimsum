import base64
import hashlib
import logging
import os
import jwt
from typing import List, Optional, Tuple, Dict

from model import Entity, Scope, Acls

log = logging.getLogger("dimsum.scopes")

invite_session_key = base64.b64encode(os.urandom(32)).decode("utf-8")


class Usernames(Scope):
    def __init__(self, users: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.acls = Acls.system_writes()
        self.users = users if users else {}


async def register_username(entity: Entity, username: str, key: str):
    with entity.make(Usernames) as usernames:
        assert key not in usernames.users
        usernames.users[username] = key
        entity.touch()


async def lookup_username(entity: Entity, username: str) -> Optional[str]:
    with entity.make_and_discard(Usernames) as usernames:
        if username in usernames.users:
            return usernames.users[username]
    return None


def secure_password(password: str) -> Tuple[str, str]:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return (
        base64.b64encode(salt).decode("utf-8"),
        base64.b64encode(key).decode("utf-8"),
    )


def try_password(secured: Tuple[str, str], password: str) -> bool:
    salt_encoded, key_encoded = secured
    salt = base64.b64decode(salt_encoded)
    key = base64.b64decode(key_encoded)
    actual_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return actual_key == key


class Auth(Scope):
    def __init__(self, password: Optional[Tuple[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.acls = Acls.system_writes()
        self.password = password if password else None

    def change(self, password: str):
        self.password = secure_password(password)
        self.ourselves.touch()
        log.info("%s: password changed %s", self.ourselves.key, self.ourselves)

    def try_password(self, password: str, **kwargs):
        if self.password:
            return try_password(self.password, password)
        return None

    def invite(self, password: str) -> Tuple[str, str]:
        token = {"creator": self.ourselves.key, "password": secure_password(password)}
        invite_token = jwt.encode(token, invite_session_key, algorithm="HS256")
        url = "http://127.0.0.1:8082/invite?token=%s" % (invite_token,)
        log.info("invite: %s", url)
        return url, invite_token


class Groups(Scope):
    def __init__(self, memberships: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.acls = Acls.system_writes()
        self.memberships = memberships if memberships else []
