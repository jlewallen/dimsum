<template>
    <div class="response area-observation card">
        <div class="markdown" v-if="true">
            <Markdown :source="markdown" />
        </div>
        <WithEntity :entityKey="reply.area.key" v-slot="where" v-else>
            <div class="card-body">
                <h4 class="card-title">{{ where.entity.props.map.name.value }}</h4>
                <h6 class="card-subtitle">{{ where.entity.props.map.desc.value }}</h6>
                <div class="people">
                    <div v-for="observed in reply.living" v-bind:key="observed.entity.key">
                        <WithEntity :entityKey="observed.entity.key" v-slot="withEntity">
                            <TinyEntityPanel :entity="withEntity.entity" @selected="(e) => onSelected(e)" />
                        </WithEntity>
                    </div>
                </div>
                <div class="entities">
                    <div v-for="observed in reply.items" v-bind:key="observed.entity.key">
                        <WithEntity :entityKey="observed.entity.key" v-slot="withEntity">
                            <TinyEntityPanel :entity="withEntity.entity" @selected="(e) => onSelected(e)" />
                        </WithEntity>
                    </div>
                </div>
            </div>
        </WithEntity>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity, HistoryEntry, AreaObservation } from "@/store";
import WithEntity from "../entity/WithEntity.vue";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";
import Markdown from "vue3-markdown-it";

export default defineComponent({
    name: "AreaObservation",
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
            type: Object as () => AreaObservation,
            required: true,
        },
    },
    mounted() {
        console.log("reply", this.reply);
    },
    computed: {
        markdown(): string {
            const r = this.entry.rendered;
            if (_.isArray(r.description)) {
                return `## ${r.title}\n\n` + r.description.join("\n\n");
            }
            return "";
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
.routes {
    display: flex;
}
.routes .route {
    display: flex;
    align-items: flex-end;
}
.people {
    display: flex;
}
.entities {
    display: flex;
    flex-wrap: wrap;
}
.card {
    background-color: transparent;
}
.markdown {
    padding: 1em;
}
</style>
