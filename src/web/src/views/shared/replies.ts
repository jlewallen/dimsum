import { defineComponent } from "vue";

import AreaObservation from "./AreaObservation.vue";
import DetailedObservation from "./DetailedObservation.vue";
import PersonalObservation from "./PersonalObservation.vue";
import EntitiesObservation from "./EntitiesObservation.vue";
import Success from "./Success.vue";
import Failure from "./Failure.vue";
import DefaultReply from "./DefaultReply.vue";

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
			{{ reply.living.name }} entered from {{ reply.area.name }}
		</div>
	`,
});

const LivingLeftArea = defineComponent({
    name: "LivingLeftArea",
    props: CommonProps,
    template: `
		<div class="response living-left-area">
			{{ reply.living.name }} left to {{ reply.area.name }}
		</div>`,
});

const PlayerSpoke = defineComponent({
    name: "PlayerSpoke",
    props: CommonProps,
    template: `<div class="response player-spoke">{{ reply.living.name }} said "{{ reply.message }}"</div>`,
});

const ItemsHeld = defineComponent({
    name: "ItemsHeld",
    props: CommonProps,
    template: `<div class="response items">{{ reply.living.name }} picked up {{ reply.items }}</div>`,
});

const ItemsDropped = defineComponent({
    name: "ItemsDropped",
    props: CommonProps,
    template: `<div class="response items">{{ reply.living.name }} dropped {{ reply.items }}</div>`,
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
};
