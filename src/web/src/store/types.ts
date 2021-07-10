import { Entity, Area, Person, UpdateEntityDetailsPayload, UpdateEntityBehaviorPayload, ReplResponse } from "@/http";
export * from "@/http";

export function getObjectType(something: Record<string, unknown>) {
    const pyObject: string = (something["py/object"] as string) || "";
    const parts = pyObject.split(".");
    const simpleClassName = parts.length > 0 ? parts[parts.length - 1] : null;
    return {
        pyObject: pyObject,
        simple: simpleClassName,
    };
}

export class RootState {
    authenticated = false;
    connected = false;
    key = "";
    token = "";
    headers: { [index: string]: string } = {};
    entities: { [index: string]: Entity } = {};
    areas: { [index: string]: Area } = {};
    people: { [index: string]: Person } = {};
    interactables: ReplResponse[] = [];
    responses: ReplResponse[] = [];
}

export enum ActionTypes {
    LOGIN = "LOGIN",
    LOGOUT = "LOGOUT",
    AUTHENTICATED = "AUTHENTICATED",
    LOADING = "LOADING",
    REFRESH_ENTITY = "REFRESH_ENTITY",
    NEED_ENTITY = "NEED_ENTITY",
    SAVE_ENTITY_DETAILS = "SAVE_ENTITY_DETAILS",
    SAVE_ENTITY_BEHAVIOR = "SAVE_ENTITY_BEHAVIOR",
    REPL = "REPL",
    UPDATE_ENTITY = "UPDATE_ENTITY",
}

export enum MutationTypes {
    INIT = "INIT",
    AUTH = "AUTH",
    PEOPLE = "PEOPLE",
    AREAS = "AREAS",
    ENTITY = "ENTITY",
    ENTITIES = "ENTITIES",
    REPLY = "REPLY",
    REMOVE_HISTORY_ENTRY = "REMOVE_HISTORY_ENTRY",
    CONNECTED = "CONNECTED",
    DISCONNECTED = "DISCONNECTED",
}

export class LoadingAction {
    type = ActionTypes.LOADING;
}

export class ReplAction {
    type = ActionTypes.REPL;

    constructor(public readonly command: string) {}
}

export class RefreshEntityAction {
    type = ActionTypes.REFRESH_ENTITY;

    constructor(public readonly key: string) {}
}

export class NeedEntityAction {
    type = ActionTypes.NEED_ENTITY;

    constructor(public readonly key: string) {}
}

export class SaveEntityDetailsAction {
    type = ActionTypes.SAVE_ENTITY_DETAILS;

    constructor(public readonly form: UpdateEntityDetailsPayload) {}
}

export class SaveEntityBehaviorAction {
    type = ActionTypes.SAVE_ENTITY_BEHAVIOR;

    constructor(public readonly key: string, public readonly form: UpdateEntityBehaviorPayload) {}
}

export class LoginAction {
    type = ActionTypes.LOGIN;

    constructor(
        public readonly name: string,
        public readonly password: string,
        public readonly secret: string | null,
        public readonly token: string | null
    ) {}
}

export class LogoutAction {
    type = ActionTypes.LOGOUT;
}

export interface Auth {
    key: string;
    token: string;
}

export class AuthenticatedAction {
    type = ActionTypes.AUTHENTICATED;

    constructor(public readonly auth: Auth) {}
}

export function entityToKind(entity: Entity): string {
    return entity.klass["py/type"].replace("scopes.", "").replace("Class", "");
}

export function entityToClass(entity: Entity): string {
    const classes: string[] = [entityToKind(entity).toLowerCase()];
    if (entity.chimeras.visibility && entity.chimeras.visibility.visible.hard_to_see) {
        classes.push("hard-to-see");
    }
    return classes.join(" ");
}

export class RemoveHistoryEntry {
    type = MutationTypes.REMOVE_HISTORY_ENTRY;

    constructor(public readonly entry: ReplResponse) {}
}

export class UpdateEntityAction {
    type = ActionTypes.UPDATE_ENTITY;

    constructor(public readonly entity: Entity) {}
}
