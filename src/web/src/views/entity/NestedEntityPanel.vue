<template>
    <div class="">
        <EntityPanel :entity="entity" @selected="raiseSelected"></EntityPanel>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import EntityPanel from "./EntityPanel.vue";

export default defineComponent({
    name: "NestedEntityPanel",
    components: { EntityPanel },
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    computed: {
        inner(): EntityRef | null {
            if (this.entity.area) {
                return this.entity.area;
            }
            return null;
        },
    },
    methods: {
        raiseSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped></style>
