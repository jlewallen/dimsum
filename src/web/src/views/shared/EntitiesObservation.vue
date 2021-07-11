<template>
    <div class="response entities-observation">
        <div class="markdown" v-if="true">
            <Markdown :source="markdown" />
        </div>
        <div class="card-body" v-else>
            <div class="entities">
                <div v-for="entity in reply.entities" v-bind:key="entity.key">
                    <WithEntity :entityKey="entity.key" v-slot="withEntity">
                        <TinyEntityPanel :entity="withEntity.entity" @selected="(e) => onSelected(e)" />
                    </WithEntity>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity, EntitiesObservation, HistoryEntry } from "@/store";
import WithEntity from "../entity/WithEntity.vue";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";
import Markdown from "vue3-markdown-it";

export default defineComponent({
    name: "EntitiesObservation",
    components: {
        WithEntity,
        TinyEntityPanel,
        Markdown,
    },
    props: {
        entry: {
            type: Object as () => HistoryEntry,
            required: true,
        },
        reply: {
            type: Object as () => EntitiesObservation,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {
        markdown(): string {
            const r = this.entry.rendered;
            if (_.isArray(r.lines)) {
                return r.lines.join("\n\n");
            }
            return r.lines;
        },
    },
    methods: {
        onSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
.entities {
    display: flex;
    flex-wrap: wrap;
}
</style>
