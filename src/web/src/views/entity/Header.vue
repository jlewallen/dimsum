<template>
    <div class="entity-header">
        <h3>{{ entityToKind(entity) }}: {{ entity.props.map.name.value }}</h3>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import { entityToKind } from "@/store";

export default defineComponent({
    name: "Header",
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    methods: {
        entityToKind: entityToKind,
    },
});
</script>

<style scoped>
.entity-header {
    margin-bottom: 1em;
}
</style>
