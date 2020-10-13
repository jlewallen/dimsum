<template>
    <div class="entities">
        <div v-for="key in Object.keys(entityRefs)" v-bind:key="key">
            {{ key }}
            <DynamicSmallEntityPanel :entityKey="entityRefs[key].key" @selected="raiseSelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import DynamicSmallEntityPanel from "./DynamicSmallEntityPanel.vue";

export default defineComponent({
    name: "KeyedEntities",
    components: { DynamicSmallEntityPanel },
    props: {
        entityRefs: {
            type: Object as () => { [index: string]: EntityRef },
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
