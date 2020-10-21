<template>
    <div>
        <div v-if="entity">
            <slot :entity="entity"></slot>
        </div>
        <div v-else>Loading</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity } from "@/http";
import store, { NeedEntityAction } from "@/store";

export default defineComponent({
    name: "WithEntity",
    components: {},
    props: {
        entityKey: {
            type: String,
            required: true,
        },
		force: {
			type: Boolean,
			default: false,
		},
    },
    computed: {
        entity(): Entity | null {
            return store.state.entities[this.entityKey];
        },
    },
    mounted(): Promise<void> {
        if (this.force || this.entity == null) {
            return store.dispatch(new NeedEntityAction(this.entityKey));
        }
        return Promise.resolve();
    },
});
</script>

<style scoped></style>
