<template>
    <a href="#">
        {{ word }}
    </a>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "WikiLink",
    props: {
        word: {
            type: String,
            required: true,
        },
    },
});
</script>
<style scoped></style>
