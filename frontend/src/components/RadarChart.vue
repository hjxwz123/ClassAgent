<template>
  <div ref="el" class="radar" role="img" aria-label="知识掌握雷达图"></div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref, watch } from "vue";
import { init, use, type ECharts } from "echarts/core";
import { RadarChart } from "echarts/charts";
import { RadarComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([RadarChart, RadarComponent, CanvasRenderer]);

const props = defineProps<{ items: Array<{ name: string; value: number }> }>();
const el = ref<HTMLDivElement | null>(null);
let chart: ECharts | null = null;

function getTokenColor(property: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(property).trim() || fallback;
}

function draw() {
  if (!el.value) return;
  chart ||= init(el.value);
  const data = props.items.length ? props.items.slice(0, 7) : [{ name: "暂无", value: 0 }];

  const textMuted = getTokenColor("--ca-color-paper-muted", "#999990");
  const borderColor = getTokenColor("--ca-color-paper-border", "#E6E4DD");
  const cardColor = getTokenColor("--ca-color-paper-card", "#FFFFFF");
  const bgColor = getTokenColor("--ca-color-paper-bg", "#F9F8F6");
  const primaryColor = getTokenColor("--ca-role-student-primary", "#00B8D4");

  chart.setOption({
    radar: {
      indicator: data.map((item) => ({ name: item.name, max: Math.max(5, ...data.map((x) => x.value)) })),
      splitNumber: 3,
      axisName: { color: textMuted, fontSize: 12 },
      splitLine: { lineStyle: { color: borderColor } },
      splitArea: { areaStyle: { color: [cardColor, bgColor] } },
      axisLine: { lineStyle: { color: borderColor } }
    },
    series: [{
      type: "radar",
      data: [{ value: data.map((item) => item.value), areaStyle: { color: `${primaryColor}2E` }, lineStyle: { color: primaryColor } }]
    }]
  });
}

onMounted(() => {
  draw();
  window.addEventListener("resize", draw);
});
watch(() => props.items, draw, { deep: true });
onBeforeUnmount(() => {
  window.removeEventListener("resize", draw);
  chart?.dispose();
});
</script>

<style scoped>
.radar { width: 100%; height: 280px; }
</style>
