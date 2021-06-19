<template>
    <div class="area-editor">
        <div v-if="adjacent.length > 0" class="adjacent">
            <h4>Adjacent Areas:</h4>
            <Entities :entityRefs="adjacent" @selected="entitySelected" />
        </div>

        <div class="routes" v-if="false && entity.routes.length > 0">
            <h4>Routes:</h4>
            <div v-for="route in entity.routes" v-bind:key="route.direction.compass" class="route">
                <div>{{ route.direction.compass }} of here there is</div>
                <WithEntity :entityKey="route.area.key" v-slot="withEntity" v-if="route.area.key">
                    <EntityPanel :entity="withEntity.entity" @selected="(e) => entitySelected(e)" />
                </WithEntity>
            </div>
        </div>

        <div v-if="entity.chimeras.occupyable.occupied.length > 0">
            <h4>Also Here:</h4>
            <Entities :entityRefs="entity.chimeras.occupyable.occupied" @selected="entitySelected" />
        </div>

        <div v-if="entity.chimeras.containing.holding.length > 0">
            <h4>Also Here:</h4>
            <Entities :entityRefs="entity.chimeras.containing.holding" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Area, Item, AreaRoute, Entity, EntityRef, Exit } from "@/http";
import Entities from "./Entities.vue";
import WithEntity from "./WithEntity.vue";
import EntityPanel from "./EntityPanel.vue";
import store from "@/store";

export default defineComponent({
    name: "AreaEditor",
    components: { Entities, WithEntity, EntityPanel },
    props: {
        entity: {
            type: Object as () => Area,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {
        adjacent(): EntityRef[] {
            return _.flatten(
                (this.entity.chimeras.containing?.holding || [])
                    .map((ref: EntityRef) => store.state.entities[ref.key])
                    .filter((e: Entity | undefined) => {
                        return e && e.chimeras.exit;
                    })
                    .map((e: Entity) => e.chimeras.exit!)
            ).map((e: Exit) => e.area);
        },
    },
    methods: {
        entitySelected(entity: Entity) {
            console.log("area:selected", entity);
            return this.$router.push({
                name: "entity",
                params: { key: entity.key },
            });
        },
    },
});
</script>

<style scoped>
.entity {
}
.entities {
    display: flex;
    flex-wrap: wrap;
}
.adjacent {
    margin-top: 1em;
}
</style>
