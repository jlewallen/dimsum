<template>
    <div>
        <SmallEntityPanel :entity="entity" v-if="entity" @selected="raiseSelected" />
        <div v-else>Loading</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import store, { NeedEntityAction } from "@/store";
import SmallEntityPanel from "./SmallEntityPanel.vue";

export default defineComponent({
    name: "DynamicSmallEntityPanel",
    components: { SmallEntityPanel },
    props: {
        entityKey: {
            type: String,
            required: true,
        },
    },
    computed: {
        entity(): Entity | null {
            return store.state.entities[this.entityKey];
        },
    },
    mounted(): Promise<void> {
        if (this.entity == null) {
            return store.dispatch(new NeedEntityAction(this.entityKey));
        }
        return Promise.resolve();
    },
    methods: {
        raiseSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
.entity {
}
</style>
