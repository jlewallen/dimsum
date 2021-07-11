<template lang="html">
    <div class="tab" v-if="isActive">
        <slot></slot>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Tab",
    props: {
        title: {
            type: String,
            default: "Tab",
        },
    },
    data(): { isActive: boolean } {
        return {
            isActive: true,
        };
    },
    created(): void {
        if (this.$parent) {
            (this.$parent as any).tabs.push(this);
        }
    },
});
</script>

<style lang="css">
.tab {
    display: flex;
    flex-direction: column;
}
</style>
