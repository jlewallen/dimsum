import { Entity, Area, Person, UpdateEntityPayload } from "@/http";
export * from "@/http";

export class RootState {
    entities: { [index: string]: Entity } = {};
    areas: { [index: string]: Area } = {};
    people: { [index: string]: Person } = {};
}

export enum ActionTypes {
    LOADING = "LOADING",
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

export class NeedEntityAction {
    type = ActionTypes.NEED_ENTITY;

    constructor(public readonly key: string) {}
}

export class SaveEntityAction {
    type = ActionTypes.SAVE_ENTITY;

    constructor(public readonly form: UpdateEntityPayload) {}
}
