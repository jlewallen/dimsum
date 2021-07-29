from typing import Any, Dict, List, Optional, TextIO

from gql import Client, gql
from gql.transport.aiohttp import AIOHTTPTransport

from loggers import get_logger
from model import Entity, CompiledJson, Serialized

from .core import EntityStorage

log = get_logger("dimsum.storage")


class HttpStorage(EntityStorage):
    def __init__(self, url: str, token: Optional[str] = None):
        super().__init__()
        self.url = url
        self.token = token

    def _get_headers(self):
        if self.token:
            return {"Authorization": "Bearer %s" % (self.token,)}
        return {}

    def session(self):
        return Client(
            transport=AIOHTTPTransport(url=self.url, headers=self._get_headers()),
            fetch_schema_from_transport=True,
        )

    async def number_of_entities(self):
        async with self.session() as session:
            query = gql("query { size }")
            response = await session.execute(query)
            return response["size"]

    async def update(self, updates: Dict[str, CompiledJson]) -> Dict[str, CompiledJson]:
        async with self.session() as session:
            query = gql(
                """
        mutation Update($entities: [EntityDiff!]!) {
            update(entities: $entities) {
                affected { key serialized }
            }
        }
    """
            )
            entities = [
                {"key": key, "serialized": update.text}
                for key, update in updates.items()
            ]
            response = await session.execute(
                query, variable_values={"entities": entities}
            )

            affected = response["update"]["affected"]
            return {row["key"]: row["serialized"] for row in affected}

    async def load_by_gid(self, gid: int):
        async with self.session() as session:
            query = gql(
                "query entityByGid($gid: Int!) { entitiesByGid(gid: $gid) { key serialized } }"
            )
            response = await session.execute(query, variable_values={"gid": gid})
            serialized_entities = response["entitiesByGid"]
            if len(serialized_entities) == 0:
                return []
            return [Serialized(**row) for row in serialized_entities]

    async def load_by_key(self, key: str):
        async with self.session() as session:
            query = gql(
                "query entityByKey($key: Key!) { entitiesByKey(key: $key) { key serialized }}"
            )
            response = await session.execute(query, variable_values={"key": key})
            serialized_entities = response["entitiesByKey"]
            if len(serialized_entities) == 0:
                return []
            return [Serialized(**row) for row in serialized_entities]

    def __repr__(self):
        return "Http<%s>" % (self.url,)

    def __str__(self):
        return "Http<%s>" % (self.url,)
