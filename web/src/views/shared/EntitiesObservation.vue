<template>
    <div class="response area-observation card">
        <div class="card-body">
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
import { defineComponent } from "vue";
import { Entity, EntitiesObservation } from "@/store";
import WithEntity from "../entity/WithEntity.vue";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";

export default defineComponent({
    name: "EntitiesObservation",
    components: {
        WithEntity,
        TinyEntityPanel,
    },
    props: {
        reply: {
            type: Object as () => EntitiesObservation,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {},
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
}
</style>
