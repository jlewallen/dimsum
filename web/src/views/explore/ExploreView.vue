<template>
    <div class="explore container-fluid">
        <Repl @response="onResponse" />

        <div v-for="response in responses" v-bind:key="response.key">
            <component v-bind:is="viewFor(response)" :response="response" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Repl from "../shared/Repl.vue";
import Replies from "../shared/replies";
import store, { ReplResponse } from "@/store";

export default defineComponent({
    name: "ExploreView",
    components: {
        ...Replies,
        Repl,
    },
    props: {},
    computed: {
        responses(): ReplResponse[] {
            return store.state.responses;
        },
    },
    data(): { command: string; response: ReplResponse | null } {
        return { command: "", response: null };
    },
    methods: {
        onResponse(response: ReplResponse): void {
            this.response = response;
        },
        viewFor(response: ReplResponse): string | null {
            return response?.reply.kind || null;
        },
    },
});
</script>
<style scoped></style>
