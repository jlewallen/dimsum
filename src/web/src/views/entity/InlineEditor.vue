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
            <div class="buttons">
                <input type="submit" value="Save" class="btn btn-primary" />
                <button class="btn btn-secondary" v-on:click="cancel">Cancel</button>
            </div>
        </form>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity, PropertyMap } from "@/http";
import store, { UpdateEntityAction } from "@/store";

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
            const updating = _.clone(this.entity);
            updating.props.map.name.value = this.form.name;
            updating.props.map.desc.value = this.form.desc;
            await store.dispatch(new UpdateEntityAction(updating));
            console.log("save-form");
            this.$emit("dismiss");
        },
        async cancel(e: Event): Promise<void> {
            console.log("cancel");
            this.$emit("dismiss");
            e.preventDefault();
        },
    },
});
</script>
<style>
.buttons input {
    margin-right: 1em;
}
.buttons button {
    margin-right: 1em;
}
</style>
