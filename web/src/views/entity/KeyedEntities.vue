<template>
    <div class="entities">
        <div v-for="name in Object.keys(entityRefs)" v-bind:key="name">
            <h4>{{ name }}</h4>
            <WithEntity :entityKey="entityRefs[name].key" @selected="raiseSelected" v-slot="withEntity">
                <slot :entity="withEntity.entity">
                    <component v-bind:is="panel" :entity="withEntity.entity" @selected="raiseSelected" />
                </slot>
            </WithEntity>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { EntityRef, Entity } from "@/http";
import SmallEntityPanel from "./SmallEntityPanel.vue";
import WithEntity from "./WithEntity.vue";

export default defineComponent({
    name: "KeyedEntities",
    components: { WithEntity, SmallEntityPanel },
    props: {
        entityRefs: {
            type: Object as () => { [index: string]: EntityRef },
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
