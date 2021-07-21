<template>
    <div class="interactables">
        <HistoryEntries :entries="interactables" @resume-repl="this.$emit('resume-repl')" />
        <Repl :connected="connected" @send="send" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Repl from "./Repl.vue";
import store, { ReplAction, ReplResponse } from "@/store";
import HistoryEntries from "@/views/explore/HistoryEntries.vue";

export default defineComponent({
    name: "Interactables",
    components: {
        HistoryEntries,
        Repl,
    },
    computed: {
        connected(): boolean {
            return store.state.connected;
        },
        interactables(): ReplResponse[] {
            return store.state.interactables;
        },
    },
    methods: {
        async send(command: string): Promise<void> {
            if (command.length > 0) {
                await store.dispatch(new ReplAction(command));
            }
        },
    },
});
</script>
<style></style>
