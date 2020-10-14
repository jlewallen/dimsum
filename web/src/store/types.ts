import { Entity, Area, Person, UpdateEntityPayload } from "@/http";
export * from "@/http";

export class RootState {
    authenticated = false;
    headers: { [index: string]: string } = {};
    entities: { [index: string]: Entity } = {};
    areas: { [index: string]: Area } = {};
    people: { [index: string]: Person } = {};
}

export enum ActionTypes {
    LOGIN = "LOGIN",
    LOGOUT = "LOGOUT",
    AUTHENTICATED = "AUTHENTICATED",
    LOADING = "LOADING",
    REFRESH_ENTITY = "REFRESH_ENTITY",
    NEED_ENTITY = "NEED_ENTITY",
    SAVE_ENTITY = "SAVE_ENTITY",
}

export enum MutationTypes {
    PEOPLE = "PEOPLE",
    AREAS = "AREAS",
    ENTITY = "ENTITY",
}

export class LoadingAction {
    type = ActionTypes.LOADING;
}

export class RefreshEntityAction {
    type = ActionTypes.REFRESH_ENTITY;

    constructor(public readonly key: string) {}
}

export class NeedEntityAction {
    type = ActionTypes.NEED_ENTITY;

    constructor(public readonly key: string) {}
}

export class SaveEntityAction {
    type = ActionTypes.SAVE_ENTITY;

    constructor(public readonly form: UpdateEntityPayload) {}
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
