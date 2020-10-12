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
import { http, EntityResponse, Entity } from "@/http";

export default defineComponent({
    name: "Entity",
    components: {
        EntityEditor,
    },
    data(): { busy: boolean; entity: Entity | null } {
        return {
            busy: false,
            entity: null,
        };
    },
    computed: {
        key(): string | null {
            return this.$route.params.key?.toString() || null;
        },
    },
    watch: {
        key(): Promise<EntityResponse | null> {
            return this.refresh();
        },
    },
    mounted(): Promise<EntityResponse | null> {
        return this.refresh();
    },
    methods: {
        refresh(): Promise<EntityResponse | null> {
            const key = this.$route.params.key?.toString() || null;
            if (!key) {
                console.log("no key", this.$route);
                return Promise.resolve(null);
            }
            this.busy = true;
            console.log("entity:change", key);
            return http<EntityResponse>({ url: `/entities/${key}` })
                .then((data: EntityResponse) => {
                    console.log("entity:data", data);
                    this.entity = data.entity;
                    return data;
                })
                .finally(() => {
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
