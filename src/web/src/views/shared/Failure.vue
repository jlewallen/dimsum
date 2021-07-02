<template>
    <div class="alert alert-dismissible alert-danger">
        <div class="response failure" v-if="reply.message">{{ reply.message }}</div>
        <div class="response failure" v-else>{{ JSON.stringify(reply) }}</div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Failure } from "@/store";

export default defineComponent({
    name: "Failure",
    props: {
        reply: {
            type: Object as () => Failure,
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
