<template>
    <WithRoutedEntity v-slot="withEntity">
        <div class="container-fluid">
            <Header :entity="withEntity.entity" />

            {{ withEntity.entity }}
        </div>
    </WithRoutedEntity>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Header from "./Header.vue";
import WithRoutedEntity from "./WithRoutedEntity.vue";
import { Entity } from "@/http";
import { entityToKind } from "@/store";

export default defineComponent({
    name: "EntityView",
    components: {
        Header,
        WithRoutedEntity,
    },
    methods: {
        kindSpecific(entity: Entity): string {
            return entityToKind(entity) + "Editor";
        },
    },
});
</script>

<style scoped>
.specific {
    margin-top: 1em;
    margin-bottom: 1em;
}
</style>
