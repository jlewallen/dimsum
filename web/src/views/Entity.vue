<template>
    <div class="home"></div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
// import HelloWorld from '@/components/HelloWorld.vue'; // @ is an alias to /src

export default defineComponent({
    name: "Entity",
    components: {
        // HelloWorld,
    },
    mounted() {
        const key: string = this.$route.params.key.toString();
        console.log("entity:mounted", key);
    },
});
</script>
