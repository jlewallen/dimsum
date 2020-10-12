<template>
    <div class="entities">
        <template v-for="entity in entities" v-bind:key="entity.key">
            <SmallEntityPanel :entity="entity" @selected="raiseSelected" />
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import SmallEntityPanel from "./SmallEntityPanel.vue";

export default defineComponent({
    name: "Entities",
    components: { SmallEntityPanel },
    props: {
        entities: {
            type: Array,
            required: true,
        },
    },
    mounted(): void {
        console.log("entities:mounted", this.entities);
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
}
</style>
