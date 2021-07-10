import base64
import hashlib
import logging
import os
from typing import List, Optional

from model import Entity, Scope

log = logging.getLogger("dimsum.scopes")


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
            if actual_key == key:
                return {
                    "key": self.ourselves.key,
                }
        return None
