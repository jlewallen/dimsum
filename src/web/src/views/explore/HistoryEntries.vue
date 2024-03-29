<template>
    <div class="history">
        <div v-for="entry in entries" v-bind:key="entry.key" class="response">
            <component
                v-bind:is="viewFor(entry)"
                :response="entry"
                :entry="entry"
                :reply="entry.reply"
                @selected="onSelected"
                @dismiss="onDismissed(entry)"
                @command="(command) => onCommand(entry, command)"
            />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Replies from "../shared/replies";
import store, { getObjectType, Entity, ReplAction, HistoryEntry, RemoveHistoryEntry } from "@/store";

export default defineComponent({
    name: "HistoryEntries",
    components: {
        ...Replies,
    },
    props: {
        entries: {
            type: Object as () => HistoryEntry[],
            required: true,
        },
    },
    methods: {
        viewFor(response: HistoryEntry): string | null {
            // eslint-disable-next-line
            const info = getObjectType(response?.reply as any);
            if (info.simple) {
                const keys = Object.keys(Replies);
                if (keys.indexOf(info.simple) >= 0) {
                    return info.simple;
                }
            }
            return "DefaultReply";
        },
        async onSelected(entity: Entity): Promise<void> {
            console.log("explore:selected", entity);
            await this.$router.push({
                name: "entity",
                params: { key: entity.key },
            });
        },
        onDismissed(entry: HistoryEntry) {
            console.log("explore:dismissed", entry);
            store.commit(new RemoveHistoryEntry(entry));
            this.$emit("resume-repl");
        },
        async onCommand(entry: HistoryEntry, command: { line: string }) {
            console.log("explore:command", entry, command);
            await store.dispatch(new ReplAction(command.line));
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
}
.response.universal {
    padding: 1em;
}
.response.help,
.response.wiki {
    padding: 1em;
    background-color: #30475e;
    background-color: rgb(34, 39, 46);
}

.response.entities-observation {
    padding: 1em;
}

.response.waiting {
    padding: 1em;
    background-color: #222;
}
</style>
