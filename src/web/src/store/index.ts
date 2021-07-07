import _ from "lodash";
import { createLogger, createStore, ActionContext } from "vuex";
import {
    RootState,
    MutationTypes,
    ActionTypes,
    Area,
    Person,
    Entity,
    Reply,
    RefreshEntityAction,
    NeedEntityAction,
    SaveEntityDetailsAction,
    SaveEntityBehaviorAction,
    LoginAction,
    Auth,
    AuthenticatedAction,
    ReplResponse,
    ReplAction,
    RemoveHistoryEntry,
    UpdateEntityAction,
} from "./types";
import { getApi, subscribe } from "@/http";

export * from "./types";

type ActionParameters = ActionContext<RootState, RootState>;

function base64ToHex(key: string): string {
    if (!key) throw new Error("key is required");
    let hex = "";
    const bytes = atob(key);
    for (let i = 0; i < bytes.length; ++i) {
        const byte = bytes.charCodeAt(i).toString(16);
        hex += byte.length === 2 ? byte : "0" + byte;
    }
    return hex;
}

const urlKey = base64ToHex;

export default createStore<RootState>({
    plugins: [createLogger()],
    state: new RootState(),
    mutations: {
        [MutationTypes.INIT]: (state: RootState) => {
            const raw = window.localStorage["dimsum:auth"];
            if (raw) {
                const auth = JSON.parse(raw);
                state.authenticated = true;
                state.headers = auth.headers;
                state.key = auth.key;
            }
        },
        [MutationTypes.AUTH]: (state: RootState, auth: Auth | null) => {
            if (auth) {
                state.headers["Authorization"] = `Bearer ${auth.token}`;
                state.key = auth.key;
                state.authenticated = true;
                window.localStorage["dimsum:auth"] = JSON.stringify({ key: auth.key, headers: state.headers });
            } else {
                state.headers = {};
                state.key = "";
                state.authenticated = false;
                delete window.localStorage["dimsum:auth"];
            }
        },
        [MutationTypes.PEOPLE]: (state: RootState, people: Person[]) => {
            state.people = _.keyBy(people, (p: Person) => p.key);
            for (const e of people) {
                state.entities[e.key] = e;
            }
        },
        [MutationTypes.AREAS]: (state: RootState, areas: Area[]) => {
            state.areas = _.keyBy(areas, (p: Area) => p.key);
            for (const e of areas) {
                state.entities[e.key] = e;
            }
        },
        [MutationTypes.ENTITY]: (state: RootState, entity: Entity) => {
            state.entities[entity.key] = entity;
        },
        [MutationTypes.ENTITIES]: (state: RootState, entities: Entity[]) => {
            for (const row of entities) {
                state.entities[row.key] = row;
            }
        },
        [MutationTypes.REPLY]: (state: RootState, entry: ReplResponse) => {
            if (entry.reply.information === true) {
                if (entry.reply.entities) {
                    for (const row of entry.reply.entities) {
                        state.entities[row.key] = JSON.parse(row.serialized);
                    }
                }
                return;
            }
            if (entry.reply.interactive === true) {
                state.interactables.push(entry);
            } else {
                if ((entry.reply as any)["py/object"] == "plugins.editing.ScreenCleared") {
                    state.responses = [];
                } else {
                    state.responses.push(entry);
                }
            }
        },
        [MutationTypes.REMOVE_HISTORY_ENTRY]: (state: RootState, payload: RemoveHistoryEntry) => {
            const i = state.responses.indexOf(payload.entry);
            if (i >= 0) {
                state.responses.splice(i, 1);
            } else {
                const j = state.interactables.indexOf(payload.entry);
                if (j >= 0) {
                    state.interactables.splice(j, 1);
                }
            }
        },
    },
    actions: {
        [ActionTypes.LOGIN]: async ({ state, dispatch, commit }: ActionParameters, payload: LoginAction) => {
            const api = getApi(state.headers);
            const data = await api.login({ username: payload.name, password: payload.password });
            commit(MutationTypes.AUTH, data.login);
            return Promise.all([dispatch(new AuthenticatedAction(data.login)), dispatch(ActionTypes.LOADING)]);
        },
        [ActionTypes.AUTHENTICATED]: ({ state }: ActionParameters, payload: AuthenticatedAction) => {
            return Promise.resolve();
        },
        [ActionTypes.LOGOUT]: ({ commit }: ActionParameters) => {
            commit(MutationTypes.AUTH, null);
        },
        [ActionTypes.REPL]: async ({ state, commit }: ActionParameters, payload: ReplAction) => {
            const api = getApi(state.headers);
            const data = await api.language({ text: payload.command, evaluator: state.key });
            if (data.language) {
                commit(MutationTypes.REPLY, { reply: JSON.parse(data.language.reply) });
                if (data.language.entities) {
                    commit(
                        MutationTypes.ENTITIES,
                        data.language.entities.map((row) => JSON.parse(row.serialized))
                    );
                }
            }
        },
        [ActionTypes.LOADING]: async ({ state, commit }: ActionParameters) => {
            const api = getApi(state.headers);
            const areas = await api.areas();
            if (areas && areas.areas) {
                commit(
                    MutationTypes.AREAS,
                    areas.areas.map((row) => JSON.parse(row.serialized))
                );
            }
            const people = await api.people();
            if (people && people.people) {
                commit(
                    MutationTypes.PEOPLE,
                    people.people.map((row) => JSON.parse(row.serialized))
                );
            }

            await subscribe(state.headers, async (received) => {
                const reply = received as { nearby: string[] };
                for (const nearby of reply.nearby) {
                    const parsed = JSON.parse(nearby);
                    console.log("ws:received", parsed);
                    commit(MutationTypes.REPLY, { reply: parsed });
                }
            });
        },
        [ActionTypes.REFRESH_ENTITY]: async ({ state, commit }: ActionParameters, payload: RefreshEntityAction) => {
            if (state.entities[payload.key]) {
                return Promise.resolve();
            }
            const api = getApi(state.headers);
            const data = await api.entity({ key: payload.key });
            if (data.entitiesByKey) {
                commit(MutationTypes.ENTITY, JSON.parse(data.entitiesByKey[0].serialized));
            }
        },
        [ActionTypes.NEED_ENTITY]: async ({ state, commit }: ActionParameters, payload: NeedEntityAction) => {
            const api = getApi(state.headers);
            const data = await api.entity({ key: payload.key });
            if (data.entitiesByKey) {
                for (const row of data.entitiesByKey) {
                    commit(MutationTypes.ENTITY, JSON.parse(row.serialized));
                    break; // TODO FIX
                }
            }
        },
        [ActionTypes.UPDATE_ENTITY]: async ({ state, commit }: ActionParameters, payload: UpdateEntityAction) => {
            const api = getApi(state.headers);
            const data = await api.updateEntity({
                key: payload.entity.key,
                serialized: JSON.stringify(payload.entity),
            });
            if (data.update && data.update.affected) {
                for (const row of data.update.affected) {
                    commit(MutationTypes.ENTITY, JSON.parse(row.serialized));
                }
            }
        },
    },
    getters: {},
    modules: {},
});
