<template>
  <div ref="el" class="radar"></div>
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

function draw() {
  if (!el.value) return;
  chart ||= init(el.value);
  const data = props.items.length ? props.items.slice(0, 7) : [{ name: "暂无", value: 0 }];
  chart.setOption({
    radar: {
      indicator: data.map((item) => ({ name: item.name, max: Math.max(5, ...data.map((x) => x.value)) })),
      splitNumber: 3,
      axisName: { color: "#64748B", fontSize: 12 },
      splitLine: { lineStyle: { color: "#E2E8F0" } },
      splitArea: { areaStyle: { color: ["#FFFFFF", "#F8FAFC"] } },
      axisLine: { lineStyle: { color: "#E2E8F0" } }
    },
    series: [{
      type: "radar",
      data: [{ value: data.map((item) => item.value), areaStyle: { color: "rgba(99, 102, 241, 0.2)" }, lineStyle: { color: "#6366F1" } }]
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
