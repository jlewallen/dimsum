from typing import List

from model.inflection import infl
from model.game import (
    Reply,
    Action,
    Unknown,
    DynamicFailure,
    Success,
    Failure,
    Universal,
)
from model.crypto import Identity
from model.kinds import Kind
from model.permissions import (
    Acls,
    Permission,
    SystemIdentity,
    OwnerIdentity,
    CreatorIdentity,
    AdminIdentity,
    TrustedIdentity,
    generate_security_check_from_json_diff,
    find_all_acls,
)

from model.properties import (
    Common,
    Map,
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
    MissingEntityException,
    generate_entity_identity,
    Version,
    EntityRef,
    EntityFrozen,
    find_entity_area,
    find_entity_area_maybe,
    cleanup_entity,
    set_entity_keys_provider,
    set_entity_identities_provider,
    set_entity_cleanup_handler,
    set_entity_describe_handler,
    set_entity_area_provider,
    CompiledJson,
)
from model.entity import Serialized  # Can we move these?
from model.world import World, WorldKey, WelcomeAreaKey
from model.events import event, Event, StandardEvent, get_all_events, TickEvent
from model.visual import Comms, NoopComms, Renderable, Updated, String
from model.reply import (
    Activity,
    ObservedEntity,
    HoldingActivity,
    Observation,
    observe_entity,
)
from model.hooks import ManagedHooks, All, ExtendHooks
from model.context import Ctx, get, TryMaterialize
from model.finders import (
    ItemFinder,
    FindNone,
    FindStaticItem,
    FindObjectByGid,
    FindCurrentArea,
    ItemFactory,
)
from model.well_known import (
    materialize_well_known_entity,
    get_well_known_key,
    set_well_known_key,
)

import model.hooks as hooks

__all__: List[str] = [
    "Ctx",
    "TryMaterialize",
    "get",
    "EntityFrozen",
    "Reply",
    "Action",
    "Unknown",
    "DynamicFailure",
    "Success",
    "Failure",
    "Universal",
    "Identity",
    "Kind",
    "Entity",
    "Version",
    "EntityRef",
    "Serialized",
    "EntityClass",
    "RootEntityClass",
    "Scope",
    "Registrar",
    "World",
    "WorldKey",
    "WelcomeAreaKey",
    "event",
    "Event",
    "StandardEvent",
    "Kind",
    "Common",
    "Map",
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
    "ExtendHooks",
    "TickEvent",
    "ObservedEntity",
    "Observation",
    "HoldingActivity",
    "hooks",
    "find_entity_area",
    "find_entity_area_maybe",
    "generate_entity_identity",
    "set_entity_keys_provider",
    "set_entity_identities_provider",
    "set_entity_cleanup_handler",
    "set_entity_describe_handler",
    "set_entity_area_provider",
    "materialize_well_known_entity",
    "get_well_known_key",
    "set_well_known_key",
    "cleanup_entity",
    "observe_entity",
    "get_all_events",
    "infl",
    "ItemFinder",
    "FindNone",
    "FindStaticItem",
    "FindObjectByGid",
    "ItemFactory",
    "FindCurrentArea",
    "Acls",
    "Permission",
    "find_all_acls",
    "SystemIdentity",
    "OwnerIdentity",
    "CreatorIdentity",
    "AdminIdentity",
    "CompiledJson",
    "MissingEntityException",
]
