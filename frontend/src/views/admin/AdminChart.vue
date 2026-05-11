<template>
  <div class="admin-chart-wrap">
    <div ref="el" class="admin-chart"></div>
    <div v-if="isEmpty" class="chart-empty">暂无数据</div>
  </div>
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
const isEmpty = computed(() => !props.labels.length || !props.series.some((item) => item.data.some((value) => Number(value) > 0)));
let chart: ECharts | null = null;

function getTokenColor(property: string, fallback: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(property).trim() || fallback;
}

function draw() {
  if (!el.value) return;
  chart ||= init(el.value);
  const isHorizontal = props.type === "hbar";
  const surface = getTokenColor("--color-bg-surface", "#0F172A");
  const border = getTokenColor("--color-border-default", "#334155");
  const subtle = getTokenColor("--color-border-subtle", "#1E293B");
  const body = getTokenColor("--color-text-body", "#E2E8F0");
  const secondary = getTokenColor("--color-text-secondary", "#CBD5E1");
  chart.setOption({
    color: props.series.map((item) => item.color).filter((color): color is string => Boolean(color)),
    tooltip: { trigger: "axis", backgroundColor: surface, borderColor: border, textStyle: { color: body } },
    legend: { top: 0, right: 0, textStyle: { color: secondary, fontSize: 12 } },
    grid: { left: 36, right: 24, top: 42, bottom: 28, containLabel: true },
    xAxis: isHorizontal
      ? { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: subtle } }, axisLabel: { color: secondary, fontSize: 12 } }
      : { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: secondary, fontSize: 12 } },
    yAxis: isHorizontal
      ? { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: secondary, fontSize: 12 } }
      : { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: subtle } }, axisLabel: { color: secondary, fontSize: 12 } },
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
.admin-chart-wrap {
  position: relative;
  min-width: 0;
}
.admin-chart {
  width: 100%;
  height: v-bind(chartHeight);
}
.chart-empty {
  position: absolute;
  inset: 42px 0 0;
  display: grid;
  place-items: center;
  border: 1px dashed var(--ca-color-paper-border, #E6E4DD);
  border-radius: var(--radius-lg, 8px);
  background: rgba(255,255,255,.76);
  color: var(--ca-color-paper-sub, #666560);
  font-size: var(--text-body-sm, 13px);
  pointer-events: none;
}
</style>
