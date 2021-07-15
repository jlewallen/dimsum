import _ from "lodash";
import { defineComponent } from "vue";
import Markdown from "vue3-markdown-it";

export interface Rendered {
    lines: string[];
}

const BasicMarkdown = defineComponent({
    name: "BasicMarkdown",
    props: {
        source: {
            type: Object as () => Rendered,
            required: true,
        },
    },
    components: {
        Markdown,
    },
    template: `<div class="response wiki markdown"><Markdown :source="wikiBody" v-on:click="onClick" /></div>`,
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
            return this.rendered.replace(wikiWord, function(a) {
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

export { BasicMarkdown };
