<template>
    <div class="behavior-editor">
        <div class="row">
            <div class="col">
                <h4>Behaviors</h4>
            </div>
        </div>

        <div class="row">
            <div class="col">
                <button v-on:click="add" class="btn btn-secondary">Add Behavior</button>
                <button v-on:click="save" class="btn btn-primary">Save</button>
            </div>
        </div>

        <div class="behavior-container">
            <div v-for="behavior in behaviors" v-bind:key="behavior.id" class="behavior">
                <div>
                    <div class="form-group">
                        <label>Key</label>
                        <input class="form-control" type="text" v-model="behavior.key" />
                    </div>
                    <div class="form-group">
                        <label>Lua</label>
                        <CodeEditor v-model="behavior.lua" />
                    </div>
                    <div class="form-group">
                        <button class="btn btn-secondary" v-on:click="(ev) => remove(behavior)">Remove</button>
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
import { getTimeStamp } from "@/datetime";

import CodeEditor from "../shared/CodeEditor.vue";

export class Behavior {
    constructor(public id: string, public key: string, public lua: string) {}

    public static makeDefault() {
        const template = `function(s, world, person)
    return nil
end
`;
        const uniq = getTimeStamp();
        const key = `b:${uniq}:hold:after`;
        return new Behavior(key, key, template);
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
        return {
            behaviors: _.map(this.entity.behaviors, (value, key) => {
                return new Behavior(key, key, value!.lua);
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
    width: 40em;
    margin-right: 1em;
    margin-bottom: 1em;
}
.behavior-container {
    display: flex;
    flex-wrap: wrap;
}
</style>
