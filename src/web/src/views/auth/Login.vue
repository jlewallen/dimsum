<template>
    <div class="container login">
        <div class="row justify-content-center">
            <form class="form col-4" @submit.stop.prevent="login">
                <div class="form-group row" v-if="token">
                    <label class="col-sm-4 col-form-label">Invite Secret</label>
                    <div class="col-sm-8">
                        <input class="form-control" type="secret" v-model="form.secret" />
                    </div>
                </div>
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
import _ from "lodash";
import { defineComponent } from "vue";
import store, { LoginAction } from "@/store";

export default defineComponent({
    name: "Login",
    data(): {
        busy: boolean;
        form: {
            secret: string;
            name: string;
            password: string;
        };
        invalidCredentials: boolean;
    } {
        return {
            busy: false,
            form: {
                secret: "",
                name: "",
                password: "",
            },
            invalidCredentials: false,
        };
    },
    computed: {
        token(): string | null {
            const maybe = this.$route.query?.token;
            if (!maybe) {
                return null;
            }
            if (_.isArray(maybe)) {
                return maybe[0];
            }
            return maybe || null;
        },
    },
    methods: {
        async login(): Promise<void> {
            try {
                this.invalidCredentials = false;
                this.busy = true;
                await store.dispatch(new LoginAction(this.form.name, this.form.password, this.form.secret, this.token));
                await this.$router.push("/explore");
            } catch (error) {
                console.log("error", error);
                this.invalidCredentials = true;
            } finally {
                this.busy = false;
            }
        },
    },
});
</script>

<style></style>
