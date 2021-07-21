// import _ from "lodash";
import { createLogger, createStore, ActionContext } from "vuex";
import {
    RootState,
    MutationTypes,
    ActionTypes,
    Entity,
    RefreshEntityAction,
    NeedEntityAction,
    LoginAction,
    Auth,
    AuthenticatedAction,
    ReplResponse,
    ReplAction,
    RemoveHistoryEntry,
    UpdateEntityAction,
    UpdateWaitingMutation,
} from "./types";
import { getApi, subscribe } from "@/http";

export * from "./types";

type ActionParameters = ActionContext<RootState, RootState>;

const disabledRefresh = true;

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
                state.token = auth.token;
                state.key = auth.key;
            }
        },
        [MutationTypes.CONNECTED]: (state: RootState) => {
            state.connected = true;
        },
        [MutationTypes.DISCONNECTED]: (state: RootState) => {
            state.connected = false;
        },
        [MutationTypes.AUTH]: (state: RootState, auth: Auth | null) => {
            if (auth) {
                state.key = auth.key;
                state.headers["Authorization"] = `Bearer ${auth.token}`;
                state.token = auth.token;
                state.authenticated = true;
                window.localStorage["dimsum:auth"] = JSON.stringify({
                    key: auth.key,
                    headers: state.headers,
                    token: auth.token,
                });
            } else {
                state.key = "";
                state.headers = {};
                state.token = "";
                state.authenticated = false;
                delete window.localStorage["dimsum:auth"];
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
                // eslint-disable-next-line
                if ((entry.reply as any)["py/object"] == "plugins.editing.ScreenCleared") {
                    state.responses = [];
                } else {
                    state.responses = state.responses.filter((r) => !r.reply || r.reply["py/object"] != "Waiting");
                    state.responses.push(entry);
                    state.received++;
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
        [MutationTypes.WAITING]: (state: RootState, payload: UpdateWaitingMutation) => {
            if (payload.waiting) {
                state.responses.push({ rendered: {}, reply: { "py/object": "Waiting", interactive: false, information: true } });
                state.received++;
            }
        },
    },
    actions: {
        [ActionTypes.LOGIN]: async ({ state, dispatch, commit }: ActionParameters, payload: LoginAction) => {
            const api = getApi(state.headers);
            let data;
            if (payload.token && payload.secret) {
                data = await api.redeemInvite({
                    username: payload.name,
                    password: payload.password,
                    token: payload.token,
                    secret: payload.secret,
                });
            } else {
                data = await api.login({ username: payload.name, password: payload.password });
            }
            commit(MutationTypes.AUTH, data.login);
            return Promise.all([dispatch(new AuthenticatedAction(data.login)), dispatch(ActionTypes.LOADING)]);
        },
        [ActionTypes.AUTHENTICATED]: (/*{ state }: ActionParameters, payload: AuthenticatedAction*/) => {
            return Promise.resolve();
        },
        [ActionTypes.LOGOUT]: ({ commit }: ActionParameters) => {
            commit(MutationTypes.AUTH, null);
        },
        [ActionTypes.REPL]: async ({ state, commit }: ActionParameters, payload: ReplAction) => {
            commit(new UpdateWaitingMutation(true));
            const api = getApi(state.headers);
            const data = await api.language({ text: payload.command, evaluator: state.key });
            if (data.language) {
                commit(MutationTypes.REPLY, {
                    rendered: data.language.reply.rendered ? JSON.parse(data.language.reply.rendered) : undefined,
                    reply: JSON.parse(data.language.reply.model),
                });
                if (data.language.entities) {
                    commit(
                        MutationTypes.ENTITIES,
                        data.language.entities.map((row) => JSON.parse(row.serialized))
                    );
                }
            }
        },
        [ActionTypes.LOADING]: async ({ state, commit }: ActionParameters) => {
            await subscribe(
                state.headers,
                state.token,
                async (received) => {
                    const reply = received as { nearby: { rendered: string; model: string }[] };
                    for (const nearby of reply.nearby) {
                        const parsed = JSON.parse(nearby.model);
                        commit(MutationTypes.REPLY, { reply: parsed });
                    }
                },
                async () => {
                    commit(MutationTypes.CONNECTED);
                },
                async () => {
                    commit(MutationTypes.DISCONNECTED);
                }
            );
        },
        [ActionTypes.REFRESH_ENTITY]: async ({ state, commit }: ActionParameters, payload: RefreshEntityAction) => {
            if (state.entities[payload.key]) {
                return Promise.resolve();
            }
            if (!disabledRefresh) {
                const api = getApi(state.headers);
                const data = await api.entity({ key: payload.key });
                if (data.entitiesByKey) {
                    commit(MutationTypes.ENTITY, JSON.parse(data.entitiesByKey[0].serialized));
                }
            }
        },
        [ActionTypes.NEED_ENTITY]: async ({ state, commit }: ActionParameters, payload: NeedEntityAction) => {
            if (!disabledRefresh) {
                const api = getApi(state.headers);
                const data = await api.entity({ key: payload.key });
                if (data && data.entitiesByKey) {
                    for (const row of data.entitiesByKey) {
                        commit(MutationTypes.ENTITY, JSON.parse(row.serialized));
                    }
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
