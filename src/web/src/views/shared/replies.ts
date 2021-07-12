import _ from "lodash";
import { defineComponent } from "vue";

import AreaObservation from "./AreaObservation.vue";
import DetailedObservation from "./DetailedObservation.vue";
import PersonalObservation from "./PersonalObservation.vue";
import EntitiesObservation from "./EntitiesObservation.vue";
import Success from "./Success.vue";
import Failure from "./Failure.vue";
import DefaultReply from "./DefaultReply.vue";
import { Universal } from "@/entity";
import { CommonComponents } from "./index";
import { HistoryEntry } from "@/store";
import Markdown from "vue3-markdown-it";

const CommonProps = {
    entry: {
        type: Object as () => HistoryEntry,
        required: true,
    },
    reply: {
        type: Object as () => Record<string, unknown>,
        required: true,
    },
};

export interface Rendered {
    lines: string[];
}

const BasicMarkdown = defineComponent({
    name: "BasicMarkdown",
    props: {
        source: {
            type: Object as () => string | Rendered,
            required: true,
        },
    },
    components: {
        Markdown,
    },
    template: `<div class="response help"><Markdown :source="wikiBody" v-on:click="onClick" /></div>`,
    computed: {
        rendered(): string {
            if (_.isString(this.source)) {
                return this.source;
            }
            console.log("source", this.source);
            return this.source.lines.join("\n\n");
        },
        wikiBody(): string {
            const wikiWord = /([A-Z]+[a-z]+([A-Z]+[a-z]+)+)/g;
            return this.rendered.replace(wikiWord, function(a, b) {
                return `[${a}](#)`;
            });
        },
    },
    methods: {
        onClick(ev: Event) {
            if (ev.target) {
                const el = ev.target as HTMLElement;
                if (el.innerText) {
                    console.log("navigate", el.innerText);
                    this.$emit("command", { line: `help ${el.innerText}` });
                }
            }
        },
    },
});

const RenderedEntry = defineComponent({
    name: "Help",
    props: {
        entry: {
            type: Object as () => HistoryEntry,
            required: true,
        },
    },
    components: {
        BasicMarkdown,
    },
    template: `<BasicMarkdown :source="entry.rendered" />`,
});

const Help = defineComponent({
    name: "Help",
    props: {
        reply: {
            type: Object as () => { body: string },
            required: true,
        },
    },
    components: {
        BasicMarkdown,
    },
    template: `<BasicMarkdown :source="this.reply.body" />`,
});

const LivingEnteredArea = RenderedEntry;
const LivingLeftArea = RenderedEntry;
const PlayerSpoke = RenderedEntry;
const ItemsHeld = RenderedEntry;
const ItemsDropped = RenderedEntry;
const ItemsObliterated = RenderedEntry;
const EntityCreated = RenderedEntry;

import InlineEditor from "@/views/entity/InlineEditor.vue";

const EditingEntityBehavior = defineComponent({
    name: "EditingEntityBehavior",
    props: CommonProps,
    components: {
        ...CommonComponents,
        InlineEditor,
    },
    template: `<div class="response editor"><WithEntity :entityKey="reply.entity.key" v-slot="withEntity"><InlineEditor :help="false" :entity="withEntity.entity" @dismiss="$emit('dismiss')" /></WithEntity></div>`,
});

const EditingEntityHelp = defineComponent({
    name: "EditingEntityHelp",
    props: CommonProps,
    components: {
        ...CommonComponents,
        InlineEditor,
    },
    template: `<div class="response editor"><WithEntity :entityKey="reply.entity.key" v-slot="withEntity"><InlineEditor :help="true" :entity="withEntity.entity" @dismiss="$emit('dismiss')" /></WithEntity></div>`,
});

const ScreenCleared = defineComponent({
    name: "ScreenCleared",
    props: CommonProps,
    template: `<div class="response clear">Screen Cleared</div>`,
});

const DynamicMessage = defineComponent({
    name: "DynamicMessage",
    props: CommonProps,
    template: `<div class="response dynamic">{{ reply.message.message }} (from {{ reply.source.name }})</div>`,
});

const UniversalString = defineComponent({
    name: "UniversalString",
    props: { value: { type: String, required: true } },
    template: `<span>{{ value }}</span>`,
});

const UniversalLink = defineComponent({
    name: "UniversalLink",
    props: { value: { type: String, required: true } },
    template: `<a :href="value">{{ simple }}</a>`,
    computed: {
        simple(): string {
            const i = this.value.indexOf("?");
            if (i < 0) {
                return this.value;
            }
            return this.value.substring(0, i);
        },
    },
});

function render(value: string): { view: unknown; value: string } {
    if (value.indexOf("http") == 0) {
        return { view: UniversalLink, value: value.toString() };
    }
    return { view: UniversalString, value: value.toString() };
}
const Universal = defineComponent({
    name: "Universal",
    props: {
        reply: {
            type: Object as () => Universal,
            required: true,
        },
    },
    template: `<div class="response universal">
	<template v-for="(p, i) in parsed" v-bind:key="i">
		<component :is="p.view" :value="p.value" />
	</template>
</div>`,
    computed: {
        parsed(): { view: unknown; value: string }[] {
            if (this.reply && this.reply.f && this.reply.kwargs) {
                const re = /(%\([^{}]*\)s)/g;
                const broken = this.reply.f.split(re).map((part) => {
                    const m = part.match(/%\(([^{}]*)\)s/);
                    if (m) {
                        return render(this.reply.kwargs[m[1]]);
                    } else {
                        return { view: UniversalString, value: part };
                    }
                });
                console.log("parsed", broken);
                return broken;
            }
            return [];
        },
    },
});

export default {
    AreaObservation,
    EntitiesObservation,
    DetailedObservation,
    PersonalObservation,
    Success,
    Failure,
    LivingEnteredArea,
    LivingLeftArea,
    PlayerSpoke,
    DefaultReply,
    ItemsHeld,
    ItemsDropped,
    EditingEntityBehavior,
    EditingEntityHelp,
    EntityCreated,
    ScreenCleared,
    ItemsObliterated,
    DynamicMessage,
    Universal,
    Help,
};
