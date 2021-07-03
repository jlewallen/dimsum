<template>
    <div>
        <form class="" @submit.prevent="saveForm">
            <div class="form-group row">
                <label class="col-sm-2">Name</label>
                <div class="col-sm-5">
                    <input class="form-control" type="text" v-model="form.name" ref="name" />
                </div>
            </div>
            <div class="form-group row">
                <label class="col-sm-2">Description</label>
                <div class="col-sm-5">
                    <input class="form-control" type="text" v-model="form.desc" ref="desc" />
                </div>
            </div>
            <div class="">
                <input type="submit" value="Save" class="btn btn-primary" />
            </div>
        </form>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Entity, PropertyMap } from "@/http";

export default defineComponent({
    name: "InlineEditor",
    components: {},
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data() {
        return {
            form: {
                name: this.entity.props.map.name.value,
                desc: this.entity.props.map.desc.value,
            },
        };
    },
    mounted() {
        (this.$refs.name as HTMLInputElement).focus();
    },
    methods: {
        async saveForm(): Promise<void> {
            console.log("save");
            await Promise.resolve();
            this.$emit("saved");
        },
    },
});
</script>
