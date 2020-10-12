<template>
    <div>
        <div class="entity person">
            <div></div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "PersonEditor",
    components: {},
    props: {
        entity: {
            type: Object,
            required: true,
        },
    },
    data() {
        return {};
    },
});
</script>

<style scoped>
.entity {
}
</style>
