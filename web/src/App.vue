<template>
    <div id="nav">
        <router-link to="/">Home</router-link>
    </div>
    <router-view />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { LoadingAction } from "@/store";

export default defineComponent({
    name: "App",
    data() {
        return {
            busy: false,
        };
    },
    mounted(): Promise<void> {
        this.busy = true;
        return store.dispatch(new LoadingAction()).finally(() => {
            this.busy = false;
        });
    },
});
</script>

<style>
#app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #2c3e50;
}

#nav {
    text-align: center;
    padding: 30px;
}

#nav a {
    font-weight: bold;
    color: #2c3e50;
}

#nav a.router-link-exact-active {
    color: #42b983;
}
</style>
