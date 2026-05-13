<template>
  <div ref="containerRef" class="document-preview-surface" :class="{ compact, bare }">
    <div v-if="state === 'loading'" class="document-preview-state loading">
      <span>正在加载原课件</span>
    </div>
    <div v-else-if="state === 'error'" class="document-preview-state error">
      <span>{{ errorText || "原课件预览失败" }}</span>
    </div>
    <div v-else-if="state === 'empty'" class="document-preview-state">
      <span>暂无可预览的原课件</span>
    </div>
    <div v-else ref="stageRef" class="document-preview-stage" :class="stageClass">
      <VuePdfEmbed
        v-if="normalizedType === 'pdf' && pdfSource"
        :key="pdfRenderKey"
        class="document-preview-view document-preview-pdf"
        :source="pdfSource"
        :page="pdfPageProp"
        :scale="pdfScale"
        text-layer
        @loaded="handlePdfLoaded"
        @rendered="handleRendered"
        @loading-failed="handleError"
        @rendering-failed="handlePdfRenderError"
      />
      <VueOfficeDocx
        v-else-if="isDocx && binarySource"
        ref="docxRoot"
        class="document-preview-view docx-view"
        :src="binarySource"
        :options="docxOptions"
        @rendered="handleRendered"
        @error="handleError"
      />
      <VueOfficePptx
        v-else-if="isPptx && pptxSource"
        :key="pptxRenderKey"
        ref="pptxRoot"
        class="document-preview-view pptx-view"
        :src="pptxSource"
        :options="pptxOptions"
        @rendered="handleRendered"
        @error="handleError"
      />
      <div v-else-if="isTextLike" class="document-preview-view text-view lesson-markdown markdown-body" v-html="textHtml"></div>
      <div v-else class="document-preview-state">
        <span>当前文件类型暂不支持原件预览</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, markRaw, nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from "vue";
import VueOfficeDocx from "@vue-office/docx";
import VueOfficePptx from "@vue-office/pptx";
import VuePdfEmbed from "vue-pdf-embed";
import "@vue-office/docx/lib/index.css";
import "vue-pdf-embed/dist/styles/textLayer.css";
import { renderRichText } from "../utils/richText";

type MaterialLike = {
  id?: number | null;
  material_type?: string | null;
  title?: string | null;
  original_filename?: string | null;
  preview_url?: string | null;
};

const props = withDefaults(defineProps<{
  material?: MaterialLike | null;
  compact?: boolean;
  pageNumber?: number | null;
  bare?: boolean;
}>(), {
  material: null,
  compact: false,
  pageNumber: null,
  bare: false,
});

const state = ref<"empty" | "loading" | "ready" | "error">("empty");
const errorText = ref("");
const binaryBytes = shallowRef<Uint8Array | null>(null);
const pptxBytes = shallowRef<Uint8Array | null>(null);
const pdfBytes = shallowRef<Uint8Array | null>(null);
const textSource = ref("");
const requestSeq = ref(0);
const containerRef = ref<HTMLElement | null>(null);
const stageRef = ref<HTMLElement | null>(null);
const docxRoot = ref<any>(null);
const pptxRoot = ref<any>(null);
const pdfDoc = shallowRef<any>(null);
const pdfScale = ref(1);
const pdfFitsHeight = ref(false);
const pdfRenderTick = ref(0);
const previewSize = ref({ width: 0, height: 0 });
let resizeObserver: ResizeObserver | null = null;
let pdfResizeTimer: number | undefined;
let pdfLastRenderSize = { width: 0, height: 0 };
const apiBase = (import.meta.env.VITE_API_BASE_URL || "/api/v1").replace(/\/$/, "");

function widestElement(...elements: Array<HTMLElement | null | undefined>) {
  return elements.reduce((max, element) => {
    const width = element?.clientWidth || 0;
    return width > (max?.clientWidth || 0) ? element || max : max;
  }, elements[0] || null);
}

function basePdfRenderScale() {
  if (props.compact) return 1.15;
  if (props.bare) return 1.5;
  return 1.25;
}

function fallbackPreviewSize() {
  return {
    width: props.compact ? 860 : 1180,
    height: props.compact ? 520 : 700,
  };
}

