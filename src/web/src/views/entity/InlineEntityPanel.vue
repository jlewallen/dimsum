<template>
    <div class=""></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";

export default defineComponent({
    name: "InlineEntityPanel",
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    computed: {},
    methods: {
        raiseSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped></style>
