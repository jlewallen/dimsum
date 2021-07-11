export interface ObservedItem {
    item: EntityRef;
}

export interface ObservedPerson {
    activities: never[];
    alive: EntityRef;
}

export interface Direction {
    compass: string;
}

export interface AreaRoute {
    area: EntityRef;
    direction?: Direction;
}

export interface AreaObservation {
    interactive: false;
    information: false;
    where: EntityRef;
    people: ObservedPerson[];
    items: ObservedItem[];
    routes: AreaRoute[];
}

export interface DetailedObservation {
    interactive: false;
    information: false;
    person: ObservedPerson;
    item: ObservedItem;
}

export interface InteractiveReply {
    interactive: boolean;
    information: false;
}

export interface Universal {
    interactive: false;
    information: false;
    f: string;
    kwargs: Record<string, any>;
}

export interface ReplResponse {
    reply:
        | { interactive: false; information: boolean; entities?: { key: string; serialized: string }[] }
        | AreaObservation
        | EntitiesObservation
        | DetailedObservation
        | PersonalObservation
        | Success
        | Failure
        | InteractiveReply
        | Universal;
}

export type PropertyMap = { [index: string]: any };
export type UpdateEntityDetailsPayload = PropertyMap;
export type UpdateEntityBehaviorPayload = PropertyMap;

export interface Property<T> {
    value: T;
}

export interface Properties {
    name: Property<string>;
    desc: Property<string>;
}

export type EntityKey = string;

export type Klass = Record<string, string>;

export interface EntityRef {
    key: string;
    klass: Klass;
    name: string;
}

export interface Behavior {
    "py/object": string;
    lua: string | null;
    python: string | null;
    logs: string[];
}

export type Behaviors = { [index: string]: Behavior };

export interface Occupyable {
    occupied: EntityRef[];
}

export interface Containing {
    holding: EntityRef[];
}

export interface Visibility {
    visible: {
        hard_to_see: boolean;
        hidden: never;
        observations: never;
    };
}

export interface Exit {
    area: EntityRef;
}

export interface Kind {
    identity: unknown;
}

export interface Carryable {
    quantity: number;
    kind: Kind;
}

export interface Encyclopedia {
    body: string;
}

export interface Entity {
    key: string;
    url: string;
    klass: Klass;
    creator: EntityRef;
    props: { map: Properties };
    chimeras: {
        behaviors: { behaviors: { map: Behaviors } };
        containing?: Containing;
        encyclopedia?: Encyclopedia;
        occupyable?: Occupyable;
        visibility?: Visibility;
        carryable?: Carryable;
        exit?: Exit;
    };
}

export interface Person extends Entity {
    ignored: boolean;
}

export interface Animal extends Entity {
    ignored: boolean;
}

export interface Area extends Entity {
    ignored: boolean;
}

export interface Item extends Entity {
    ignored: boolean;
}

export class Reply {}

export interface Success extends Reply {
    interactive: false;
    information: false;
    message: string;
}

export interface Failure extends Reply {
    interactive: false;
    information: false;
    message: string;
}

export interface EntitiesObservation {
    interactive: false;
    information: false;
    entities: EntityRef[];
}

export interface PersonalObservation {
    interactive: false;
    information: false;
    who: ObservedPerson;
}
