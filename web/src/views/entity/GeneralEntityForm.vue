<template>
    <div class="general-editor">
        <div class="row">
            <div class="col">
                <h4>General</h4>
            </div>
        </div>

        <div class="row">
            <div class="col">
                <form class="" @submit.prevent="saveForm">
                    <div class="form-group row" v-for="field in fields" v-bind:key="field.name">
                        <label class="col-sm-2">{{ field.name }}</label>
                        <div class="col-sm-5">
                            <div v-if="!field.readOnly">
                                <select class="form-control" v-model="form[field.name]" v-if="field.bool">
                                    <option :value="true">yes</option>
                                    <option :value="false">no</option>
                                </select>
                                <input class="form-control" type="text" v-model="form[field.name]" v-else />
                            </div>
                            <div v-else>
                                {{ form[field.name] }}
                            </div>
                        </div>
                    </div>
                    <div class="">
                        <input type="submit" value="Save" class="btn btn-primary" />
                    </div>
                </form>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Person, Entity, PropertyMap } from "@/http";
import store, { SaveEntityDetailsAction } from "@/store";

export interface Field {
    name: string;
    readOnly: boolean;
    numeric: boolean;
    bool: boolean;
}

export default defineComponent({
    name: "GeneralEntityForm",
    components: {},
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data(): { fields: Field[]; field: { name: string }; form: PropertyMap } {
        const readOnly = ["py/object", "created", "touched"];
        const fields = _.map(this.entity.details, (value, key) => {
            return {
                name: key,
                readOnly: readOnly.indexOf(key) >= 0,
                numeric: _.isNumber(value),
                bool: _.isBoolean(value),
                complex: _.isObject(value) || _.isArray(value),
            };
        }).filter((field) => !field.complex);
        return {
            fields: fields,
            field: {
                name: "",
            },
            form: {
                key: this.entity.key,
                ...this.entity.details,
            },
        };
    },
    computed: {
        people(): Person[] {
            return Object.values(store.state.people);
        },
    },
    methods: {
        addDumbField(): void {
            this.fields.push({
                name: "field",
                readOnly: false,
                numeric: false,
                bool: false,
            });
        },
        addBoolField(): void {
            this.fields.push({
                name: "field",
                readOnly: false,
                numeric: false,
                bool: true,
            });
        },
        saveForm(): Promise<any> {
            console.log("entity-editor:saving", this.entity);
            return store.dispatch(new SaveEntityDetailsAction(this.form));
        },
    },
});
</script>

<style scoped></style>
