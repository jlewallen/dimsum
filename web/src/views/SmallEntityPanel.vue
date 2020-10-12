<template>
    <div class="entity" v-on:click="(ev) => raiseSelected(entity)" v-bind:class="entity.kind.toLowerCase()">
        <div class="name">{{ entity.details.name }}</div>
        <div class="desc">{{ entity.details.desc }}</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";

export default defineComponent({
    name: "SmallEntityPanel",
    components: {},
    props: {
        entity: {
            type: Object,
            required: true,
        },
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
    padding: 1em;
    margin-bottom: 1em;
    margin-right: 1em;
    border-radius: 5px;
    border: 1px solid #f2f2f2;
    width: 50em;
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
.entity .name {
    font-weight: bold;
    margin-bottom: 1em;
}
.entity .desc {
}
</style>
