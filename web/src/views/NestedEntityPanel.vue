<template>
    <div class="">
        <SmallEntityPanel :entity="entity" @selected="raiseSelected"></SmallEntityPanel>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import SmallEntityPanel from "./SmallEntityPanel.vue";

export default defineComponent({
    name: "NestedEntityPanel",
    components: { SmallEntityPanel },
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
