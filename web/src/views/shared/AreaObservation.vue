<template>
    <div class="response area-observation">
        <div>{{ response.reply.area.where.details.name }}</div>
        <div>{{ response.reply.area.where.details.desc }}</div>
        <div>
            <div v-for="person in response.reply.area.people" v-bind:key="person.key">
                {{ person.details.name }}
            </div>
        </div>
        <div>
            <div v-for="entity in response.reply.area.items" v-bind:key="entity.key">
                {{ entity.details.name }}
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { ReplResponse } from "@/store";

export default defineComponent({
    name: "AreaObservation",
    props: {
        response: {
            type: Object as () => ReplResponse,
            required: true,
        },
    },
    data(): {} {
        return {};
    },
    computed: {},
    methods: {},
});
</script>

<style scoped></style>
