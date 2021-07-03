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
            const stored = window.localStorage["dimsum:headers"];
            if (stored) {
                state.authenticated = true;
                state.headers = JSON.parse(stored);
            }
        },
        [MutationTypes.AUTH]: (state: RootState, auth: Auth | null) => {
            if (auth) {
                state.headers["Authorization"] = `Bearer ${auth.token}`;
                state.authenticated = true;
                window.localStorage["dimsum:headers"] = JSON.stringify(state.headers);
            } else {
                state.headers = {};
                state.authenticated = false;
                delete window.localStorage["dimsum:headers"];
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
        [MutationTypes.REPLY]: (state: RootState, entry: ReplResponse) => {
            if (entry.reply.interactive === true) {
                state.interactables.push(entry);
            } else {
                state.responses.push(entry);
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
            const data = await api.language({ text: payload.command, evaluator: "jlewallen" });
            if (data.language) {
                commit(MutationTypes.REPLY, { reply: JSON.parse(data.language.reply) });
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
        [ActionTypes.SAVE_ENTITY_DETAILS]: ({ state, commit }: ActionParameters, payload: SaveEntityDetailsAction) => {
            /*
            return http<EntityResponse>({
                url: `/entities/${urlKey(payload.form.key)}/props`,
                method: "POST",
                data: payload.form,
                headers: state.headers,
            }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
                return data;
			});
			*/
        },
        [ActionTypes.SAVE_ENTITY_BEHAVIOR]: ({ state, commit }: ActionParameters, payload: SaveEntityBehaviorAction) => {
            /*
            return http<EntityResponse>({
                url: `/entities/${urlKey(payload.key)}/behavior`,
                method: "POST",
                data: payload.form,
                headers: state.headers,
            }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
                return data;
			});
			*/
        },
    },
    getters: {},
    modules: {},
});
