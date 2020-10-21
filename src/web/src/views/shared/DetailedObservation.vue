<template>
    <div class="response detailed-observation"></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { DetailedObservation } from "@/store";

export default defineComponent({
    name: "DetailedObservation",
    props: {
        reply: {
            type: Object as () => DetailedObservation,
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
