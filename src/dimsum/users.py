from typing import Tuple, List

import os
import hashlib
import base64

import entity


class Auth(entity.Scope):
    def __init__(self, password: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.password = password if password else None

    def change(self, password: str):
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
        self.password = [
            base64.b64encode(salt).decode("utf-8"),
            base64.b64encode(key).decode("utf-8"),
        ]

    def try_password(self, password: str, **kwargs):
        if not self.password:
            raise Exception("unauthenticated")
        saltEncoded, keyEncoded = self.password
        salt = base64.b64decode(saltEncoded)
        key = base64.b64decode(keyEncoded)
        actual_key = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, 100000
        )

        return {
            "key": self.ourselves.key,
        }
