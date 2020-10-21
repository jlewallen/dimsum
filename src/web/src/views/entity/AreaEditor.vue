<template>
    <div class="area-editor">
        <div v-if="adjacent.length > 0" class="adjacent">
            <h4>Adjacent Areas:</h4>
            <Entities :entityRefs="adjacent" @selected="entitySelected" />
        </div>

        <div v-if="entity.occupied.length > 0">
            <h4>Also Here:</h4>
            <Entities :entityRefs="entity.occupied" @selected="entitySelected" />
        </div>

        <div v-if="entity.holding.length > 0">
            <h4>Also Here:</h4>
            <Entities :entityRefs="entity.holding" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Area, Item, AreaRoute, Entity, EntityRef } from "@/http";
import Entities from "./Entities.vue";
import store from "@/store";

export default defineComponent({
    name: "AreaEditor",
    components: { Entities },
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
                this.entity.holding
                    .map((ref: EntityRef) => store.state.entities[ref.key])
                    .filter((e: Entity | undefined) => {
                        return e && e.routes;
                    })
                    .map((e: Entity) => e.routes!)
            ).map((e: AreaRoute) => e.area);
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
