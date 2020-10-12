<template>
    <div class="home">
        <div v-if="busy">Busy</div>
        <div v-if="areas">
            <Entities :entities="areas" @selected="entitySelected" />
        </div>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Entities from "./Entities.vue";
import { http, AreasResponse, Entity, Area } from "@/http";

export default defineComponent({
    name: "Home",
    components: {
        Entities,
    },
    data(): { busy: boolean; areas: Area[] } {
        return {
            busy: false,
            areas: [],
        };
    },
    mounted() {
        console.log("home:mounted");
        this.busy = true;
        return http<AreasResponse>({ url: `` })
            .then((data) => {
                this.areas = data.areas;
                return;
            })
            .finally(() => {
                this.busy = false;
            });
    },
    methods: {
        entitySelected(entity: Entity): Promise<any> {
            console.log("home:selected", entity);
            return this.$router.push({ path: `/entities/${entity.key}` });
        },
    },
});
</script>
