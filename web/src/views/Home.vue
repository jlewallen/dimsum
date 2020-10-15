<template>
    <div class="container-fluid home">
        <div v-if="busy">Busy</div>
        <div v-if="areas">
            <Entities :entityRefs="areas" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Entities from "./entity/Entities.vue";
import { Entity, Area } from "@/http";
import store from "@/store";

export default defineComponent({
    name: "Home",
    components: {
        Entities,
    },
    data(): { busy: boolean } {
        return {
            busy: false,
        };
    },
    computed: {
        areas(): Area[] {
            return Object.values(store.state.areas);
        },
    },
    methods: {
        entitySelected(entity: Entity): Promise<any> {
            console.log("home:selected", entity);
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>
