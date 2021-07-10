<template>
    <div class="container login">
        <div class="row justify-content-center">
            <form class="form col-4" @submit.prevent="login">
                <div class="form-group row">
                    <label class="col-sm-4 col-form-label">Name</label>
                    <div class="col-sm-8">
                        <input class="form-control" type="text" v-model="form.name" />
                    </div>
                </div>
                <div class="form-group row">
                    <label class="col-sm-4 col-form-label">Password</label>
                    <div class="col-sm-8">
                        <input class="form-control" type="password" v-model="form.password" />
                    </div>
                </div>
                <div class="alert alert-danger" v-if="invalidCredentials">Sorry, those don't seem to be valid.</div>
                <div class="form-group row">
                    <div class="col-sm-6">
                        <input class="btn btn-primary" type="submit" value="Login" :disabled="busy" />
                    </div>
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
    data(): {
        busy: boolean;
        form: { name: string; password: string };
        invalidCredentials: boolean;
    } {
        return {
            busy: false,
            form: {
                name: "",
                password: "",
            },
            invalidCredentials: false,
        };
    },
    computed: {},
    methods: {
        async login(): Promise<void> {
            try {
                this.invalidCredentials = false;
                this.busy = true;
                await store.dispatch(new LoginAction(this.form.name, this.form.password));
                await this.$router.push("/explore");
            } catch (error) {
                this.invalidCredentials = true;
            } finally {
                this.busy = false;
            }
        },
    },
});
</script>

<style></style>
