import dataclasses
import json
import logging
import os
import os.path
import shortuuid
from typing import Dict, List, Optional

from domains import Domain
from storage import *

log = logging.getLogger("dimsum.config")


@dataclasses.dataclass
class Persistence:
    read: List[str]
    write: List[str]

    def get_store_from_url(self, url: str, cache: Dict[str, EntityStorage]):
        if url not in cache:
            log.info("storage-url: %s", url)
            if url.startswith("http"):
                cache[url] = HttpStorage(url)
            else:
                cache[url] = SqliteStorage(url)
        return cache[url]

    def get_stores_from_url(self, urls: List[str], cache: Dict[str, EntityStorage]):
        return [self.get_store_from_url(url, cache) for url in urls]

    def make_store(self):
        if not self.read or not self.write:
            raise ConfigurationException("at least one read and write url is required")
        cache: Dict[str, EntityStorage] = {}
        read = Prioritized(self.get_stores_from_url(self.read, cache))
        write = All(self.get_stores_from_url(self.write, cache))
        return Separated(read, write)


@dataclasses.dataclass
class Configuration:
    persistence: Persistence
    session_key: str

    def make_domain(self, handlers=None):
        store = self.persistence.make_store()
        log.info("store = %s", store)
        return Domain(store=store, handlers=handlers)


class ConfigurationException(Exception):
    pass


def make_configuration(persistence=None, **kwargs):
    return Configuration(persistence=Persistence(**persistence), **kwargs)


def get(path: Optional[str]) -> Configuration:
    if path is None:
        return symmetrical(":memory:")
    if os.path.exists(path):
        with open(path, "r") as f:
            cfg = json.loads(f.read())  # TODO Parsing logging config JSON
            return make_configuration(**cfg)
    raise ConfigurationException("file not found")


def generate_session_key() -> str:
    return shortuuid.uuid()


def symmetrical(file: str, session_key: Optional[str] = None, **kwargs):
    return Configuration(
        persistence=Persistence(read=[file], write=[file]),
        session_key=session_key or generate_session_key(),
    )
