import { defineComponent } from "vue";

import AreaObservation from "./AreaObservation.vue";
import DetailedObservation from "./DetailedObservation.vue";
import PersonalObservation from "./PersonalObservation.vue";
import EntitiesObservation from "./EntitiesObservation.vue";
import Success from "./Success.vue";
import Failure from "./Failure.vue";
import DefaultReply from "./DefaultReply.vue";
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
};
