<template>
    <div class="entity" v-on:click="(ev) => raiseSelected(entity)" v-bind:class="entity.kind.toLowerCase()">
        <div class="one">
            <div class="name">{{ entity.details.name }}</div>
            <div class="owner">
                {{ entity.owner.name }}
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

export default defineComponent({
    name: "SmallEntityPanel",
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
            return this.entities.map((e) => e.kind).join(", ");
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
    display: flex;
    flex-direction: column;
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
</style>
