<template>
    <div class="history">
        <div v-for="response in responses" v-bind:key="response.key" class="response">
            <component
                v-bind:is="viewFor(response)"
                :response="response"
                :reply="response.reply"
                @selected="onSelected"
                @obsolete="onObsolete(response)"
            />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Replies from "../shared/replies";
import store, { getObjectType, Entity, ReplAction, ReplResponse, RemoveHistoryEntry } from "@/store";

export default defineComponent({
    name: "ExploreView",
    components: {
        ...Replies,
    },
    data(): { command: string; response: ReplResponse | null } {
        return { command: "", response: null };
    },
    computed: {
        responses(): ReplResponse[] {
            return store.state.responses;
        },
        historyLength(): number {
            return store.state.responses.length;
        },
    },
    watch: {
        historyLength(after: number, before: number): void {
            this.$emit("scroll-bottom");
        },
    },
    async mounted(): Promise<void> {
        this.$emit("scroll-bottom");
        if (this.historyLength == 0) {
            await store.dispatch(new ReplAction("look"));
            await store.dispatch(new ReplAction("ed guitar"));
        }
    },
    methods: {
        send(command: string): Promise<any> {
            return store.dispatch(new ReplAction(command));
        },
        viewFor(response: ReplResponse): string | null {
            const info = getObjectType(response?.reply as any);
            if (info.simple) {
                const keys = Object.keys(Replies);
                if (keys.indexOf(info.simple) >= 0) {
                    return info.simple;
                }
            }
            return "DefaultReply";
        },
        onSelected(entity: Entity): Promise<any> {
            console.log("explore:selected", entity);
            return this.$router.push({
                name: "entity",
                params: { key: entity.key },
            });
        },
        onObsolete(response: ReplResponse) {
            console.log("explore:obsolete", response);
            store.commit(new RemoveHistoryEntry(response));
            this.$emit("resume-repl");
        },
    },
});
</script>
<style>
.response.clear {
    padding: 1em;
    background-color: #30475e;
    display: none;
}
.response.editor {
    padding: 1em;
    background-color: #30475e;
}
.response.living-entered-area {
    padding: 1em;
    background-color: #30475e;
}
.response.living-left-area {
    padding: 1em;
    background-color: #30475e;
}
.response.player-spoke {
    padding: 1em;
    background-color: #30475e;
}
.response.items {
    padding: 1em;
    background-color: #30475e;
}
</style>
