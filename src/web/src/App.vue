<template>
    <div id="hack">
        <div id="upper" :class="{ obscured: isObscured }" @click="resumeRepl()">
            <nav class="navbar navbar-expand-lg navbar-dark bg-dark">
                <a class="navbar-brand" href="#">Mudsum</a>

                <div class="collapse navbar-collapse">
                    <ul class="navbar-nav mr-auto">
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
                    <form class="form-inline my-2 my-lg-0" v-show="false">
                        <input class="form-control mr-sm-2" type="search" placeholder="Search" aria-label="Search" />
                        <button class="btn btn-outline-success my-2 my-sm-0" type="submit">Search</button>
                    </form>
                </div>
            </nav>
            <div id="main">
                <router-view @scroll-bottom="scrollBottom" @resume-repl="resumeRepl" />
            </div>
        </div>
        <div id="lower">
            <Interactables @scroll-bottom="scrollBottom" @resume-repl="resumeRepl" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { MutationTypes, LoadingAction } from "@/store";
import Interactables from "./views/shared/Interactables.vue";
import { ignoringKey } from "@/ux";

export default defineComponent({
    name: "App",
    components: {
        Interactables,
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
        isObscured(): boolean {
            return store.state.interactables.length > 0;
        },
    },
    created() {
        window.onfocus = () => {
            console.log("window:focus");
            this.resumeRepl();
        };
        window.addEventListener("keyup", (data) => {
            if (ignoringKey(data)) {
                return;
            }
            if (data.key == " ") {
                this.resumeRepl();
                return;
            }
        });
    },
    mounted(): Promise<void> {
        this.busy = true;

        store.commit(MutationTypes.INIT);

        if (store.state.authenticated) {
            return store.dispatch(new LoadingAction()).finally(() => {
                this.busy = false;
            });
        }

        return Promise.resolve();
    },
    methods: {
        scrollBottom(): void {
            this.$nextTick(() => {
                const el = this.$el.parentNode.querySelector("#upper");
                if (el) {
                    el.scrollTop = el.scrollHeight + 90;
                }
            });
        },
        resumeRepl(): void {
            const focusing = this.$el.parentNode.querySelector("#repl-command");
            if (focusing) {
                focusing.focus();
            }
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

#hack {
    height: 100%;
    display: flex;
    flex-direction: column;
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
}

.obscured {
    opacity: 0.5;
}
</style>
