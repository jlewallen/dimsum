<template>
    <div class="alert alert-dismissible">
        <BasicMarkdown :source="entry.rendered" v-if="entry.rendered" />
        <div v-else class="response unknown">{{ JSON.stringify(reply) }}</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { HistoryEntry } from "@/entity";
import { BasicMarkdown } from "./BasicMarkdown";

export default defineComponent({
    name: "DefaultReply",
    components: {
        BasicMarkdown,
    },
    props: {
        entry: {
            type: Object as () => HistoryEntry,
            required: true,
        },
        reply: {
            type: Object as () => Record<string, unknown>,
            required: true,
        },
    },
    mounted() {
        console.log(`unknown:`, this.entry.rendered);
    },
});
</script>

<style scoped></style>
