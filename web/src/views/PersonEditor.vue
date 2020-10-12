<template>
    <div>
        <div class="entity person">
            <div></div>
        </div>

        <div v-if="entity.holding?.length > 0">
            <h4>Holding:</h4>
            <Entities :entityRefs="entity.holding" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import Entities from "./Entities.vue";

export default defineComponent({
    name: "PersonEditor",
    components: { Entities },
    props: {
        entity: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {};
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
</style>
