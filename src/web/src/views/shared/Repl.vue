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

export default defineComponent({
    name: "Repl",
    props: {},
    data(): { command: string } {
        return { command: "" };
    },
    methods: {
        send(): void {
            this.$emit("send", this.command);
            this.command = "";
        },
    },
});
</script>
<style scoped></style>
