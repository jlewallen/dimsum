<template>
    <div class="entities">
        <template v-for="ref in entityRefs" v-bind:key="ref.key">
            <WithEntity :entityKey="ref.key" v-slot="withEntity">
                <slot :entity="withEntity.entity">
                    <component v-bind:is="panel" :entity="withEntity.entity" @selected="raiseSelected" />
                </slot>
            </WithEntity>
        </template>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import SmallEntityPanel from "./SmallEntityPanel.vue";
import WithEntity from "./WithEntity.vue";

export default defineComponent({
    name: "Entities",
    components: { WithEntity, SmallEntityPanel },
    props: {
        entityRefs: {
            type: Array as () => EntityRef[],
            required: true,
        },
        panel: {
            type: Object,
            default: SmallEntityPanel,
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
.entities {
    display: flex;
    flex-wrap: wrap;
}
</style>
