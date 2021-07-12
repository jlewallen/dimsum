<template>
    <div class="inline-editor" @keydown.esc="cancel">
        <Tabs @close="cancel">
            <Tab title="General">
                <div class="inline-form">
                    <div class="label">Name</div>
                    <input class="form-control col-sm-2" type="text" v-model="form.name" ref="name" />
                </div>
                <div class="editor-grow">
                    <div class="label">Description</div>
                    <keep-alive>
                        <VCodeMirror v-model="form.desc" :autoFocus="true" :mode="{ name: 'markdown' }" />
                    </keep-alive>
                </div>
            </Tab>
            <Tab title="Help">
                <keep-alive>
                    <VCodeMirror v-model="form.pedia" :autoFocus="true" :mode="{ name: 'markdown' }" />
                </keep-alive>
            </Tab>
            <Tab title="Behavior">
                <keep-alive>
                    <VCodeMirror v-model="form.behavior" :autoFocus="true" />
                </keep-alive>
            </Tab>
            <Tab title="Logs">
                <div class="editor-grow logs">
                    <div v-for="(entry, index) in logs" v-bind:key="index">
                        {{ entry }}
                    </div>
                </div>
            </Tab>
        </Tabs>
        <div class="alert alert-danger" v-if="error">
            Oops, something has gone wrong. The most common cause of this is something in the world made changes to this object before you
            could make yours. When this happens the backend refuses to overwrite those changes with the ones you're making now. I'm trying
            to think up a good solution. See
            <WikiLink word="OptimisticLocking" />
            .
        </div>
        <div class="buttons">
            <button class="btn btn-primary" v-on:click="save" :disabled="busy">Save</button>
            <button class="btn btn-secondary" v-on:click="cancel" :disabled="busy">Cancel</button>
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity } from "@/http";
import store, { UpdateEntityAction } from "@/store";
import { VCodeMirror } from "@/views/shared/VCodeMirror.ts";
import Tabs from "@/views/shared/Tabs.vue";
import Tab from "@/views/shared/Tab.vue";
import { CommonComponents } from "@/views/shared";

export default defineComponent({
    name: "InlineEditor",
    components: {
        ...CommonComponents,
        VCodeMirror,
        Tabs,
        Tab,
    },
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
        help: {
            type: Boolean,
            required: true,
        },
    },
    data() {
        const behavior = this.entity.scopes.behaviors.behaviors.map["b:default"];
        const pedia = (() => {
            if (this.entity.scopes.encyclopedia) {
                return this.entity.scopes.encyclopedia.body;
            }
            return null;
        })();

        return {
            error: false,
            busy: false,
            logs: _.reverse(behavior?.logs || []),
            form: {
                behavior: behavior?.python || "",
                pedia: pedia || "",
                name: this.entity.props.map.name.value,
                desc: this.entity.props.map.desc.value,
            },
        };
    },
    mounted() {
        if (this.form.behavior == "" && this.form.pedia == "") {
            (this.$refs.name as HTMLInputElement).focus();
        }
    },
    methods: {
        async save(): Promise<void> {
            const updating = _.clone(this.entity);
            updating.props.map.name.value = this.form.name;
            updating.props.map.desc.value = this.form.desc;
            updating.scopes.encyclopedia = _.extend(updating.scopes.encyclopedia || {}, {
                body: this.form.pedia,
            });
            const behavior = this.entity.scopes.behaviors.behaviors.map["b:default"] || {};
            updating.scopes.behaviors.behaviors.map["b:default"] = _.merge(
                {
                    "py/object": "scopes.behavior.Behavior",
                },
                behavior,
                {
                    python: this.form.behavior,
                    executable: true,
                }
            );
            console.log("updating entity", updating);
            try {
                this.busy = true;
                this.error = false;
                await store.dispatch(new UpdateEntityAction(updating));
                this.$emit("dismiss");
            } catch (error) {
                console.log("error", error);
                this.error = true;
            } finally {
                this.busy = false;
            }
        },
        async cancel(e: Event): Promise<void> {
            this.$emit("dismiss");
            if (e) {
                e.preventDefault();
            }
        },
    },
});
</script>
<style>
.logs {
    padding: 1em;
    overflow-y: scroll;
    flex-grow: 1;
}
.buttons {
    display: flex;
    flex-direction: row;
    margin-top: 1em;
    padding-left: 1em;
    padding-right: 1em;
}
.buttons * {
    margin-right: 1em;
}
.label {
    color: #8f8f8f;
    padding: 1em;
}
.editor-grow {
    flex-grow: 1;
    display: flex;
    flex-direction: column;
}
.v-code-mirror {
    flex-grow: 1;
}
.inline-form {
    display: flex;
    flex-direction: row;
    align-items: center;
}
</style>
