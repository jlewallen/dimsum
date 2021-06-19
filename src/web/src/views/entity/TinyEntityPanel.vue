<template>
    <div class="entity" v-on:click="() => onSelected(entity)" v-bind:class="entityToClass(entity)">
        <template v-if="entity.quantity == 1">
            {{ entity.props.map.name.value }}
        </template>
        <template v-else>{{ entity.quantity }} {{ entity.props.map.name.value }}</template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import { entityToClass } from "@/store";

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
        entityToClass: entityToClass,
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
.entity.exit {
    background-color: thistle;
}
.entity.living {
    background-color: darkseagreen;
}
</style>
