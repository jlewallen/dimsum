<template>
    <HistoryEntries :entries="entries" @selected="(v) => $emit('selected', v)" @obsolete="(v) => $emit('obsolete', v)" />
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
    },
    async mounted(): Promise<void> {
        this.$emit("scroll-bottom");
        if (this.length == 0) {
            await store.dispatch(new ReplAction("look"));
            await store.dispatch(new ReplAction("ed guitar"));
        }
    },
    methods: {},
});
</script>
<style></style>
