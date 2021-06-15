<template>
    <div class="response area-observation card">
        <WithEntity :entityKey="reply.where.key" :force="true" v-slot="where">
            <div class="card-body">
                <h4 class="card-title">{{ where.entity.props.name }}</h4>
                <h6 class="card-subtitle">{{ where.entity.props.desc }}</h6>
                <div class="routes">
                    <div v-for="(route, index) in reply.routes" v-bind:key="index" class="route">
                        <div>{{ route.direction.compass }} of here there is</div>
                        <WithEntity :entityKey="route.area.key" :force="true" v-slot="withEntity">
                            <TinyEntityPanel :entity="withEntity.entity" @selected="(e) => onSelected(e)" />
                        </WithEntity>
                    </div>
                </div>
                <div class="people">
                    <div v-for="observed in reply.living" v-bind:key="observed.alive.key">
                        <WithEntity :entityKey="observed.alive.key" :force="true" v-slot="withEntity">
                            <TinyEntityPanel :entity="withEntity.entity" @selected="(e) => onSelected(e)" />
                        </WithEntity>
                    </div>
                </div>
                <div class="entities">
                    <div v-for="observed in reply.items" v-bind:key="observed.item.key">
                        <WithEntity :entityKey="observed.item.key" :force="true" v-slot="withEntity">
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
}
</style>
