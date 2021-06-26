from typing import List, Dict, Optional

import logging
import dataclasses
import os
import os.path
import json

import model.domains as domains

import storage

log = logging.getLogger("dimsum.config")


@dataclasses.dataclass
class Persistence:
    read: List[str]
    write: List[str]

    def get_store_from_url(self, url: str, cache: Dict[str, storage.EntityStorage]):
        if url not in cache:
            log.info("storage-url: %s", url)
            if url.startswith("http"):
                cache[url] = storage.HttpStorage(url)
            else:
                cache[url] = storage.SqliteStorage(url)
        return cache[url]

    def get_stores_from_url(
        self, urls: List[str], cache: Dict[str, storage.EntityStorage]
    ):
        return [self.get_store_from_url(url, cache) for url in urls]

    def make_store(self):
        cache: Dict[str, storage.EntityStorage] = {}
        read = storage.Prioritized(self.get_stores_from_url(self.read, cache))
        write = storage.All(self.get_stores_from_url(self.write, cache))
        return storage.Separated(read, write)


@dataclasses.dataclass
class Configuration:
    persistence: Persistence
    session_key: str

    def make_domain(self):
        store = self.persistence.make_store()
        log.info("store = %s", store)
        return domains.Domain(store=store)


class ConfigurationException(Exception):
    pass


def make_configuration(persistence=None, **kwargs):
    return Configuration(persistence=Persistence(**persistence), **kwargs)


def get(path: Optional[str]) -> Configuration:
    if path is None:
        return symmetrical(":memory:")
    if os.path.exists(path):
        with open(path, "r") as f:
            return make_configuration(**json.loads(f.read()))
    raise ConfigurationException("file not found")


def symmetrical(file: str, session_key: str = None, **kwargs):
    return Configuration(
        persistence=Persistence(read=[file], write=[file]),
        session_key=session_key or "terrible-session-key",
    )
