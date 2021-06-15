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

export interface Properties {
    name: string;
    desc: string;
    presence: string;
}

export type EntityKey = string;

export interface EntityRef {
    key: string;
    klass: string;
    name: string;
}

export interface Behavior {
    lua: string;
    logs: string[];
}

export type Behaviors = { [index: string]: Behavior };

export interface Entity {
    key: string;
    url: string;
    klass: string;
    creator: EntityRef;
    props: Properties;
    behaviors: Behaviors;
    holding?: EntityRef[];
    occuped?: EntityRef[];
    routes?: AreaRoute[];
    visible?: {
        hard_to_see: boolean;
        hidden: never;
        observations: never;
    };
    memory?: { [index: string]: EntityRef };
}

export interface Person extends Entity {
    holding: EntityRef[];
    wearing: EntityRef[];
    memory: { [index: string]: EntityRef };
}

export interface Animal extends Entity {
    holding: EntityRef[];
    wearing: EntityRef[];
    memory: { [index: string]: EntityRef };
}

export interface Area extends Entity {
    holding: EntityRef[];
    occuped: EntityRef[];
}

export interface Item extends Entity {
    area: EntityRef;
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
