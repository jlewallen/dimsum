<template>
    <div class="explore container-fluid">
        <Repl @response="response" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Repl from "../shared/Repl.vue";
import { ReplResponse } from "@/store";

export default defineComponent({
    name: "ExploreView",
    components: {
        Repl,
    },
    props: {},
    data(): { command: string } {
        return { command: "" };
    },
    methods: {
        response(response: ReplResponse): void {
            console.log(response);
        },
    },
});
</script>
<style scoped></style>
