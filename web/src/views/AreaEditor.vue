<template>
    <div>
        <div class="entity area">
            <div></div>
        </div>

        <div v-if="adjacent.length > 0" class="adjacent">
            <h4>Adjacent Areas:</h4>
            <div class="entities">
                <DynamicSmallEntityPanel v-for="ref in adjacent" v-bind:key="ref.key" :entityKey="ref.key" @selected="entitySelected" />
            </div>
        </div>

        <div v-if="entity.entities?.length > 0">
            <h4>Also Here:</h4>
            <Entities :entities="entity.entities" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Area, Entity, EntityRef } from "@/http";
import DynamicSmallEntityPanel from "./DynamicSmallEntityPanel.vue";
import Entities from "./Entities.vue";

export default defineComponent({
    name: "AreaEditor",
    components: { DynamicSmallEntityPanel, Entities },
    props: {
        entity: {
            type: Object as () => Area,
            required: true,
        },
    },
    data() {
        return {};
    },
    computed: {
        adjacent(): EntityRef[] {
            return this.entity.entities.filter((e) => e.area).map((e) => e.area!);
        },
    },
    methods: {
        entitySelected(entity: Entity) {
            console.log("area:selected", entity);
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>

<style scoped>
.entity {
}
.entities {
    display: flex;
    flex-wrap: wrap;
}
.adjacent {
    margin-top: 1em;
}
</style>
