import CodeMirror from "codemirror";
import "codemirror/addon/fold/brace-fold";
import "codemirror/addon/fold/foldgutter";
import "codemirror/addon/fold/foldgutter.css";
import "codemirror/mode/python/python.js";
import "codemirror/mode/markdown/markdown.js";
import "codemirror/lib/codemirror.css";
import "codemirror/theme/dracula.css";
import "codemirror/theme/blackboard.css";
import "codemirror/keymap/vim.js";
import "codemirror/addon/selection/active-line.js";

import { defineComponent, capitalize, h, markRaw } from "vue";
import ResizeObserver from "resize-observer-polyfill";

import { $theme } from "theme-helper";

const Events: (keyof CodeMirror.EditorEventMap)[] = ["focus", "blur", "scroll"];

export const VCodeMirror = defineComponent({
    name: "VCodeMirror",
    emits: ["update:modelValue", "save", ...Events],
    props: {
        modelValue: {
            type: String,
            required: true,
        },
        mode: {
            type: Object,
            default: () => {
                return { name: "python", json: true };
            },
        },
        readonly: {
            type: Boolean,
            default: false,
        },
        wrap: {
            type: Boolean,
            default: true,
        },
        autoHeight: {
            type: Boolean,
            default: false,
        },
        autoFocus: {
            type: Boolean,
            default: true,
        },
    },
    data(): {
        editor: CodeMirror.Editor | null;
        backupValue: string | null;
        observer: ResizeObserver | null;
        cleanEvent: () => void;
    } {
        return {
            editor: null,
            backupValue: null,
            observer: null,
            cleanEvent: () => {
                console.log("editor:clean");
            },
        };
    },

    render() {
        return h("div", { class: "v-code-mirror" });
    },

    mounted() {
        // eslint-disable-next-line
        (CodeMirror.commands as any).save = () => {
            if (this.editor) {
                this.$emit("save", this.editor.getValue());
            }
        };

        console.log("editor:mode", this.mode);

        const editor = (this.editor = markRaw(
            CodeMirror(this.$el, {
                value: (this.modelValue as unknown) as string,
                mode: this.mode as { name: string },
                theme: $theme.get() === "white" ? "default" : "blackboard",
                readOnly: this.readonly,
                autofocus: this.autoFocus,
                lineWrapping: this.wrap,
                lineNumbers: true,
                foldGutter: true,
                keyMap: "vim",
                gutters: ["CodeMirror-linenumbers", "CodeMirror-foldgutter"],
            })
        ));

        editor.on("changes", () => {
            const value = editor.getValue();
            this.backupValue = value;
            this.$emit("update:modelValue", editor.getValue());
        });

        Events.forEach((x) => {
            const eventName = "on" + capitalize(x);
            if (this.$.vnode.props && typeof this.$.vnode.props[eventName] === "function") {
                editor.on(x, this.$emit.bind(this, x));
            }
        });

        this.cleanEvent = markRaw(
            $theme.onchange(({ detail }) => {
                if (this.editor) {
                    this.editor.setOption("theme", detail === "white" ? "default" : "dracula");
                }
            })
        );

        this.backupValue = (this.modelValue as unknown) as string;

        this.$el._component = this;

        this.observer = new ResizeObserver(function(this: void, entries) {
            entries.forEach((entry) => {
                const that = (entry.target as HTMLDivElement & { _component: typeof VCodeMirror })._component;
                if (that.autoHeight) {
                    that.editor.refresh();
                } else {
                    that.editor.setSize(entry.contentRect.width, entry.contentRect.height);
                }
            });
        });
        this.observer.observe(this.$el);
    },

    beforeUnmount() {
        this.cleanEvent?.();
        if (this.observer) {
            this.observer.unobserve(this.$el);
        }
    },

    focus() {
        if (this.editor) {
            this.editor.focus();
        }
    },
});
