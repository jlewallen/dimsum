<template>
    <div class="container-fluid home"></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store from "@/store";

export default defineComponent({
    name: "Home",
    async mounted(): Promise<void> {
        await this.$router.push("/explore");
    },
});
</script>
