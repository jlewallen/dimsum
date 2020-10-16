<template>
    <div class="response area-observation card">
        <div class="card-body">
            <div class="entities">
                <div v-for="entity in response.reply.entities" v-bind:key="entity.key">
                    <TinyEntityPanel :entity="entity" @selected="(e) => onSelected(e)" />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity, ReplResponse } from "@/store";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";

export default defineComponent({
    name: "EntitiesObservation",
    components: {
        TinyEntityPanel,
    },
    props: {
        response: {
            type: Object as () => ReplResponse,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {},
    methods: {
        onSelected(entity: Entity): void {
            this.$emit("selected", entity);
        },
    },
});
</script>

<style scoped>
.entities {
    display: flex;
}
</style>
