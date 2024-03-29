<template>
    <div class="inline-editor" @keydown.esc="handleEscape">
        <Tabs :initiallySelected="initiallySelectedTab()" @changed="tabChanged" @close="cancel" ref="tabs">
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
            <Tab title="Behavior">
                <keep-alive>
                    <VCodeMirror v-model="form.behavior" :autoFocus="true" />
                </keep-alive>
            </Tab>
            <Tab title="Help">
                <keep-alive>
                    <VCodeMirror v-model="form.pedia" :autoFocus="true" :mode="{ name: 'markdown' }" />
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
            <span v-if="error.mystery">Honestly, no idea what just happened. You should probably report this.</span>
            <span v-if="error.concurrency">
                Oops, something has gone wrong. The most common cause of this is something in the world made changes to this object before
                you could make yours. When this happens the backend refuses to overwrite those changes with the ones you're making now. See
                <WikiLink word="OptimisticLocking" />
                .
            </span>
            <div v-if="error.python">
                <h5>An error occurred:</h5>

                <h3>
                    <span class="error-line-number">Line {{ error.python.location.line }}</span>
                    {{ error.python.message }}
                </h3>
                <div v-show="false">{{ error.python.exception }}</div>
            </div>
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
import store, { UpdateEntityAction, EntityChange } from "@/store";
import { VCodeMirror } from "@/views/shared/VCodeMirror";
import Tabs from "@/views/shared/Tabs.vue";
import Tab from "@/views/shared/Tab.vue";
import { CommonComponents } from "@/views/shared";
import { ignoringKey } from "@/ux";

export interface ErrorInfo {
    mystery?: boolean;
    concurrency?: boolean;
    python?: {
        message: string;
        location: { line: number; column: number } | null;
        exception?: { context: Record<string, unknown>; stacktrace: string };
    };
}

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
            default: false,
        },
    },
    data(): {
        error: ErrorInfo | null;
        busy: boolean;
        logs: unknown[];
        form: {
            behavior: string;
            pedia: string;
            name: string;
            desc: string;
        };
    } {
        const behavior = this.entity.scopes.behaviors.behaviors.map["b:default"];
        const pedia = (() => {
            if (this.entity.scopes.encyclopedia) {
                return this.entity.scopes.encyclopedia.body;
            }
            return null;
        })();

        return {
            error: null,
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
        console.log("editor:mounted");

        window.addEventListener("keyup", this.keyUp);
        window.addEventListener("keydown", this.keyDown);
    },
    unmounted() {
        console.log("editor:unmounted");

        window.removeEventListener("keyup", this.keyUp);
        window.removeEventListener("keydown", this.keyDown);
    },
    methods: {
        initiallySelectedTab(): number {
            const lastTab = Number(window.localStorage["dimsum:editor:tab"] || 0);
            return this.help ? 2 : lastTab;
        },
        keyDown(data: KeyboardEvent) {
            // console.log("key-down", data, data.keyCode);
            this.keyUp(data);
        },
        keyUp(data: KeyboardEvent) {
            if (ignoringKey(data)) {
                // console.log("ignoring");
                // return;
            }
            if (data.ctrlKey && data.keyCode == 71) {
                // Ctrl-g
                console.log("show-general");
                (this.$refs.tabs as typeof Tabs).selectTab(0);
                data.preventDefault();
                return;
            }
            if (data.ctrlKey && data.keyCode == 66) {
                // Ctrl-b
                console.log("show-behavior");
                (this.$refs.tabs as typeof Tabs).selectTab(1);
                data.preventDefault();
                return;
            }
            if (data.ctrlKey && data.keyCode == 72) {
                // Ctrl-h
                console.log("show-help");
                (this.$refs.tabs as typeof Tabs).selectTab(2);
                data.preventDefault();
                return;
            }
            if (data.ctrlKey && data.keyCode == 76) {
                // Ctrl-l
                console.log("show-logs");
                (this.$refs.tabs as typeof Tabs).selectTab(3);
                data.preventDefault();
                return;
            }
        },
        async save(): Promise<void> {
            const changes: EntityChange[] = [];

            changes.push(new EntityChange("props.map.name.value", this.entity.props.map.name.value, this.form.name));
            changes.push(new EntityChange("props.map.desc.value", this.entity.props.map.desc.value, this.form.desc));
            changes.push(new EntityChange("scopes.encyclopedia.body", this.entity.scopes.encyclopedia?.body || null, this.form.pedia));

            if (this.entity.scopes.behaviors.behaviors.map["b:default"]) {
                const behavior = this.entity.scopes.behaviors.behaviors.map["b:default"] || {};
                changes.push(new EntityChange("scopes.behaviors.behaviors.map.b:default.python", behavior?.python, this.form.behavior));
                changes.push(new EntityChange("scopes.behaviors.behaviors.map.b:default.executable", null, true));
            } else {
                changes.push(
                    new EntityChange("scopes.behaviors.behaviors.map.b:default", null, {
                        "py/object": "scopes.behavior.Behavior",
                        python: this.form.behavior,
                        executable: true,
                        logs: [],
                    })
                );
            }

            console.log("updating entity", this.entity, changes);
            try {
                this.busy = true;
                this.error = null;
                await store.dispatch(new UpdateEntityAction(this.entity, changes));
                this.$emit("dismiss");
            } catch (error) {
                console.log("error", error);
                const berror = error as { response?: { errors: { message: string; locations: { line: number; column: number }[] }[] } };
                if (berror.response) {
                    if (berror.response.errors && berror.response.errors.length > 0) {
                        const pythonError = berror.response.errors[0];
                        console.log("python", pythonError);
                        this.error = {
                            python: {
                                message: pythonError.message,
                                location: pythonError.locations[0] || null,
                                // exception: pythonError.extensions.exception,
                            },
                        };
                    } else {
                        console.log("mystery", berror.response);
                        this.error = {
                            mystery: true,
                        };
                    }
                } else {
                    this.error = {
                        mystery: true,
                    };
                }
            } finally {
                this.busy = false;
            }
        },
        handleEscape(ev: KeyboardEvent) {
            console.log("editor:escape", ev);
            this.$emit("dismiss");
        },
        async tabChanged(selected: number) {
            console.log("editor:tab", selected);
            if (!this.help) {
                window.localStorage["dimsum:editor:tab"] = selected;
            }
        },
        async cancel(ev: Event): Promise<void> {
            console.log("editor:cancel", ev);
            this.$emit("dismiss");
            if (ev) {
                ev.preventDefault();
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
.error-line-number {
    font-size: 70%;
    color: #ffaaaa;
}
</style>
