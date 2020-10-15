<template>
    <div class="behavior-editor">
        <h4>Behaviors</h4>

        <div class="row actions">
            <button v-on:click="add" class="button">Add Behavior</button>
            <button v-on:click="save" class="button">Save</button>
        </div>

        <div class="behavior-container">
            <div v-for="behavior in behaviors" v-bind:key="behavior.key" class="behavior">
                <div class="inner">
                    <div class="row">
                        <label>Key</label>
                        <input type="text" v-model="behavior.key" />
                    </div>
                    <div class="row">
                        <label>Lua</label>
                        <CodeEditor v-model="behavior.lua" />
                    </div>
                    <div class="row">
                        <button v-on:click="(ev) => remove(behavior)">Remove</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity } from "@/http";
import store, { SaveEntityBehaviorAction } from "@/store";

import CodeEditor from "./CodeEditor.vue";

export class Behavior {
    constructor(public key: string, public lua: string) {}

    public static makeDefault() {
        const template = `function(s, world, person)
    return nil
end
`;
        const uniq = Math.random();
        return new Behavior(`b:${uniq}:hold:after`, template);
    }
}

export default defineComponent({
    name: "BehaviorEditor",
    components: {
        CodeEditor,
    },
    props: {
        entity: {
            type: Object as () => Entity,
            required: true,
        },
    },
    data(): {
        behaviors: Behavior[];
    } {
        console.log(this.entity);
        return {
            behaviors: _.map(this.entity.behaviors, (value, key) => {
                return new Behavior(key, value!.lua);
            }),
        };
    },
    computed: {},
    methods: {
        add(): void {
            this.behaviors.push(Behavior.makeDefault());
        },
        remove(behavior: Behavior): void {
            this.behaviors = _.without(this.behaviors, behavior);
        },
        save(): Promise<any> {
            const form = _.keyBy(this.behaviors, (b) => b.key);
            console.log("behavior-editor:saving", this.entity);
            return store.dispatch(new SaveEntityBehaviorAction(this.entity.key, form));
        },
    },
});
</script>
<style scoped>
.behavior {
    width: 50em;
    padding: 1em;
}
.behavior-container {
    display: flex;
    flex-wrap: wrap;
}
</style>
