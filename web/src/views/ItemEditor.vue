<template>
    <div>
        <div class="entity item">
            <div></div>
        </div>

        <div v-if="entity.area">
            <h3>This leads to:</h3>
            <DynamicSmallEntityPanel :entityKey="entity.area.key" @selected="destinationSelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import DynamicSmallEntityPanel from "./DynamicSmallEntityPanel.vue";
import { Entity } from "@/http";

export default defineComponent({
    name: "ItemEditor",
    components: { DynamicSmallEntityPanel },
    props: {
        entity: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {};
    },
    mounted(): void {
        console.log("item-editor:mounted", this.entity);
    },
    methods: {
        destinationSelected(entity: Entity) {
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>

<style scoped>
.entity {
}
</style>
