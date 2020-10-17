<template>
    <div class="entity" v-on:click="() => onSelected(entity)" v-bind:class="entity.kind.toLowerCase()">
        <template v-if="entity.quantity == 1">
            {{ entity.details.name }}
        </template>
        <template v-else>{{ entity.quantity }} {{ entity.details.name }}</template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";

export default defineComponent({
    name: "TinyEntityPanel",
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    computed: {},
    methods: {
        onSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
/* top left bottom right */
.entity {
    border-radius: 5px;
    display: flex;
    color: black;
    margin: 0.1em 0.1em 0.1em 0.1em;
    padding: 0.2em 0.5em 0.2em 0.5em;
    cursor: pointer;
}
.entity.area {
    background-color: azure;
    background-color: skyblue;
}
.entity.person,
.entity.player {
    background-color: coral;
}
.entity.item {
    background-color: khaki;
}
.entity.recipe {
    background-color: thistle;
}
</style>
