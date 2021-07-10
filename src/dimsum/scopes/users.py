import base64
import hashlib
import logging
import os
import jwt
from typing import List, Optional, Tuple, Dict

from model import Entity, Scope

log = logging.getLogger("dimsum.scopes")

invite_session_key = base64.b64encode(os.urandom(32)).decode("utf-8")


class Usernames(Scope):
    def __init__(self, users: Optional[Dict[str, str]] = None, **kwargs):
        super().__init__(**kwargs)
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


class Auth(Scope):
    def __init__(self, password: Optional[List[str]] = None, **kwargs):
        super().__init__(**kwargs)
        self.password = password if password else None

    def change(self, password: str):
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        self.password = [
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(key).decode("utf-8"),
        ]
        self.ourselves.touch()
        log.info("%s: password changed %s", self.ourselves.key, self.ourselves)

    def try_password(self, password: str, **kwargs):
        if self.password:
            salt_encoded, key_encoded = self.password
            salt = base64.b64decode(salt_encoded)
            key = base64.b64decode(key_encoded)
            actual_key = hashlib.pbkdf2_hmac(
                "sha256", password.encode("utf-8"), salt, 100000
            )
            return actual_key == key
        return None

    def invite(self, password: str) -> Tuple[str, str]:
        token = {"creator": self.ourselves.key}
        invite_token = jwt.encode(token, invite_session_key, algorithm="HS256")
        url = "http://127.0.0.1:8082/invite?token=%s" % (invite_token,)
        log.info("invite: %s", url)
        return url, invite_token
