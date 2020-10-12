<template>
    <div class="entity">
        <div v-if="busy">Busy</div>
        <div v-if="entity">
            <EntityEditor :entity="entity" v-bind:key="entity.key" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import EntityEditor from "./EntityEditor.vue";
import { Entity } from "@/http";
import store, { NeedEntityAction } from "@/store";

export default defineComponent({
    name: "Entity",
    components: {
        EntityEditor,
    },
    data(): { busy: boolean } {
        return {
            busy: false,
        };
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
            this.busy = true;
            return store.dispatch(new NeedEntityAction(this.key)).finally(() => {
                this.busy = false;
            });
        },
    },
});
</script>

<style scoped>
.home {
}
</style>
