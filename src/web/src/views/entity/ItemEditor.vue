<template>
    <div class="item-editor">
        <div v-for="route in entity.routes" v-bind:key="route.area.key">
            <WithEntity :entityKey="route.area.key" v-slot="withEntity">
                <EntityPanel :entity="withEntity.entity" @selected="raiseSelected" />
            </WithEntity>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import WithEntity from "./WithEntity.vue";
import EntityPanel from "./EntityPanel.vue";

export default defineComponent({
    name: "ItemEditor",
    components: {
        WithEntity,
        EntityPanel,
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
