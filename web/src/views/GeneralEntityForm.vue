<template>
    <form class="container form" @submit.prevent="saveForm">
        <div class="row">
            <div class="col-25">
                <label>Name</label>
            </div>
            <div class="col-75">
                <input type="text" v-model="form.name" />
            </div>
        </div>
        <div class="row">
            <div class="col-25">
                <label>Description</label>
            </div>
            <div class="col-75">
                <input type="text" v-model="form.desc" />
            </div>
        </div>
        <div class="row">
            <div class="col-25">
                <label>Presence</label>
            </div>
            <div class="col-75">
                <input type="text" v-model="form.presence" />
            </div>
        </div>
        <div class="row">
            <div class="col-25">
                <label>Owner</label>
            </div>
            <div class="col-75">
                <select v-model="form.owner">
                    <option disabled value="">Please select one</option>
                    <option v-for="person in people" v-bind:key="person.key" :value="person.key">{{ person.details.name }}</option>
                </select>
            </div>
        </div>
        <div class="row actions">
            <input type="submit" value="Save" />
        </div>
    </form>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import { Person, Entity, UpdateEntityPayload } from "@/http";
import store, { SaveEntityAction } from "@/store";

export default defineComponent({
    name: "GeneralEntityForm",
    components: {},
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data(): { form: UpdateEntityPayload } {
        return {
            form: {
                key: this.entity.key,
                name: this.entity.details.name,
                desc: this.entity.details.desc,
                presence: this.entity.details.presence,
                owner: this.entity.owner.key,
            },
        };
    },
    computed: {
        people(): Person[] {
            return Object.values(store.state.people);
        },
    },
    methods: {
        saveForm(): Promise<any> {
            console.log("entity-editor:saving", this.entity);
            return store.dispatch(new SaveEntityAction(this.form));
        },
    },
});
</script>
<style>
/* Style inputs, select elements and textareas */
input[type="text"],
select,
textarea {
    width: 100%;
    padding: 12px;
    border: 1px solid #ccc;
    border-radius: 4px;
    box-sizing: border-box;
    resize: vertical;
}

/* Style the label to display next to the inputs */
label {
    padding: 12px 12px 12px 0;
    display: inline-block;
}

/* Style the submit button */
input[type="submit"] {
    background-color: #4caf50;
    color: white;
    padding: 12px 20px;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    float: right;
}

/* Style the container */
.container {
    border-radius: 5px;
    background-color: #f2f2f2;
    padding: 20px;
}

/* Floating column for labels: 25% width */
.col-25 {
    float: left;
    width: 25%;
    margin-top: 6px;
}

/* Floating column for inputs: 75% width */
.col-75 {
    float: left;
    width: 75%;
    margin-top: 6px;
}

/* Clear floats after the columns */
.row:after {
    content: "";
    display: table;
    clear: both;
}

.row.actions {
    margin-top: 1em;
}

/* Responsive layout - when the screen is less than 600px wide, make the two columns stack on top of each other instead of next to each other */
@media screen and (max-width: 600px) {
    .col-25,
    .col-75,
    input[type="submit"] {
        width: 100%;
        margin-top: 0;
    }
}
</style>
