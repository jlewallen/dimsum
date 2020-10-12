<template>
    <div class="home"></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Config } from "@/config";

export default defineComponent({
    name: "Home",
    components: {},
    mounted() {
        console.log("home:mounted");
        Promise.all([fetch(Config.baseUrl)]);
    },
});
</script>
