<template>
    <div class="explore container-fluid">
        <Repl @send="send" />

        <div v-for="response in responses" v-bind:key="response.key" class="response">
            <component v-bind:is="viewFor(response)" :response="response" :reply="response.reply" @selected="onSelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Repl from "../shared/Repl.vue";
import Replies from "../shared/replies";
import store, { Entity, ReplAction, ReplResponse } from "@/store";

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
    mounted(): Promise<any> {
        return store.dispatch(new ReplAction("look"));
    },
    methods: {
        send(command: string): Promise<any> {
            return store.dispatch(new ReplAction(command));
        },
        viewFor(response: ReplResponse): string | null {
            const pyObject: string = (response?.reply as any)["py/object"] || "";
            return pyObject.replace("reply.", "").replace("game.", "") || null;
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
    margin-bottom: 1em;
}
</style>
