<template>
    <div class="item-editor">
        <div v-if="entity.area">
            <h3>This leads to:</h3>
            <WithEntity :entityKey="entity.area.key" v-slot="withEntity">
                <SmallEntityPanel :entity="withEntity.entity" @selected="raiseSelected" />
            </WithEntity>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import WithEntity from "./WithEntity.vue";
import SmallEntityPanel from "./SmallEntityPanel.vue";

export default defineComponent({
    name: "ItemEditor",
    components: {
        WithEntity,
        SmallEntityPanel,
    },
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
        raiseSelected(entity: Entity) {
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>

<style scoped>
.entity {
}
</style>
