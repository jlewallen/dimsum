import _ from "lodash";
import { createLogger, createStore, ActionContext } from "vuex";
import {
    RootState,
    MutationTypes,
    ActionTypes,
    AreasResponse,
    Area,
    PeopleResponse,
    Person,
    EntityResponse,
    Entity,
    RefreshEntityAction,
    NeedEntityAction,
    SaveEntityDetailsAction,
    SaveEntityBehaviorAction,
    LoginAction,
    Auth,
    AuthenticatedAction,
    ReplResponse,
    ReplAction,
} from "./types";
import { http } from "@/http";

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
        [MutationTypes.REPLY]: (state: RootState, response: ReplResponse) => {
            state.responses.unshift(response);
        },
    },
    actions: {
        [ActionTypes.LOGIN]: ({ dispatch, commit }: ActionParameters, payload: LoginAction) => {
            return http<Auth>({ url: "/login", method: "POST", data: payload }).then((data: Auth) => {
                commit(MutationTypes.AUTH, data);
                return Promise.all([dispatch(new AuthenticatedAction(data)), dispatch(ActionTypes.LOADING)]);
            });
        },
        [ActionTypes.AUTHENTICATED]: ({ state }: ActionParameters, payload: AuthenticatedAction) => {
            return Promise.resolve();
        },
        [ActionTypes.LOGOUT]: ({ commit }: ActionParameters) => {
            commit(MutationTypes.AUTH, null);
        },
        [ActionTypes.REPL]: ({ state, commit }: ActionParameters, payload: ReplAction) => {
            return http<ReplResponse>({ method: "POST", url: "/repl", headers: state.headers, data: payload }).then((response) => {
                commit(MutationTypes.REPLY, response);
                return response;
            });
        },
        [ActionTypes.LOADING]: ({ state, commit }: ActionParameters) => {
            return Promise.all([
                http<AreasResponse>({ url: "/areas", headers: state.headers }).then((data) => {
                    commit(MutationTypes.AREAS, data.areas);
                }),
                http<PeopleResponse>({ url: "/people", headers: state.headers }).then((data) => {
                    commit(MutationTypes.PEOPLE, data.people);
                }),
            ]);
        },

        [ActionTypes.REFRESH_ENTITY]: ({ state, commit }: ActionParameters, payload: RefreshEntityAction) => {
            if (state.entities[payload.key]) {
                return Promise.resolve();
            }
            return http<EntityResponse>({ url: `/entities/${urlKey(payload.key)}`, headers: state.headers }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
            });
        },
        [ActionTypes.NEED_ENTITY]: ({ state, commit }: ActionParameters, payload: NeedEntityAction) => {
            return http<EntityResponse>({ url: `/entities/${urlKey(payload.key)}`, headers: state.headers }).then((data) => {
                if (!data.entity) {
                    console.warn("commit-null-entity", data);
                    return;
                }
                commit(MutationTypes.ENTITY, data.entity);
            });
        },
        [ActionTypes.SAVE_ENTITY_DETAILS]: ({ state, commit }: ActionParameters, payload: SaveEntityDetailsAction) => {
            return http<EntityResponse>({
                url: `/entities/${urlKey(payload.form.key)}/props`,
                method: "POST",
                data: payload.form,
                headers: state.headers,
            }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
                return data;
            });
        },
        [ActionTypes.SAVE_ENTITY_BEHAVIOR]: ({ state, commit }: ActionParameters, payload: SaveEntityBehaviorAction) => {
            return http<EntityResponse>({
                url: `/entities/${urlKey(payload.key)}/behavior`,
                method: "POST",
                data: payload.form,
                headers: state.headers,
            }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
                return data;
            });
        },
    },
    getters: {},
    modules: {},
});
