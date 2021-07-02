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
import store, { Entity, ReplAction, ReplResponse } from "@/store";

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
            const pyObject: string = (response?.reply as any)["py/object"] || "";
            return pyObject.replace("model.reply.", "").replace("model.game.", "") || null;
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
<style scoped>
.response {
}
</style>
