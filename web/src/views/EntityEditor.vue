<template>
    <div class="entity-editor" v-if="entity">
        <h3>{{ entity.kind }}: {{ entity.details.name }}</h3>
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
        <component v-bind:is="kindSpecific" :entity="entity" />
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import AreaEditor from "./AreaEditor.vue";
import ItemEditor from "./ItemEditor.vue";
import PersonEditor from "./PersonEditor.vue";
import { http, Person, PeopleResponse, EntityResponse } from "@/http";

export default defineComponent({
    name: "EntityEditor",
    components: {
        AreaEditor,
        ItemEditor,
        PersonEditor,
        PlayerEditor: PersonEditor,
    },
    props: {
        entity: {
            type: Object,
            required: true,
        },
    },
    data(): { form: { name: string; desc: string; owner: string }; people: Person[] } {
        return {
            form: {
                name: this.entity.details.name,
                desc: this.entity.details.desc,
                owner: this.entity.owner.key,
            },
            people: [],
        };
    },
    computed: {
        kindSpecific(): string {
            return this.entity.kind + "Editor";
        },
    },
    mounted(): Promise<PeopleResponse> {
        console.log("entity-editor:mounted", this.entity);
        return http<PeopleResponse>({ url: `/people` }).then((data) => {
            this.people = data.people;
            return data;
        });
    },
    methods: {
        saveForm(): Promise<EntityResponse> {
            console.log("entity-editor:saving", this.entity);
            return http<EntityResponse>({ url: `/entities/${this.entity.key}`, method: "POST", data: this.form }).then((data) => {
                return data;
            });
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
