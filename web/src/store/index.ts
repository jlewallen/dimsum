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
    NeedEntityAction,
    SaveEntityAction,
} from "./types";
import { http } from "@/http";

export * from "./types";

type ActionParameters = ActionContext<RootState, RootState>;

export default createStore<RootState>({
    plugins: [createLogger()],
    state: new RootState(),
    mutations: {
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
        [ActionTypes.LOADING]: ({ commit }: ActionParameters) => {
            return Promise.all([
                http<AreasResponse>({ url: "" }).then((data) => {
                    commit(MutationTypes.AREAS, data.areas);
                }),
                http<PeopleResponse>({ url: "/people" }).then((data) => {
                    commit(MutationTypes.PEOPLE, data.people);
                }),
            ]);
        },
        [ActionTypes.NEED_ENTITY]: ({ commit }: ActionParameters, payload: NeedEntityAction) => {
            return http<EntityResponse>({ url: `/entities/${payload.key}` }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
            });
        },
        [ActionTypes.SAVE_ENTITY]: ({ commit }: ActionParameters, payload: SaveEntityAction) => {
            return http<EntityResponse>({
                url: `/entities/${payload.form.key}`,
                method: "POST",
                data: payload.form,
            }).then((data) => {
                commit(MutationTypes.ENTITY, data.entity);
                return data;
            });
        },
    },
    modules: {},
});
