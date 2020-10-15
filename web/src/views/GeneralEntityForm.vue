<template>
    <form class="container form" @submit.prevent="saveForm">
        <div class="row" v-for="field in fields" v-bind:key="field.name">
            <div class="col-25">
                <label>{{ field.name }}</label>
            </div>
            <div class="col-75">
                <div v-if="!field.readOnly">
                    <select v-model="form[field.name]" v-if="field.bool">
                        <option :value="true">yes</option>
                        <option :value="false">no</option>
                    </select>
                    <input type="text" v-model="form[field.name]" v-else />
                </div>
                <div v-else>
                    {{ form[field.name] }}
                </div>
            </div>
        </div>
        <div class="row">
            <div class="col-25">
                <label>owner</label>
            </div>
            <div class="col-75">
                <select v-model="form.owner">
                    <option disabled value="">Please select one</option>
                    <option v-for="person in people" v-bind:key="person.key" :value="person.key">{{ person.details.name }}</option>
                    <option value="world">World</option>
                </select>
            </div>
        </div>
        <div class="row actions">
            <!--
            <label>Field Name</label>
            <input type="text" v-model="field.name" />
            <input type="button" class="button" value="Add Yes/No" v-on:click="addBoolField" />
            <input type="button" class="button" value="Add Field" v-on:click="addDumbField" />
			-->
            <input type="submit" value="Save" />
        </div>
    </form>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Person, Entity, UpdateEntityPayload } from "@/http";
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
    data(): { fields: Field[]; field: { name: string }; form: any } {
        const readOnly = ["created", "touched"];
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
                owner: this.entity.owner.key,
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
<style></style>
