<template>
<div class="item-editor">
	Item
        <div v-for="(value, key) in entity.areas" v-bind:key="key">
            <h3>{{key}} -></h3>
            <WithEntity :entityKey="value.key" v-slot="withEntity">
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
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>

<style scoped>
.entity {
}
</style>
