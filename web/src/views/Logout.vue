<template>
    <div></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { LogoutAction } from "@/store";

export default defineComponent({
    name: "Logout",
    components: {},
    mounted() {
        return store.dispatch(new LogoutAction()).then(() => {
            this.$router.push("/login");
        });
    },
});
</script>

<style></style>
