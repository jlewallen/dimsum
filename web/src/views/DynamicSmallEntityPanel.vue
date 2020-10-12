<template>
    <div>
        <SmallEntityPanel :entity="entity" v-if="entity" @selected="raiseSelected" />
        <div v-else>Loading</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { http, EntityResponse, Entity } from "@/http";
import SmallEntityPanel from "./SmallEntityPanel.vue";

export default defineComponent({
    name: "DynamicSmallEntityPanel",
    components: { SmallEntityPanel },
    props: {
        entityKey: {
            type: String,
            required: true,
        },
    },
    data(): { entity: Entity | null } {
        return {
            entity: null,
        };
    },
    mounted(): Promise<EntityResponse> {
        return http<EntityResponse>({ url: `/entities/${this.entityKey}` }).then((data: EntityResponse) => {
            this.entity = data.entity;
            return data;
        });
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
}
</style>