function readPreviewSize() {
  const fallback = fallbackPreviewSize();
  const element = stageRef.value || containerRef.value;
  if (!element) return fallback;
  const styles = window.getComputedStyle(element);
  const paddingX = Number.parseFloat(styles.paddingLeft || "0") + Number.parseFloat(styles.paddingRight || "0");
  const paddingY = Number.parseFloat(styles.paddingTop || "0") + Number.parseFloat(styles.paddingBottom || "0");
  const width = Math.max(320, Math.floor(element.clientWidth - paddingX));
  const height = Math.max(240, Math.floor(element.clientHeight - paddingY));
  return {
    width: Number.isFinite(width) && width > 0 ? width : fallback.width,
    height: Number.isFinite(height) && height > 0 ? height : fallback.height,
  };
}

function updatePreviewSize() {
  const next = readPreviewSize();
  if (Math.abs(next.width - previewSize.value.width) < 2 && Math.abs(next.height - previewSize.value.height) < 2) return;
  previewSize.value = next;
  schedulePdfRerender();
}

const normalizedType = computed(() => String(props.material?.material_type || "").toLowerCase());
const isDocx = computed(() => ["doc", "docx"].includes(normalizedType.value));
const isPptx = computed(() => ["ppt", "pptx"].includes(normalizedType.value));
const isTextLike = computed(() => ["txt", "md", "markdown"].includes(normalizedType.value));
const isSinglePdfPage = computed(() => normalizedType.value === "pdf" && Number(props.pageNumber || 0) > 0);
const textHtml = computed(() => renderRichText(textSource.value || " "));
const pdfPageProp = computed(() => {
  const pageNumber = Number(props.pageNumber || 0);
  return pageNumber > 0 ? pageNumber : undefined;
});
const stageClass = computed(() => [
  `type-${normalizedType.value}`,
  {
    "fit-height": pdfFitsHeight.value,
    "single-page": isSinglePdfPage.value,
  },
]);
const docxOptions = computed(() => ({
  inWrapper: true,
  breakPages: true,
  ignoreWidth: false,
  ignoreHeight: false,
}));
const pptxOptions = computed(() => ({
  width: previewSize.value.width || fallbackPreviewSize().width,
  height: previewSize.value.height || fallbackPreviewSize().height,
}));
const pptxRenderKey = computed(() => {
  const fallback = fallbackPreviewSize();
  const width = Math.max(1, Math.round((previewSize.value.width || fallback.width) / 16) * 16);
  const height = Math.max(1, Math.round((previewSize.value.height || fallback.height) / 16) * 16);
  return `${props.material?.id || "material"}-${normalizedType.value}-${width}x${height}`;
});
const pdfRenderKey = computed(() => `${props.material?.id || "material"}-${pdfPageProp.value || "all"}-${pdfRenderTick.value}`);

function cloneBytesAsArrayBuffer(bytes: Uint8Array | null) {
  if (!bytes) return null;
  const copy = new Uint8Array(bytes.byteLength);
  copy.set(bytes);
  return copy.buffer;
}

const binarySource = computed(() => cloneBytesAsArrayBuffer(binaryBytes.value));
const pptxSource = computed(() => {
  void pptxRenderKey.value;
  return cloneBytesAsArrayBuffer(pptxBytes.value);
});
const pdfSource = computed(() => {
  void pdfRenderKey.value;
  return cloneBytesAsArrayBuffer(pdfBytes.value);
});

