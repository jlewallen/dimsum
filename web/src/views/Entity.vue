<template>
    <div class="container-fluid entity">
        <div v-if="entity">
            <EntityEditor :entity="entity" v-bind:key="entity.key" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import EntityEditor from "./EntityEditor.vue";
import { Entity } from "@/http";
import store, { RefreshEntityAction } from "@/store";

export default defineComponent({
    name: "Entity",
    components: {
        EntityEditor,
    },
    data(): {} {
        return {};
    },
    computed: {
        key(): string | null {
            return this.$route.params.key?.toString() || null;
        },
        entity(): Entity | null {
            if (!this.key) return null;
            return store.state.entities[this.key];
        },
    },
    watch: {
        key(): Promise<void> {
            return this.refresh();
        },
    },
    mounted(): Promise<void> {
        return this.refresh();
    },
    methods: {
        refresh(): Promise<void> {
            if (!this.key) {
                console.log("no key", this.$route);
                return Promise.resolve();
            }
            return store.dispatch(new RefreshEntityAction(this.key));
        },
    },
});
</script>

<style scoped>
.home {
}
</style>
