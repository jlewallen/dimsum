<template>
    <div class="repl" v-if="connected">
        <form v-on:submit.prevent="send">
            <div class="form-group">
                <div class="terminal"></div>
                <input class="form-control" type="text" v-model="command" id="repl-command" autocomplete="off" />
            </div>
        </form>
    </div>
    <div class="repl disconnected" v-else>Disconnected</div>
</template>

<script lang="ts">
import { defineComponent } from "vue";

export default defineComponent({
    name: "Repl",
    props: {
        connected: {
            type: Boolean,
            required: true,
        },
    },
    data(): { command: string } {
        return { command: "" };
    },
    methods: {
        send(): void {
            if (this.command.length > 0) {
                this.$emit("send", this.command);
                this.command = "";
            }
        },
    },
});
</script>
<style scoped>
.form-group {
    margin: 0em;
    display: flex;
    align-items: center;
}

.repl {
    padding: 1em;
}

.form-control {
    background-color: #393e46;
    color: white;
}

.disconnected {
    font-family: "Monaco";
    font-weight: bold;
    color: #8f8f8f;
}

.terminal {
    width: 50px;
    height: 50px;
    background: url("@/images/prompt-100s-126px-gray.png");
    background-size: contain;
}
</style>