async function loadFile() {
  const material = props.material;
  requestSeq.value += 1;
  const currentSeq = requestSeq.value;
  binaryBytes.value = null;
  pptxBytes.value = null;
  pdfBytes.value = null;
  pdfDoc.value = null;
  pdfScale.value = basePdfRenderScale();
  pdfFitsHeight.value = false;
  pdfRenderTick.value += 1;
  pdfLastRenderSize = { width: 0, height: 0 };
  textSource.value = "";
  errorText.value = "";

  if (!material?.id) {
    state.value = "empty";
    return;
  }

  if (!["pdf", "ppt", "pptx", "doc", "docx", "txt", "md", "markdown"].includes(normalizedType.value)) {
    state.value = "empty";
    return;
  }

  state.value = "loading";
  try {
    const response = await fetch(`${apiBase}/materials/${material.id}/content`, {
      headers: tokenHeaders(),
      credentials: "same-origin",
    });
    if (!response.ok) throw new Error(await resolveResponseError(response));
    if (isTextLike.value) {
      textSource.value = await response.text();
      if (currentSeq !== requestSeq.value) return;
      updatePreviewSize();
      state.value = "ready";
      await nextTick();
      scrollToPage();
      return;
    }
    const buffer = await response.arrayBuffer();
    if (currentSeq !== requestSeq.value) return;
    const bytes = new Uint8Array(buffer);
    if (normalizedType.value === "pdf") {
      pdfBytes.value = bytes;
    } else {
      binaryBytes.value = bytes;
      if (isPptx.value) pptxBytes.value = bytes;
    }
    updatePreviewSize();
    state.value = "ready";
    await nextTick();
    scrollToPage();
  } catch (error) {
    if (currentSeq !== requestSeq.value) return;
    state.value = "error";
    errorText.value = (error as Error).message || "原课件预览失败";
  }
}

function tokenHeaders() {
  const token = localStorage.getItem("class_agent_token") || "";
  return token ? { Authorization: `Bearer ${token}` } : undefined;
}

async function resolveResponseError(response: Response) {
  const contentType = response.headers.get("content-type") || "";
  if (contentType.includes("application/json")) {
    try {
      const payload = await response.json();
      if (typeof payload?.message === "string" && payload.message.trim()) return payload.message.trim();
      if (typeof payload?.detail === "string" && payload.detail.trim()) return payload.detail.trim();
    } catch {
      return "课件文件读取失败";
    }
  }
  return response.status === 404 ? "原课件预览接口未就绪或文件不存在" : "课件文件读取失败";
}

async function handlePdfLoaded(documentProxy: any) {
  pdfDoc.value = documentProxy ? markRaw(documentProxy) : null;
  await updatePdfLayout();
  handleRendered();
}

function isPdfRenderRaceError(error: unknown) {
  const name = (error as Error)?.name || "";
  const message = (error as Error)?.message || "";
  return name === "RenderingCancelledException" || message.includes("Cannot use the same canvas during multiple render() operations");
}

function recordPdfRenderSize() {
  pdfLastRenderSize = readPreviewSize();
}

function schedulePdfRerender(force = false) {
  if (normalizedType.value !== "pdf" || state.value !== "ready" || !pdfBytes.value) return;
  const next = readPreviewSize();
  const widthChanged = Math.abs(next.width - pdfLastRenderSize.width) >= 12;
  const heightChanged = Math.abs(next.height - pdfLastRenderSize.height) >= 12;
  if (!force && !widthChanged && !heightChanged) return;
  if (pdfResizeTimer) window.clearTimeout(pdfResizeTimer);
  pdfResizeTimer = window.setTimeout(() => {
    pdfResizeTimer = undefined;
    recordPdfRenderSize();
    pdfRenderTick.value += 1;
  }, force ? 80 : 180);
}

async function updatePdfLayout() {
  if (normalizedType.value !== "pdf" || !pdfDoc.value || !stageRef.value) return;
  try {
    const pageNumber = Math.max(1, Number(pdfPageProp.value || 1));
    const page = await pdfDoc.value.getPage(pageNumber);
    const viewport = page.getViewport({ scale: 1 });
    const container = containerRef.value;
    const stage = stageRef.value;
    const widthSource = widestElement(stage, container, container?.parentElement as HTMLElement | null) || stage;
    const styles = window.getComputedStyle(stage);
    const paddingX = Number.parseFloat(styles.paddingLeft || "0") + Number.parseFloat(styles.paddingRight || "0");
    const paddingY = Number.parseFloat(styles.paddingTop || "0") + Number.parseFloat(styles.paddingBottom || "0");
    const availableWidth = Math.max(1, widthSource.clientWidth - paddingX);
    const heightSource = widestElement(stage, container) || stage;
    const availableHeight = Math.max(1, heightSource.clientHeight - paddingY);
    const widthScale = availableWidth / viewport.width;
    const renderedHeight = viewport.height * widthScale;
    pdfFitsHeight.value = isSinglePdfPage.value && renderedHeight <= availableHeight + 1;
    pdfScale.value = basePdfRenderScale();
  } catch (error) {
    handleError(error);
  }
}

