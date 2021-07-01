import { Config } from "@/config";

export interface OurRequestInfo {
    url: string;
    method?: string;
    data?: any;
    headers?: { [index: string]: string };
}

export interface ReplPayload {
    command: string;
}

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
    where: EntityRef;
    people: ObservedPerson[];
    items: ObservedItem[];
    routes: AreaRoute[];
}

export interface DetailedObservation {
    person: ObservedPerson;
    item: ObservedItem;
}

export interface ReplResponse {
    reply: AreaObservation | EntitiesObservation | DetailedObservation | PersonalObservation | Success | Failure;
}

export type PropertyMap = { [index: string]: any };
export type UpdateEntityDetailsPayload = PropertyMap;
export type UpdateEntityBehaviorPayload = PropertyMap;

export async function graphql<T>(query: string): Promise<T> {
    const response = await fetch(Config.baseUrl, {
        method: "POST",
        mode: "cors",
        headers: Object.assign({
            "Content-Type": "application/json",
        }),
        body: JSON.stringify({
            query: query,
        }),
    });
    const returned = await response.json();

    console.log(returned);

    if (returned.errors) {
        throw new Error("errors");
    }

    return returned.data;
}

export async function http<T>(info: OurRequestInfo): Promise<T> {
    let body: string | null = null;
    if (info.data) {
        body = JSON.stringify(info.data);
    }
    const response = await fetch(Config.baseUrl + info.url, {
        method: info.method || "GET",
        mode: "cors",
        headers: Object.assign(
            {
                "Content-Type": "application/json",
            },
            info.headers
        ),
        body: body,
    });
    return await response.json();
}

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
    lua: string;
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

export interface Entity {
    key: string;
    url: string;
    klass: Klass;
    creator: EntityRef;
    props: { map: Properties };
    chimeras: {
        containing?: Containing;
        behaviors?: { behaviors: { map: Behaviors } };
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

export interface EntityResponse {
    entity: Entity;
}

export interface AreasResponse {
    areas: Area[];
}

export interface PeopleResponse {
    people: Person[];
}

export interface Success {
    message: string;
}

export interface Failure {
    message: string;
}

export interface EntitiesObservation {
    entities: EntityRef[];
}

export interface PersonalObservation {
    who: ObservedPerson;
}
