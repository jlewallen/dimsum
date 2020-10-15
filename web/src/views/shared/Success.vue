<template>
    <div class="alert alert-dismissible alert-success">
        <div class="response success">{{ response.reply.success }}</div>
    </div>
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
