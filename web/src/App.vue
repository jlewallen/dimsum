<template>
    <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <a class="navbar-brand" href="#">Mudsum</a>

        <div class="collapse navbar-collapse">
            <ul class="navbar-nav mr-auto">
                <li class="nav-item">
                    <span class="nav-link">
                        <router-link to="/">Home</router-link>
                    </span>
                </li>
                <li class="nav-item" v-if="!authenticated">
                    <span class="nav-link">
                        <router-link to="/login">Login</router-link>
                    </span>
                </li>
                <li class="nav-item" v-if="authenticated">
                    <span class="nav-link">
                        <router-link to="/logout">Logout</router-link>
                    </span>
                </li>
            </ul>
            <form class="form-inline my-2 my-lg-0">
                <input class="form-control mr-sm-2" type="search" placeholder="Search" aria-label="Search" />
                <button class="btn btn-outline-success my-2 my-sm-0" type="submit">Search</button>
            </form>
        </div>
    </nav>
    <div id="main">
        <router-view />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { MutationTypes, LoadingAction } from "@/store";

export default defineComponent({
    name: "App",
    data() {
        return {
            busy: false,
        };
    },
    computed: {
        authenticated() {
            return store.state.authenticated;
        },
    },
    mounted(): Promise<void> {
        this.busy = true;

        store.commit(MutationTypes.INIT);

        if (store.state.authenticated) {
            return store.dispatch(new LoadingAction()).finally(() => {
                this.busy = false;
            });
        }

        this.$router.push("/login");

        return Promise.resolve();
    },
});
</script>

<style>
html {
    overflow-y: scroll;
}

#main {
    margin-top: 1em;
}
</style>
