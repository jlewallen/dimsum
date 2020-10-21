<template>
    <div class="person-editor">
        <div v-if="entity.holding?.length > 0">
            <h4>Holding:</h4>
            <Entities :entityRefs="entity.holding" @selected="entitySelected" />
        </div>

        <div v-if="Object.keys(entity.memory || {}).length > 0">
            <h3>Memory:</h3>
            <KeyedEntities :entityRefs="entity.memory" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity, Person } from "@/http";
import Entities from "./Entities.vue";
import KeyedEntities from "./KeyedEntities.vue";

export default defineComponent({
    name: "PersonEditor",
    components: { KeyedEntities, Entities },
    props: {
        entity: {
            type: Object as () => Person,
            required: true,
        },
    },
    data() {
        return {};
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
</style>
