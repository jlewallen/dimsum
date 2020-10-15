<template>
    <div id="nav">
        <router-link to="/">Home</router-link>
        |
        <router-link to="/login" v-if="!authenticated">Login</router-link>
        <router-link to="/logout" v-if="authenticated">Logout</router-link>
    </div>
    <router-view />
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
/* General */
html {
    overflow-y: scroll;
}

/* Forms */

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

/* Style inputs, select elements and textareas */
input[type="password"],
input[type="text"],
select,
textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-sizing: border-box;
    resize: vertical;
}

/* Style the label to display next to the inputs */
label {
    padding: 12px 12px 12px 0;
    display: inline-block;
}

/* Style the submit button */
input[type="submit"] {
    background-color: #4caf50;
    color: white;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    float: right;
}

/* Style the container */
.container {
    border-radius: 5px;
    background-color: #f2f2f2;
    padding: 20px;
}

/* Floating column for labels: 25% width */
.col-25 {
    float: left;
    width: 25%;
    margin-top: 6px;
}

/* Floating column for inputs: 75% width */
.col-75 {
    float: left;
    width: 75%;
    margin-top: 6px;
}

/* Clear floats after the columns */
.row:after {
    content: "";
    display: table;
    clear: both;
}

.row.actions {
    margin-top: 1em;
    display: flex;
    justify-content: flex-end;
}

/* Responsive layout - when the screen is less than 600px wide, make the two columns stack on top of each other instead of next to each other */
@media screen and (max-width: 600px) {
    .col-25,
    .col-75,
    input[type="submit"] {
        width: 100%;
        margin-top: 0;
    }
}

.button {
    background-color: coral;
    color: white;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    float: right;
    margin-right: 1em;
}
</style>
