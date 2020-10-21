<template>
    <div class="container login">
        <div class="row justify-content-center">
            <form class="form col-8" @submit.prevent="login">
                <div class="form-group row">
                    <label class="col-sm-2 col-form-label">Name</label>
                    <div class="col-sm-4">
                        <input class="form-control" type="text" v-model="form.name" />
                    </div>
                </div>
                <div class="form-group row">
                    <label class="col-sm-2 col-form-label">Password</label>
                    <div class="col-sm-4">
                        <input class="form-control" type="password" v-model="form.password" />
                    </div>
                </div>
                <div class="form-group row">
                    <input class="btn btn-primary" type="submit" value="Login" />
                </div>
            </form>
        </div>
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
