<template>
    <div class="code-editor">
        <textarea class="form-control" :value="modelValue" @input="updated" rows="8" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "CodeEditor",
    props: {
        modelValue: {
            type: String,
            required: true,
        },
    },
    methods: {
        updated(ev: any): void {
            this.$emit("update:modelValue", ev.target.value);
        },
    },
});
</script>
<style scoped></style>