function scrollToPage() {
  const pageNumber = Number(props.pageNumber || 0);
  if (!pageNumber || state.value !== "ready") return;
  const scroller = stageRef.value || containerRef.value;
  if (!scroller) return;

  if (normalizedType.value === "pdf") {
    if (isSinglePdfPage.value) return;
    const page = scroller.querySelector<HTMLElement>(`.vue-pdf-embed__page[data-page-number="${pageNumber}"]`);
    page?.scrollIntoView({ block: "start", behavior: "smooth" });
    return;
  }

  if (isPptx.value) {
    const slides = scroller.querySelectorAll<HTMLElement>(".pptx-preview-slide-wrapper");
    const target = slides[Math.max(0, pageNumber - 1)];
    target?.scrollIntoView({ block: "start", behavior: "smooth" });
    return;
  }

  if (isDocx.value && pageNumber <= 1) {
    scroller.scrollTo({ top: 0, behavior: "smooth" });
    return;
  }

  if (isTextLike.value && pageNumber <= 1) {
    scroller.scrollTo({ top: 0, behavior: "smooth" });
  }
}

function handleRendered() {
  if (state.value === "loading") state.value = "ready";
  void nextTick(async () => {
    if (normalizedType.value === "pdf") recordPdfRenderSize();
    await updatePdfLayout();
    scrollToPage();
  });
}

function handlePdfRenderError(error: unknown) {
  if (isPdfRenderRaceError(error)) {
    schedulePdfRerender(true);
    return;
  }
  handleError(error);
}

function handleError(error: unknown) {
  state.value = "error";
  errorText.value = (error as Error)?.message || "原课件预览失败";
}

watch(
  () => [props.material?.id, normalizedType.value],
  () => {
    void loadFile();
  },
  { immediate: true }
);

watch(
  () => props.pageNumber,
  () => {
    void nextTick(() => updatePdfLayout());
    void nextTick(() => scrollToPage());
  }
);

watch(
  () => props.compact,
  () => {
    updatePreviewSize();
    void nextTick(() => {
      updatePreviewSize();
      void updatePdfLayout();
    });
  }
);

watch(
  [containerRef, stageRef, () => state.value],
  () => {
    if (!resizeObserver) return;
    resizeObserver.disconnect();
    if (containerRef.value) resizeObserver.observe(containerRef.value);
    if (stageRef.value) resizeObserver.observe(stageRef.value);
    updatePreviewSize();
    void nextTick(async () => {
      updatePreviewSize();
      await updatePdfLayout();
      requestAnimationFrame(() => {
        updatePreviewSize();
        void updatePdfLayout();
      });
    });
  }
);

onMounted(() => {
  resizeObserver = new ResizeObserver(() => {
    updatePreviewSize();
    void updatePdfLayout();
  });
  if (containerRef.value) resizeObserver.observe(containerRef.value);
  if (stageRef.value) resizeObserver.observe(stageRef.value);
  updatePreviewSize();
  void nextTick(() => {
    updatePreviewSize();
    void updatePdfLayout();
  });
});

onBeforeUnmount(() => {
  requestSeq.value += 1;
  if (pdfResizeTimer) window.clearTimeout(pdfResizeTimer);
  resizeObserver?.disconnect();
  resizeObserver = null;
});
</script>

