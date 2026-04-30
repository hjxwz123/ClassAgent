<template>
  <div ref="el" class="admin-chart"></div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { init, use, type ECharts } from "echarts/core";
import { BarChart, LineChart } from "echarts/charts";
import { GridComponent, LegendComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer]);

const props = defineProps<{
  type: "line" | "bar" | "hbar";
  labels: string[];
  series: Array<{ name: string; data: number[]; color?: string }>;
  height?: number;
}>();

const el = ref<HTMLDivElement | null>(null);
const chartHeight = computed(() => `${props.height || 260}px`);
let chart: ECharts | null = null;

function draw() {
  if (!el.value) return;
  chart ||= init(el.value);
  const isHorizontal = props.type === "hbar";
  chart.setOption({
    color: props.series.map((item) => item.color).filter((color): color is string => Boolean(color)),
    tooltip: { trigger: "axis", backgroundColor: "#FFFFFF", borderColor: "#E2E8F0", textStyle: { color: "#334155" } },
    legend: { top: 0, right: 0, textStyle: { color: "#64748B", fontSize: 12 } },
    grid: { left: 36, right: 24, top: 42, bottom: 28, containLabel: true },
    xAxis: isHorizontal
      ? { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: "#F1F5F9" } } }
      : { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: "#64748B", fontSize: 12 } },
    yAxis: isHorizontal
      ? { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: "#64748B", fontSize: 12 } }
      : { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: "#F1F5F9" } }, axisLabel: { color: "#64748B", fontSize: 12 } },
    series: props.series.map((item) => ({
      name: item.name,
      type: props.type === "line" ? "line" : "bar",
      data: item.data,
      smooth: props.type === "line",
      barWidth: props.type === "line" ? undefined : 18,
      areaStyle: props.type === "line" ? { opacity: 0.08 } : undefined,
      itemStyle: { borderRadius: props.type === "line" ? 0 : [6, 6, 0, 0] }
    }))
  });
}

onMounted(() => {
  draw();
  window.addEventListener("resize", draw);
});
watch(() => [props.type, props.labels, props.series], draw, { deep: true });
onBeforeUnmount(() => {
  window.removeEventListener("resize", draw);
  chart?.dispose();
});
</script>

<style scoped>
.admin-chart {
  width: 100%;
  height: v-bind(chartHeight);
}
</style>
