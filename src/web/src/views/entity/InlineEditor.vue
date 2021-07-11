<template>
    <div class="inline-editor" @keydown.esc="cancel">
        <div class="buttons" v-if="logs.length">
            <span v-on:click="showEditor" :class="{ btn: true, 'btn-primary': editor }">Editor</span>
            <span v-on:click="showLogs" :class="{ btn: true, 'btn-primary': !editor }">Logs</span>
        </div>
        <div class="inline-editor-row" v-if="editor">
            <VCodeMirror v-model="form.behavior" :autoFocus="true" v-if="!help" />
            <VCodeMirror v-model="form.pedia" :autoFocus="true" :mode="{ name: 'markdown' }" v-if="help" />
        </div>
        <div class="inline-editor-row" v-else>
            <div class="logs">
                <div v-for="(entry, index) in logs" v-bind:key="index">
                    {{ entry }}
                </div>
            </div>
        </div>
        <div class="inline-editor-row">
            <form class="inline" @submit.prevent="saveForm">
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
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity, PropertyMap } from "@/http";
import store, { UpdateEntityAction } from "@/store";
import { VCodeMirror } from "@/views/shared/VCodeMirror.ts";

export default defineComponent({
    name: "InlineEditor",
    components: {
        VCodeMirror,
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
        const behavior = this.entity.chimeras.behaviors.behaviors.map["b:default"];
        const pedia = (() => {
            if (this.entity.chimeras.encyclopedia) {
                return this.entity.chimeras.encyclopedia.body;
            }
            return null;
        })();

        console.log("pedia", pedia);

        return {
            editor: true,
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
        showEditor(): void {
            this.editor = true;
        },
        showLogs(): void {
            this.editor = false;
        },
        async saveForm(): Promise<void> {
            const updating = _.clone(this.entity);
            updating.props.map.name.value = this.form.name;
            updating.props.map.desc.value = this.form.desc;
            if (this.help) {
                updating.chimeras.encyclopedia = _.extend(updating.chimeras.encyclopedia || {}, {
                    body: this.form.pedia,
                });
            } else {
                const behavior = this.entity.chimeras.behaviors.behaviors.map["b:default"] || {};
                updating.chimeras.behaviors.behaviors.map["b:default"] = _.merge(
                    {
                        "py/object": "model.scopes.behavior.Behavior",
                    },
                    behavior,
                    {
                        python: this.form.behavior,
                        executable: true,
                    }
                );
            }
            await store.dispatch(new UpdateEntityAction(updating));
            this.$emit("dismiss");
        },
        async cancel(e: Event): Promise<void> {
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
.inline-editor-row {
    padding-bottom: 1em;
}
form.inline {
    padding-left: 1em;
    padding-right: 1em;
}
.buttons {
}
.buttons span {
    padding: 0.2em;
}
.logs {
    height: 300px;
    padding: 1em;
    overflow-y: scroll;
}
</style>
