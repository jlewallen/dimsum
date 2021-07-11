<template>
    <template v-if="reply.message">
        <div class="response success">
            <div class="" v-if="reply.message">{{ reply.message }}</div>
            <div class="" v-if="false">{{ JSON.stringify(reply) }}</div>
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

<style scoped>
.response.success {
    padding: 1em;
}
</style>
