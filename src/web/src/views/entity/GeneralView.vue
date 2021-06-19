<template>
    <WithRoutedEntity v-slot="withEntity">
        <div class="container-fluid">
            <Header :entity="withEntity.entity" />
        </div>
        <div class="container-fluid">
            <GeneralEntityForm :entity="withEntity.entity" v-bind:key="withEntity.entity.key" />
        </div>
        <div class="container-fluid specific">
            <component v-bind:is="kindSpecific(withEntity.entity)" :entity="withEntity.entity" />
        </div>
    </WithRoutedEntity>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Header from "./Header.vue";
import WithRoutedEntity from "./WithRoutedEntity.vue";
import GeneralEntityForm from "./GeneralEntityForm.vue";
import AreaEditor from "./AreaEditor.vue";
import ItemEditor from "./ItemEditor.vue";
import AnimalEditor from "./AnimalEditor.vue";
import { Entity } from "@/http";
import { entityToKind } from "@/store";

export default defineComponent({
    name: "GeneralView",
    components: {
        Header,
        WithRoutedEntity,
        GeneralEntityForm,
        AreaEditor,
        ItemEditor,
        ExitEditor: ItemEditor,
        AnimalEditor,
        PersonEditor: AnimalEditor,
        PlayerEditor: AnimalEditor,
    },
    props: {},
    data(): {} {
        return {};
    },
    computed: {},
    watch: {},
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
