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
        }
    },
    methods: {},
});
</script>
<style></style>
