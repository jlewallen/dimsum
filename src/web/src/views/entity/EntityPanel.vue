<template>
    <div class="entity" v-on:click="(ev) => raiseSelected(entity)" v-bind:class="entityToClass(entity)">
        <div class="one">
            <div class="name" v-if="entity.quantity > 1">{{ entity.quantity }} {{ entity.details.name }}</div>
            <div class="name" v-else>{{ entity.details.name }}</div>
            <div class="creator">
                {{ entity.creator.name }}
            </div>
        </div>
        <div class="desc">{{ entity.details.desc }}</div>
        <div class="summary" v-if="summary">
            {{ summary }}
        </div>
        <slot></slot>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import { entityToClass } from "@/store";

export default defineComponent({
    name: "EntityPanel",
    props: {
        entity: {
            type: Object,
            required: true,
        },
    },
    computed: {
        entities(): EntityRef[] {
            const holding = this.entity.holding || [];
            const entities = this.entity.entities || [];
            return [...holding, ...entities];
        },
        summary(): string | null {
            if (this.entities.length == 0) {
                return null;
            }
            return this.entities.map((e) => e.klass).join(", ");
        },
    },
    methods: {
        entityToClass: entityToClass,
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
    width: 28em;
    display: flex;
    flex-direction: column;
    color: black;
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
.entity.animal {
    background-color: darkseagreen;
}

.entity .one {
    display: flex;
    justify-content: space-between;
}

.entity .name {
    font-weight: bold;
    margin-bottom: 1em;
}
.entity .owner {
    font-size: 10pt;
}
.entity .statistics {
    font-size: 10pt;
}
.entity .desc {
    margin-bottom: 1em;
}
.hard-to-see {
    opacity: 0.6;
}
</style>
