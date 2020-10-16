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

export interface ReplResponse {
    reply: {
        kind: string;
    };
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

export interface Details {
    name: string;
    desc: string;
    presence: string;
}

export type EntityKey = string;

export interface EntityRef {
    key: string;
    kind: string;
    url: string;
    name: string;
}

export interface Behavior {
    lua: string;
    logs: string[];
}

export type Behaviors = { [index: string]: Behavior };

export interface Entity {
    key: string;
    kind: string;
    url: string;
    owner: EntityRef;
    details: Details;
    holding?: Entity[];
    entities?: Entity[];
    areas?: { [index: string]: EntityRef };
    memory?: EntityRef | null;
    behaviors: Behaviors;
}

export interface Person extends Entity {
    holding: Entity[];
    memory: EntityRef | null;
}

export interface Area extends Entity {
    entities: Entity[];
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
