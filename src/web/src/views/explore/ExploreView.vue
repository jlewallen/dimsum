<template>
    <div class="history">
        <div v-for="response in responses" v-bind:key="response.key" class="response">
            <component v-bind:is="viewFor(response)" :response="response" :reply="response.reply" @selected="onSelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Replies from "../shared/replies";
import store, { getObjectType, Entity, ReplAction, ReplResponse } from "@/store";

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
    mounted(): Promise<any> {
        this.$emit("scroll-bottom");
        return store.dispatch(new ReplAction("look"));
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
    },
});
</script>
<style>
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
