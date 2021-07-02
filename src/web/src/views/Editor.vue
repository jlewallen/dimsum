<template>
    <div>
        <VCodeMirror :value="code" />
    </div>
</template>

<script>
import { VCodeMirror } from "./VCodeMirror.ts";

export default {
    data() {
        return {
            code: "print('Hello')",
            cmOptions: {
                tabSize: 4,
                lineNumbers: true,
                line: true,
            },
        };
    },
    components: {
        VCodeMirror,
    },
};
</script>