<style scoped>
.document-preview-surface {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: hidden;
  background: var(--color-bg-muted, #f8fafc);
}

.document-preview-stage {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  min-width: 0;
  overflow: auto;
  padding: 12px;
}

.document-preview-stage.type-pdf.single-page.fit-height {
  display: grid;
  place-items: center;
  overflow: hidden;
  padding: 8px;
}

.document-preview-stage.type-docx,
.document-preview-stage.type-doc,
.document-preview-stage.type-pptx,
.document-preview-stage.type-ppt,
.document-preview-stage.type-txt,
.document-preview-stage.type-md,
.document-preview-stage.type-markdown {
  overflow-y: auto;
  overflow-x: hidden;
}

.document-preview-view {
  width: 100%;
}

.document-preview-pdf {
  width: 100%;
  max-width: 100%;
  margin-inline: auto;
}

.document-preview-view.docx-view {
  height: 100%;
  background: #eef2f7;
}

.document-preview-view.pptx-view {
  min-height: 100%;
}

.document-preview-view.text-view {
  min-height: 100%;
  border-radius: var(--radius-lg);
  background: var(--color-bg-surface, #fff);
  color: var(--color-text-body, #334155);
  padding: 24px 28px 32px;
  line-height: 1.78;
}

.document-preview-state {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  color: var(--color-text-secondary, #64748b);
  text-align: center;
}

.document-preview-state span {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 38px;
  max-width: min(100%, 420px);
  border-radius: 999px;
  background: color-mix(in srgb, var(--color-bg-surface, #fff) 94%, var(--color-bg-muted, #f8fafc));
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
  padding: 0 16px;
}

.document-preview-state.loading {
  background: color-mix(in srgb, var(--color-bg-surface, #fff) 84%, transparent);
  backdrop-filter: blur(4px);
}

.document-preview-state.error {
  color: var(--color-danger-700, #b91c1c);
}

.document-preview-surface.compact .document-preview-stage {
  padding: 10px;
}

.document-preview-surface.compact .document-preview-stage.type-pdf.single-page {
  padding: 4px;
}

.document-preview-surface.compact .document-preview-view.text-view {
  padding: 20px 22px 26px;
}

.document-preview-surface.bare {
  background: transparent;
}

.document-preview-surface.bare .document-preview-stage {
  padding: 0;
}

.document-preview-surface.bare .document-preview-stage.type-pdf.single-page.fit-height {
  padding: 0;
}

.document-preview-surface.bare .document-preview-stage.type-pdf:not(.fit-height),
.document-preview-surface.bare .document-preview-stage:not(.single-page) {
  display: block;
}

.document-preview-surface.bare .document-preview-view.text-view {
  border-radius: 0;
  background: transparent;
  padding: 0;
}

.document-preview-surface.bare .document-preview-state.loading {
  background: transparent;
  backdrop-filter: none;
}

.document-preview-surface.bare .document-preview-state.loading span {
  background: rgba(15, 23, 42, 0.76);
  color: #fff;
  box-shadow: 0 16px 34px rgba(15, 23, 42, 0.18);
}

:deep(.vue-office-docx) {
  height: 100%;
}

:deep(.vue-office-docx .docx-wrapper) {
  padding: 0;
}

:deep(.vue-office-docx .docx-wrapper > section.docx) {
  margin: 0 auto 8px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.document-preview-surface.bare :deep(.vue-office-docx .docx-wrapper) {
  background: transparent;
}

.document-preview-surface.bare :deep(.vue-office-docx .docx-wrapper > section.docx) {
  box-shadow: none;
}

:deep(.vue-pdf-embed) {
  display: grid;
  gap: 14px;
  width: 100%;
  justify-items: stretch;
  align-content: start;
}

:deep(.vue-pdf-embed > div) {
  width: 100%;
}

:deep(.vue-pdf-embed__page-layer) {
  display: block;
}

:deep(.vue-pdf-embed__page) {
  width: fit-content;
  max-width: 100%;
  margin: 0 auto;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

:deep(.document-preview-stage.type-pdf.single-page.fit-height .vue-pdf-embed__page) {
  margin: 0 !important;
}

.document-preview-surface.bare :deep(.vue-pdf-embed__page) {
  box-shadow: none;
}

:deep(.vue-pdf-embed__page canvas) {
  display: block;
  width: 100%;
  max-width: none;
  height: auto;
}

:deep(.vue-pdf-embed__text-layer),
:deep(.vue-pdf-embed__text-layer *) {
  line-height: 1 !important;
  letter-spacing: normal !important;
  word-break: normal !important;
  overflow-wrap: normal !important;
  writing-mode: horizontal-tb !important;
  text-orientation: mixed !important;
}

:deep(.vue-pdf-embed__text-layer) {
  user-select: text;
  -webkit-user-select: text;
  font-kerning: none;
  text-size-adjust: none;
}

:deep(.vue-pdf-embed__text-layer span),
:deep(.vue-pdf-embed__text-layer br) {
  white-space: pre !important;
}

:deep(.vue-office-pptx .vue-office-pptx-main) {
  min-height: 100%;
}

:deep(.pptx-preview-wrapper) {
  max-width: 100%;
}

:deep(.pptx-preview-slide-wrapper) {
  margin-bottom: 16px;
}
</style>
