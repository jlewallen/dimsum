<template>
    <div class="entity-header">
        <h3>{{ entityToKind(entity) }}: {{ entity.details.name }}</h3>
        <div>
            <div class="btn-group" role="group" aria-label="Basic example">
                <router-link :to="{ name: 'entity', params: { key: entity.key } }">
                    <button type="button" class="btn btn-secondary">General</button>
                </router-link>
                <router-link :to="{ name: 'entity-behavior', params: { key: entity.key } }">
                    <button type="button" class="btn btn-secondary">Behavior</button>
                </router-link>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import { entityToKind } from "@/store";

export default defineComponent({
    name: "Header",
    components: {},
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {},
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
