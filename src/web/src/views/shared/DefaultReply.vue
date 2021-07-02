<template>
    <div class="alert alert-dismissible">
        <div class="response unknown">{{ JSON.stringify(reply) }}</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "DefaultReply",
    props: {
        reply: {
            type: Object as () => Record<string, unknown>,
            required: true,
        },
    },
});
</script>

<style scoped></style>
