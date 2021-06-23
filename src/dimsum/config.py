from typing import List, Dict, Optional

import dataclasses
import logging
import os
import os.path
import json

import storage


@dataclasses.dataclass
class Configuration:
    database: str
    session_key: str

    def make_store(self):
        return storage.SqliteStorage(self.database)


class ConfigurationException(Exception):
    pass


def get(path: Optional[str]) -> Configuration:
    if path is None:
        path = "dimsum.conf"
    if os.path.exists(path):
        with open(path, "r") as f:
            return Configuration(**json.loads(f.read()))
    raise ConfigurationException("file not found")
