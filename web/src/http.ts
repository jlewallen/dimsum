import { Config } from "@/config";

export interface OurRequestInfo {
    url: string;
    method?: string;
    data?: any;
}

export async function http<T>(info: OurRequestInfo): Promise<T> {
    let body: string | null = null;
    if (info.data) {
        body = JSON.stringify(info.data);
    }
    const response = await fetch(Config.baseUrl + info.url, {
        method: info.method || "GET",
        mode: "cors",
        headers: {
            "Content-Type": "application/json",
        },
        body: body,
    });
    return await response.json();
}

export interface Details {
    name: string;
    desc: string;
}

export interface EntityRef {
    key: string;
    kind: string;
    url: string;
}

export interface Entity {
    key: string;
    kind: string;
    url: string;
    details: Details;
    holding?: Entity[];
    entities?: Entity[];
    area?: EntityRef;
}

export interface Person extends Entity {
    holding: Entity[];
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
