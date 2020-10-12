<template>
    <div class="entities">
        <template v-for="ref in entityRefs" v-bind:key="ref.key">
            <DynamicSmallEntityPanel :entityKey="ref.key" @selected="raiseSelected" />
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import DynamicSmallEntityPanel from "./DynamicSmallEntityPanel.vue";

export default defineComponent({
    name: "Entities",
    components: { DynamicSmallEntityPanel },
    props: {
        entityRefs: {
            type: Array as () => EntityRef[],
            required: true,
        },
    },
    methods: {
        raiseSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
.entities {
    display: flex;
    flex-wrap: wrap;
}
</style>
