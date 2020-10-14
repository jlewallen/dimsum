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
    SaveEntityAction,
    LoginAction,
    Auth,
    AuthenticatedAction,
} from "./types";
import { http } from "@/http";

export * from "./types";

type ActionParameters = ActionContext<RootState, RootState>;

export default createStore<RootState>({
    plugins: [createLogger()],
    state: new RootState(),
    mutations: {
        ["INIT"]: (state: RootState) => {
            const stored = window.localStorage["dimsum:headers"];
            if (stored) {
                state.authenticated = true;
                state.headers = JSON.parse(stored);
            }
        },
        ["AUTH"]: (state: RootState, auth: Auth | null) => {
            if (auth) {
                state.headers["Authorization"] = `Bearer ${auth.token}`;
                state.authenticated = true;
                window.localStorage["dimsum:headers"] = JSON.stringify(state.headers);
            } else {
                state.headers = {};
                state.authenticated = false;
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
    },
    actions: {
        [ActionTypes.LOGIN]: ({ dispatch, commit }: ActionParameters, payload: LoginAction) => {
            return http<any>({ url: "/login", method: "POST", data: payload }).then((data: Auth) => {
                commit("AUTH", data);
                return dispatch(new AuthenticatedAction(data));
            });
        },
        [ActionTypes.AUTHENTICATED]: ({ commit }: ActionParameters, payload: AuthenticatedAction) => {
            return Promise.resolve();
        },
        [ActionTypes.LOGOUT]: ({ dispatch, commit }: ActionParameters) => {
            commit("AUTH", null);
        },
        [ActionTypes.LOADING]: ({ state, commit }: ActionParameters) => {
            return Promise.all([
                http<AreasResponse>({ url: "", headers: state.headers }).then((data) => {
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
            return http<EntityResponse>({ url: `/entities/${payload.key}`, headers: state.headers }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
            });
        },
        [ActionTypes.NEED_ENTITY]: ({ state, commit }: ActionParameters, payload: NeedEntityAction) => {
            return http<EntityResponse>({ url: `/entities/${payload.key}`, headers: state.headers }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
            });
        },
        [ActionTypes.SAVE_ENTITY]: ({ state, commit }: ActionParameters, payload: SaveEntityAction) => {
            return http<EntityResponse>({
                url: `/entities/${payload.form.key}`,
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
