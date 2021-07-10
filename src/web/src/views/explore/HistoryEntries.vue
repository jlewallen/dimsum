<template>
    <div class="history">
        <div v-for="entry in entries" v-bind:key="entry.key" class="response">
            <component
                v-bind:is="viewFor(entry)"
                :response="entry"
                :reply="entry.reply"
                @selected="onSelected"
                @dismiss="onDismissed(entry)"
            />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Replies from "../shared/replies";
import store, { getObjectType, Entity, ReplAction, ReplResponse, RemoveHistoryEntry } from "@/store";

export default defineComponent({
    name: "HistoryEntries",
    components: {
        ...Replies,
    },
    props: {
        entries: {
            type: Object as () => ReplResponse[],
            required: true,
        },
    },
    computed: {},
    methods: {
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
        onDismissed(entry: ReplResponse) {
            console.log("explore:dismissed", entry);
            store.commit(new RemoveHistoryEntry(entry));
            this.$emit("resume-repl");
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

.response.editor {
    background-color: #222;
}
.response.clear {
    padding: 1em;
    background-color: #30475e;
    display: none;
}

.response.dynamic {
    padding: 1em;
    background-color: #30475e;
}
</style>
