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

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value));
}

function compactMiddle(value: string, maxLength: number) {
  const text = String(value || "-").replace(/\s+/g, " ").trim();
  const length = Math.max(6, Math.floor(maxLength));
  if (text.length <= length) return text;
  const tail = Math.max(3, Math.floor((length - 1) * 0.34));
  const head = Math.max(3, length - tail - 1);
  return `${text.slice(0, head)}…${text.slice(-tail)}`;
}

function horizontalLabelWidth() {
  const width = el.value?.clientWidth || 420;
  return Math.round(clamp(width * 0.38, 132, 220));
}

function horizontalLabelLength() {
  const width = el.value?.clientWidth || 420;
  return Math.round(clamp(width / 15, 8, 16));
}

function tooltipText(value: unknown) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", "\"": "&quot;", "'": "&#39;" }[char] || char));
}

function tooltipFormatter(params: any) {
  const rows = Array.isArray(params) ? params : [params];
  const title = tooltipText(rows[0]?.axisValue ?? rows[0]?.name ?? "");
  return [
    `<strong>${title}</strong>`,
    ...rows.map((row) => `${row.marker || ""}${tooltipText(row.seriesName)}：${tooltipText(row.value)}`)
  ].join("<br/>");
}

function draw() {
  if (!el.value) return;
  chart ||= init(el.value);
  chart.resize();
  const isHorizontal = props.type === "hbar";
  const yLabelWidth = isHorizontal ? horizontalLabelWidth() : 0;
  const yLabelLength = isHorizontal ? horizontalLabelLength() : 0;
  const surface = getTokenColor("--color-bg-surface", "#0F172A");
  const border = getTokenColor("--color-border-default", "#334155");
  const subtle = getTokenColor("--color-border-subtle", "#1E293B");
  const body = getTokenColor("--color-text-body", "#E2E8F0");
  const secondary = getTokenColor("--color-text-secondary", "#CBD5E1");
  chart.setOption({
    color: props.series.map((item) => item.color).filter((color): color is string => Boolean(color)),
    tooltip: { trigger: "axis", axisPointer: { type: isHorizontal ? "shadow" : "line" }, backgroundColor: surface, borderColor: border, textStyle: { color: body }, formatter: tooltipFormatter },
    legend: { top: 0, right: 0, textStyle: { color: secondary, fontSize: 12 } },
    grid: isHorizontal
      ? { left: yLabelWidth + 14, right: 28, top: 42, bottom: 28, containLabel: false }
      : { left: 36, right: 24, top: 42, bottom: 28, containLabel: true },
    xAxis: isHorizontal
      ? { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: subtle } }, axisLabel: { color: secondary, fontSize: 12 } }
      : { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: secondary, fontSize: 12 } },
    yAxis: isHorizontal
      ? { type: "category", data: props.labels, axisTick: { show: false }, axisLabel: { color: secondary, fontSize: 12, interval: 0, width: yLabelWidth, overflow: "truncate", formatter: (value: string) => compactMiddle(value, yLabelLength) } }
      : { type: "value", axisLine: { show: false }, splitLine: { lineStyle: { color: subtle } }, axisLabel: { color: secondary, fontSize: 12 } },
    series: props.series.map((item) => ({
      name: item.name,
      type: props.type === "line" ? "line" : "bar",
      data: item.data,
      smooth: props.type === "line",
      barWidth: props.type === "line" ? undefined : 18,
      areaStyle: props.type === "line" ? { opacity: 0.08 } : undefined,
      itemStyle: { borderRadius: props.type === "line" ? 0 : props.type === "hbar" ? [0, 6, 6, 0] : [6, 6, 0, 0] }
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
