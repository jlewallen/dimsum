<template>
    <div class="response area-observation card">
        <div class="card-body">
            <h4 class="card-title">{{ response.reply.area.where.details.name }}</h4>
            <h6 class="card-subtitle">{{ response.reply.area.where.details.desc }}</h6>
            <div class="people">
                <div v-for="person in response.reply.area.people" v-bind:key="person.key">
                    <TinyEntityPanel :entity="person" />
                </div>
            </div>
            <div class="entities">
                <div v-for="entity in response.reply.area.items" v-bind:key="entity.key">
                    <TinyEntityPanel :entity="entity" />
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { ReplResponse } from "@/store";
import TinyEntityPanel from "../entity/TinyEntityPanel.vue";

export default defineComponent({
    name: "AreaObservation",
    components: {
        TinyEntityPanel,
    },
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

<style scoped>
.people {
    display: flex;
}
.entities {
    display: flex;
}
</style>
