<template>
    <div class="response personal-observation"></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { PersonalObservation } from "@/store";

export default defineComponent({
    name: "PersonalObservation",
    props: {
        reply: {
            type: Object as () => PersonalObservation,
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
