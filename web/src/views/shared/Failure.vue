<template>
    <div class="response failure">{{ response.reply.failure }}</div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { ReplResponse } from "@/store";

export default defineComponent({
    name: "Failure",
    props: {
        response: {
            type: Object as () => ReplResponse,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    methods: {},
});
</script>

<style scoped></style>
