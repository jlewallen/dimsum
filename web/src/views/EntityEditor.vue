<template>
    <div class="entity-editor" v-if="entity">
        <h3>{{ entity.kind }}: {{ entity.details.name }}</h3>
        <GeneralEntityForm :entity="entity" />
        <component v-bind:is="kindSpecific" :entity="entity" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import GeneralEntityForm from "./GeneralEntityForm.vue";
import AreaEditor from "./AreaEditor.vue";
import ItemEditor from "./ItemEditor.vue";
import PersonEditor from "./PersonEditor.vue";
import { Entity } from "@/http";

export default defineComponent({
    name: "EntityEditor",
    components: {
        GeneralEntityForm,
        AreaEditor,
        ItemEditor,
        PersonEditor,
        PlayerEditor: PersonEditor,
    },
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {
        kindSpecific(): string {
            return this.entity.kind + "Editor";
        },
    },
    methods: {},
});
</script>
<style></style>
