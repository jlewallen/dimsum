<template>
    <div>
        <WithEntity :entityKey="key" v-slot="withEntity">
            <slot :entity="withEntity.entity"></slot>
        </WithEntity>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import WithEntity from "./WithEntity.vue";

export default defineComponent({
    name: "WithRoutedEntity",
    components: {
        WithEntity,
    },
    computed: {
        key(): string | null {
            return this.$route.params.key?.toString() || null;
        },
    },
});
</script>

<style scoped></style>
