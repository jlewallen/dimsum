<template>
    <div class="response area-observation card">
        <WithEntity :entityKey="reply.where.key" v-slot="where">
            <div class="card-body">
                <h4 class="card-title">{{ where.entity.details.name }}</h4>
                <h6 class="card-subtitle">{{ where.entity.details.desc }}</h6>
                <div class="people">
                    <div v-for="observed in reply.people" v-bind:key="observed.person.key">
                        <WithEntity :entityKey="observed.person.key" v-slot="withEntity">
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
import { defineComponent } from "vue";
import { Entity, AreaObservation, Area } from "@/store";
import WithEntity from "../entity/WithEntity.vue";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";

export default defineComponent({
    name: "AreaObservation",
    components: {
        WithEntity,
        TinyEntityPanel,
    },
    props: {
        reply: {
            type: Object as () => AreaObservation,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    methods: {
        onSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
.people {
    display: flex;
}
.entities {
    display: flex;
}
</style>
