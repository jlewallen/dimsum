<template>
    <div class="response detailed-observation">
        <div class="markdown">
            <Markdown :source="markdown" />
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { HistoryEntry, DetailedObservation } from "@/store";
import Markdown from "vue3-markdown-it";

export default defineComponent({
    name: "DetailedObservation",
    components: {
        Markdown,
    },
    props: {
        entry: {
            type: Object as () => HistoryEntry,
            required: true,
        },
    },
    computed: {
        markdown(): string {
            const r = this.entry.rendered;
            if (_.isArray(r.description)) {
                return `### ${r.title}\n\n` + r.description.join("\n\n");
            }
            return "";
        },
    },
});
</script>

<style scoped>
.markdown {
    padding: 1em;
}
</style>
