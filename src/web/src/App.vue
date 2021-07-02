<template>
    <div id="upper">
        <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
            <a class="navbar-brand" href="#">Mudsum</a>

            <div class="collapse navbar-collapse">
                <ul class="navbar-nav mr-auto">
                    <li class="nav-item" v-if="authenticated">
                        <span class="nav-link">
                            <router-link to="/">Home</router-link>
                        </span>
                    </li>
                    <li class="nav-item" v-if="authenticated">
                        <span class="nav-link">
                            <router-link to="/explore">Explore</router-link>
                        </span>
                    </li>
                    <li class="nav-item" v-if="authenticated">
                        <span class="nav-link">
                            <router-link to="/logout">Logout</router-link>
                        </span>
                    </li>
                    <li class="nav-item" v-if="!authenticated">
                        <span class="nav-link">
                            <router-link to="/login">Login</router-link>
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
            <router-view @scroll-bottom="scrollBottom" />
        </div>
    </div>
    <div id="lower">
        <Repl @send="send" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { MutationTypes, LoadingAction, Entity, ReplAction, ReplResponse } from "@/store";
import Repl from "./views/shared/Repl.vue";

export default defineComponent({
    name: "App",
    components: {
        Repl,
    },
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
    methods: {
        send(command: string): Promise<any> {
            return store.dispatch(new ReplAction(command));
        },
        scrollBottom(): void {
            this.$nextTick(() => {
                const el = this.$el.parentNode.querySelector("#upper");
                if (el) {
                    el.scrollTop = el.scrollHeight + 90;
                }
            });
        },
    },
});
</script>

<style>
html {
    overflow-y: hidden;
}

body {
    height: 100vh;
}

#wrapper {
    height: 100%;
}

#app {
    height: 100%;
}

#main {
    margin-top: 1em;
}

#upper {
    flex: 1;
    overflow: auto;
}

#app {
    height: 100%;
    display: flex;
    flex-direction: column;
}

#lower {
    padding: 1em;
    border-top: 2px solid #dfdfdf;
}
</style>
