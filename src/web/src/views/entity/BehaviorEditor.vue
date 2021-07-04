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

        <div class="behavior-container container-fluid">
            <div v-for="behavior in behaviors" v-bind:key="behavior.id" class="behavior row">
                <div class="col-6">
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
                <div class="col-6">
                    <div v-for="(log, index) in behavior.logs" v-bind:key="index">
                        {{ log }}
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script lang="ts">
import _ from "lodash";
import { defineComponent } from "vue";
import { Entity, Behavior as BehaviorApi } from "@/http";
import store, { SaveEntityBehaviorAction } from "@/store";
import { getTimeStamp } from "@/datetime";

import CodeEditor from "../shared/CodeEditor.vue";

const HookTemplate = `
function(s, world, area, person)
    return nil
end
`;

export class Behavior {
    constructor(public id: string, public key: string, public lua: string, public logs: string[]) {}

    public static makeDefault() {
        const uniq = getTimeStamp();
        const key = `b:${uniq}:hold:after`;
        return new Behavior(key, key, HookTemplate, []);
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
            behaviors: _.compact(
                (_.map(this.entity.chimeras.behaviors?.behaviors.map || [], (value: BehaviorApi, key) => {
                    if (key != "py/object" && value.lua) {
                        return new Behavior(key, key, value!.lua, value.logs);
                    }
                    return null;
                }) as unknown) as Behavior[]
            ),
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
    /*
    background-color: #efefef;
    border: 1px solid #afafaf;
    border-radius: 5px;
    padding: 1em;
	*/
    margin-top: 1em;
}
.behavior-container {
}
</style>
