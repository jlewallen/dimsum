<template lang="html">
    <div :class="{ tabs__dark: true }">
        <ul class="tabs__header">
            <li v-for="(tab, index) in tabs" :key="tab.title" @click="selectTab(index)" :class="{ tab__selected: index == selected }">
                {{ tab.title }}
            </li>
            <li @click="closed" class="close" v-if="false">Close</li>
        </ul>
        <slot></slot>
    </div>
</template>

<script lang="ts">
import { defineComponent } from "vue";
import Tab from "./Tab.vue";

export default defineComponent({
    name: "Tabs",
    props: {
        initiallySelected: {
            type: Number,
            default: 0,
        },
    },
    data(): {
        selected: number;
        tabs: typeof Tab[];
    } {
        return {
            selected: this.initiallySelected,
            tabs: [],
        };
    },
    mounted(): void {
        this.selectTab(this.selected);
    },
    methods: {
        selectTab(i: number): void {
            this.selected = i;
            this.tabs.forEach((tab, index) => {
                tab.isActive = index === i;
            });
            this.$emit("changed", this.selected);
        },
        closed(): void {
            this.$emit("close");
        },
    },
});
</script>

<style lang="css">
ul.tabs__header {
    display: block;
    list-style: none;
    padding: 0;
    border-bottom: 2px solid #dfdfdf;
}

ul.tabs__header > li {
    padding: 10px 30px;
    margin: 0;
    display: inline-block;
    margin-right: 5px;
    cursor: pointer;
}

ul.tabs__header > li.tab__selected {
    font-weight: bold;
}

ul.tabs__header > li.close {
    background-color: transparent;
    padding: 5px;
    margin: 0px;
}

.tab {
    display: inline-block;
    min-height: calc(100vh * 0.5);
    width: 100%;
}

.tabs__dark .tab {
    color: #eee;
}

.tabs__dark li {
    color: #aaa;
    background-color: #14213d;
}

.tabs__dark li.tab__selected {
    color: white;
    background-color: #1d3557;
}
</style>
