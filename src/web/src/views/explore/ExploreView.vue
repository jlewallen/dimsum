<template>
    <HistoryEntries :entries="entries" @selected="(v) => $emit('selected', v)" @dismiss="(v) => $emit('dismiss', v)" />
</template>

<script lang="ts">
import { defineComponent } from "vue";
import HistoryEntries from "./HistoryEntries.vue";
import store, { ReplAction, ReplResponse } from "@/store";

export default defineComponent({
    name: "ExploreView",
    components: {
        HistoryEntries,
    },
    computed: {
        connected(): boolean {
            return store.state.connected;
        },
        entries(): ReplResponse[] {
            return store.state.responses;
        },
        length(): number {
            return store.state.responses.length;
        },
    },
    watch: {
        length(after: number, before: number): void {
            this.$emit("scroll-bottom");
        },
        connected(after: boolean, before: boolean): void {
            if (after) {
                if (this.length == 0) {
                    void store.dispatch(new ReplAction("look"));
                }
            }
        },
    },
    async mounted(): Promise<void> {
        this.$emit("scroll-bottom");
        this.$emit("resume-repl");
    },
    methods: {},
});
</script>
<style></style>
