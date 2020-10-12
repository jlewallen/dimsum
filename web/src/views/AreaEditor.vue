<template>
    <div>
        <div class="entity area">
            <div></div>
        </div>

        <div v-if="adjacent.length > 0" class="adjacent">
            <h4>Adjacent Areas:</h4>
            <Entities :entityRefs="adjacent" @selected="entitySelected" />
        </div>

        <div v-if="entity.entities?.length > 0">
            <h4>Also Here:</h4>
            <Entities :entityRefs="entity.entities" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Area, Entity, EntityRef } from "@/http";
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
            return this.entity.entities
                .map((ref) => store.state.entities[ref.key])
                .filter((e) => e && e.area)
                .map((e) => e.area!);
        },
    },
    methods: {
        entitySelected(entity: Entity) {
            console.log("area:selected", entity);
            return this.$router.push({ path: `/entities/${entity.key}` });
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
