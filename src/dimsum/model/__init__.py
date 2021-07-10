from typing import List

from model.inflection import infl
from model.game import Reply, Action, Unknown, DynamicFailure, Success, Failure
from model.crypto import Identity
from model.kinds import Kind
from model.properties import (
    Common,
    Map,
    SumFields,
    merge_dictionaries,
)
from model.conditions import Condition, AlwaysTrue
from model.properties import (
    Worn,
    Eaten,
    Drank,
    Opened,
)  # TODO Deprecated
from model.entity import (
    Scope,
    Entity,
    EntityClass,
    RootEntityClass,
    Registrar,
    generate_identity,
    Version,
    EntityRef,
    EntityProxy,
    install_hooks,
    cleanup,
    EntityFrozen,
    keys,
    identities,
)
from model.entity import Hooks, Keys, EntityUpdate, Serialized  # Can we move these?
from model.world import World, Key, Welcoming
from model.events import event, Event, StandardEvent, get_all, TickEvent
from model.visual import Comms, NoopComms, Renderable, Updated, String
from model.reply import Activity, ObservedEntity, HoldingActivity, Observation, observe
from model.hooks import ManagedHooks, All, ExtendHooks
from model.context import Ctx, get

import model.hooks as hooks

__all__: List[str] = [
    "Ctx",
    "get",
    "Hooks",
    "install_hooks",
    "EntityFrozen",
    "Reply",
    "Action",
    "Unknown",
    "DynamicFailure",
    "Success",
    "Failure",
    "Identity",
    "Kind",
    "generate_identity",
    "Entity",
    "Version",
    "EntityRef",
    "EntityProxy",
    "Keys",
    "EntityUpdate",
    "Serialized",
    "EntityClass",
    "RootEntityClass",
    "Scope",
    "Registrar",
    "World",
    "Key",
    "event",
    "Event",
    "StandardEvent",
    "Kind",
    "Common",
    "Map",
    "SumFields",
    "merge_dictionaries",
    "Worn",
    "Eaten",
    "Drank",
    "Opened",
    "Comms",
    "NoopComms",
    "Renderable",
    "String",
    "Updated",
    "Activity",
    "Condition",
    "AlwaysTrue",
    "All",
    "ManagedHooks",
    "get_all",
    "cleanup",
    "ExtendHooks",
    "TickEvent",
    "Welcoming",
    "ObservedEntity",
    "Observation",
    "HoldingActivity",
    "observe",
    "hooks",
    "keys",
    "identities",
    "infl",
]
