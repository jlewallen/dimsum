import logging
import ariadne
import os.path

import model.world as world
import model.domains as domains
import model.game as game

import serializing
import grammars
import storage

log = logging.getLogger("dimsum")

entity_scalar = ariadne.ScalarType("Entity")


@entity_scalar.serializer
def serialize_entity(value):
    log.debug("ariadne:entity")
    return serializing.serialize(value, indent=True, reproducible=True)


reply_scalar = ariadne.ScalarType("Reply")


@reply_scalar.serializer
def serialize_reply(value):
    log.debug("ariadne:reply")
    return serializing.serialize(value, indent=True, reproducible=True)


query = ariadne.QueryType()


@query.field("size")
async def resolve_size(_, info):
    domain = info.context.domain
    store = await domain.store.number_of_entities()
    registrar = domain.registrar.number_of_entities()
    log.info("ariadne:size store=%d registrar=%d", store, registrar)
    if registrar > store:
        return registrar
    return store


@query.field("world")
async def resolve_world(obj, info):
    domain = info.context.domain
    log.info("ariadne:world")
    return serialize_entity(domain.world)


@query.field("entities")
async def resolve_entities(obj, info, key):
    domain = info.context.domain
    log.info("ariadne:entities key=%s", key)
    entities = []
    if domain.registrar.contains(key):
        entities = [domain.registrar.find_by_key(key)]
    else:
        loaded = await domain.store.load_by_key(key)
        if loaded:
            entities = [loaded]

    log.info("ariadne:entities entities=%s", entities)
    return [serialize_entity(e) for e in entities]


class Evaluation:
    def __init__(self, reply, entities):
        super().__init__()
        self.reply = reply
        self.entities = entities


@query.field("language")
async def resolve_language(obj, info, criteria):
    domain = info.context.domain
    log.info("ariadne:language criteria=%s", criteria)

    l = grammars.create_parser()
    w = await domain.materialize(world.Key)
    assert w
    player = await domain.materialize(criteria["evaluator"])
    assert player
    tree, create_evaluator = l.parse(criteria["text"].strip())
    tree_eval = create_evaluator(w, player)
    action = tree_eval.transform(tree)
    reply = await domain.perform(action, player)

    log.info("reply: %s", reply)
    await domain.save()

    return Evaluation(
        serialize_reply(reply),
        [serialize_entity(e) for e in domain.registrar.entities.values()],
    )


evaluation = ariadne.ObjectType("Evaluation")


@evaluation.field("reply")
async def resolve_evaluation_reply(obj, info):
    log.info("evaluation:reply %s", obj)
    return None


@evaluation.field("entities")
async def resolve_evaluation_entities(obj, info):
    log.info("evaluation:entities %s", obj)
    return []


def create():
    for path in ["src/dimsum/schema.graphql", "schema.graphql"]:
        if os.path.exists(path):
            type_defs = ariadne.load_schema_from_path(path)
            return ariadne.make_executable_schema(type_defs, query)
    raise Exception("unable to find schema.graphql")


class AriadneContext:
    def __init__(self, domain):
        super().__init__()
        self.domain = domain


def context(request):
    log.info("ariadne:context %s", request)
    return AriadneContext(domains.Domain())
