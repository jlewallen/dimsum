import { createRouter, createWebHistory, RouteRecordRaw } from "vue-router";
import Home from "../views/Home.vue";
import Login from "../views/auth/Login.vue";
import Logout from "../views/auth/Logout.vue";
import GeneralView from "../views/entity/GeneralView.vue";
import BehaviorView from "../views/entity/BehaviorView.vue";
import ExploreView from "../views/explore/ExploreView.vue";

const routes: Array<RouteRecordRaw> = [
    {
        path: "/",
        name: "Home",
        component: Home,
    },
    {
        path: "/login",
        name: "Login",
        component: Login,
    },
    {
        path: "/logout",
        name: "logout",
        component: Logout,
    },
    {
        path: "/entities/:key",
        name: "entity-general",
        component: GeneralView,
    },
    {
        path: "/entities/:key/behavior",
        name: "entity-behavior",
        component: BehaviorView,
    },
    {
        path: "/explore",
        name: "explore",
        component: ExploreView,
    },
];

const router = createRouter({
    history: createWebHistory(process.env.BASE_URL),
    routes,
});

export default router;
