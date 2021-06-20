from typing import Union

import graphene


class Entity(graphene.ObjectType):
    key = graphene.String()


class Query(graphene.ObjectType):
    entities = graphene.List(
        graphene.NonNull(Entity),
        entity_id=graphene.Argument(type=graphene.ID, required=False),
    )

    def resolve_entities(self, info, entity_id: Union[str, None] = None):
        if entity_id:
            return None
        return []


class EvaluateAttributes:
    name = graphene.String(required=True)
    members = graphene.List(graphene.NonNull(graphene.ID), required=True)


class EvaluatePayload(graphene.InputObjectType, EvaluateAttributes):
    pass


class Evaluate(graphene.Mutation):
    ok = graphene.Boolean()

    class Arguments:
        payload = EvaluatePayload(required=True)

    @staticmethod
    def mutate(self, info, payload):
        session = info.context["session"]
        user = info.context["user"]
        return Evaluate(ok=True)


class Mutation(graphene.ObjectType):
    evaluate = Evaluate.Field()


def create():
    return graphene.Schema(
        query=Query,
        mutation=Mutation,
        types=[],
    )
