<template>
    <div class="login">
        <form class="container form" @submit.prevent="login">
            <div class="row">
                <div class="col-25">
                    <label>Name</label>
                </div>
                <div class="col-75">
                    <input type="text" v-model="form.name" />
                </div>
            </div>
            <div class="row">
                <div class="col-25">
                    <label>Password</label>
                </div>
                <div class="col-75">
                    <input type="password" v-model="form.password" />
                </div>
            </div>
            <div class="row actions">
                <input type="submit" value="Login" />
            </div>
        </form>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { LoginAction } from "@/store";

export default defineComponent({
    name: "Login",
    components: {},
    data(): { busy: boolean; form: { name: string; password: string } } {
        return {
            busy: false,
            form: {
                name: "",
                password: "",
            },
        };
    },
    computed: {},
    methods: {
        login(): Promise<any> {
            return store.dispatch(new LoginAction(this.form.name, this.form.password)).then(() => {
                // TODO Take them to where they are.
                this.$router.push("/");
            });
        },
    },
});
</script>

<style></style>
