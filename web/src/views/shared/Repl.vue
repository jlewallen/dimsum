<template>
    <div class="repl">
        <form v-on:submit.prevent="send">
            <div class="form-group">
                <input class="form-control" type="text" v-model="command" />
            </div>
        </form>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import store, { ReplAction, ReplResponse } from "@/store";

export default defineComponent({
    name: "Repl",
    props: {},
    data(): { command: string } {
        return { command: "" };
    },
    methods: {
        send(): Promise<any> {
            return store.dispatch(new ReplAction(this.command)).then((response: ReplResponse) => {
                this.command = "";
                this.$emit("response", response);
            });
        },
    },
});
</script>
<style scoped></style>
