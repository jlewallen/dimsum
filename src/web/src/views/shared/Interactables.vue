<template>
    <div class="interactables">
        <Repl @send="send" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Repl from "./Repl.vue";
import store, { MutationTypes, LoadingAction, Entity, ReplAction, ReplResponse } from "@/store";

export default defineComponent({
    name: "Interactables",
    components: {
        Repl,
    },
    props: {},
    computed: {},
    methods: {
        async send(command: string): Promise<void> {
            await store.dispatch(new ReplAction(command));
        },
    },
});
</script>
<style></style>
