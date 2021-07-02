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
    headers: { [index: string]: string } = {};
    entities: { [index: string]: Entity } = {};
    areas: { [index: string]: Area } = {};
    people: { [index: string]: Person } = {};
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
}

export enum MutationTypes {
    INIT = "INIT",
    AUTH = "AUTH",
    PEOPLE = "PEOPLE",
    AREAS = "AREAS",
    ENTITY = "ENTITY",
    REPLY = "REPLY",
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

    constructor(public readonly name: string, public readonly password: string) {}
}

export class LogoutAction {
    type = ActionTypes.LOGOUT;
}

export interface Auth {
    token: string;
}

export class AuthenticatedAction {
    type = ActionTypes.AUTHENTICATED;

    constructor(public readonly auth: Auth) {}
}

export function entityToKind(entity: Entity): string {
    return entity.klass["py/type"].replace("model.scopes.", "").replace("Class", "");
}

export function entityToClass(entity: Entity): string {
    const classes: string[] = [entityToKind(entity).toLowerCase()];
    if (entity.chimeras.visibility && entity.chimeras.visibility.visible.hard_to_see) {
        classes.push("hard-to-see");
    }
    return classes.join(" ");
}
