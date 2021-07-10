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

const CommonProps = {
    reply: {
        type: Object as () => Record<string, unknown>,
        required: true,
    },
};
const LivingEnteredArea = defineComponent({
    name: "LivingEnteredArea",
    props: CommonProps,
    template: `
		<div class="response living-entered-area">
			{{ reply.source.name }} entered from {{ reply.area.name }}
		</div>
	`,
});

const LivingLeftArea = defineComponent({
    name: "LivingLeftArea",
    props: CommonProps,
    template: `
		<div class="response living-left-area">
			{{ reply.source.name }} left to {{ reply.area.name }}
		</div>`,
});

const PlayerSpoke = defineComponent({
    name: "PlayerSpoke",
    props: CommonProps,
    template: `<div class="response player-spoke">{{ reply.source.name }} said "{{ reply.message }}"</div>`,
});

const ItemsHeld = defineComponent({
    name: "ItemsHeld",
    props: CommonProps,
    template: `<div class="response items">{{ reply.source.name }} picked up {{ reply.items }}</div>`,
});

const ItemsDropped = defineComponent({
    name: "ItemsDropped",
    props: CommonProps,
    template: `<div class="response items">{{ reply.source.name }} dropped {{ reply.items }}</div>`,
});

const ItemsObliterated = defineComponent({
    name: "ItemsObliterated",
    props: CommonProps,
    template: `<div class="response items">{{ reply.source.name }} obliterated {{ reply.items }}</div>`,
});

const EntityCreated = defineComponent({
    name: "EntityCreated",
    props: CommonProps,
    template: `<div class="response items">{{ reply.source.name }} created {{ reply.entity.name }}</div>`,
});

import InlineEditor from "@/views/entity/InlineEditor.vue";

const EditingEntity = defineComponent({
    name: "EditingEntity",
    props: CommonProps,
    components: {
        ...CommonComponents,
        InlineEditor,
    },
    template: `<div class="response editor"><WithEntity :entityKey="reply.entity.key" v-slot="withEntity"><InlineEditor :entity="withEntity.entity" @dismiss="$emit('dismiss')" /></WithEntity></div>`,
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
    EditingEntity,
    EntityCreated,
    ScreenCleared,
    ItemsObliterated,
    DynamicMessage,
    Universal,
};
