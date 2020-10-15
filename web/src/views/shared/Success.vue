<template>
    <div class="response success">{{ response.reply.success }}</div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { ReplResponse } from "@/store";

export default defineComponent({
    name: "Success",
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
