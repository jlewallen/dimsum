<template>
    <WithRoutedEntity v-slot="withEntity">
        <div class="container-fluid">
            <Header :entity="withEntity.entity" />
        </div>
        <div class="container-fluid">
            <BehaviorEditor :entity="withEntity.entity" />
        </div>
    </WithRoutedEntity>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Header from "./Header.vue";
import WithRoutedEntity from "./WithRoutedEntity.vue";
import BehaviorEditor from "./BehaviorEditor.vue";

export default defineComponent({
    name: "BehaviorView",
    components: {
        Header,
        WithRoutedEntity,
        BehaviorEditor,
    },
    props: {},
    data(): {} {
        return {};
    },
    computed: {},
    watch: {},
    methods: {},
});
</script>

<style scoped></style>
