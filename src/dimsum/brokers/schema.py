import dataclasses
import logging
import os.path
from typing import Optional

import ariadne
import routing
import starlette.requests

log = logging.getLogger("dimsum")

target = ariadne.ScalarType("Target")


@dataclasses.dataclass
class Credentials:
    username: str
    password: str


process_target_config = ariadne.ScalarType("ProcessTargetConfig")
http_target_config = ariadne.ScalarType("HttpTargetConfig")
target_configuration = ariadne.ScalarType("TargetConfiguration")


@dataclasses.dataclass
class ProcessTargetConfig:
    command: str


@dataclasses.dataclass
class HttpTargetConfig:
    url: str


@dataclasses.dataclass
class TargetConfiguration:
    name: str
    process: Optional[ProcessTargetConfig]
    http: Optional[HttpTargetConfig]


query = ariadne.QueryType()


@query.field("targets")
async def resolve_targets(_, info):
    broker = info.context.broker
    return broker.get_targets()


mutation = ariadne.MutationType()


def make_target_configuration(process=None, http=None, **kwargs):
    process_config = ProcessTargetConfig(**process) if process else None
    http_config = HttpTargetConfig(**http) if http else None
    return TargetConfiguration(process=process_config, http=http_config, **kwargs)


@mutation.field("provision")
async def provision(obj, info, config):
    tc = make_target_configuration(**config)
    log.info("ariadne:provision: config=%s", tc)
    if tc.process:
        return routing.ProcessTarget(name=tc.name, command=tc.process.command)
    raise NotImplementedError


def create():
    for path in ["src/dimsum/brokers/broker.graphql", "broker.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(type_defs, [query, mutation])
    raise Exception("unable to find broker.graphql")


@dataclasses.dataclass
class AriadneContext:
    broker: routing.Broker
    request: starlette.requests.Request


def context(broker: routing.Broker):
    def wrap(request):
        log.debug("ariadne:context %s", request)
        return AriadneContext(broker=broker, request=request)

    return wrap
