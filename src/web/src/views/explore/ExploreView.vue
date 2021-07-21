<template>
    <div>
        <HistoryEntries :entries="entries" @selected="(v) => $emit('selected', v)" @dismiss="(v) => $emit('dismiss', v)" />
    </div>
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
        received(): number {
            return store.state.received;
        },
    },
    watch: {
        received(): void {
            this.$emit("scroll-bottom");
        },
        connected(after: boolean): void {
            if (after) {
                if (this.received == 0) {
                    void store.dispatch(new ReplAction("look"));
                }
            }
        },
    },
    async mounted(): Promise<void> {
        this.$emit("scroll-bottom");
        this.$emit("resume-repl");

        if (!store.state.authenticated) {
            this.$router.push("/login");
        }
    },
    methods: {},
});
</script>
<style></style>
