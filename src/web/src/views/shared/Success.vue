<template>
    <template v-if="reply.message">
        <div class="alert alert-dismissible alert-success">
            <div class="response success" v-if="reply.message">{{ reply.message }}</div>
            <div class="response success" v-if="false">{{ JSON.stringify(reply) }}</div>
        </div>
    </template>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Success } from "@/store";

export default defineComponent({
    name: "Success",
    props: {
        reply: {
            type: Object as () => Success,
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
