<template>
  <Transition name="modal-pop">
    <div v-if="open && material" class="modal-mask material-preview-mask" @click.self="$emit('close')">
      <article class="material-preview-modal">
        <header class="material-preview-head">
          <div class="material-preview-hero">
            <span class="material-preview-icon">
              <FileText :size="20" />
            </span>
            <div class="material-preview-title">
            <h2>{{ material.title || material.original_filename || "资料预览" }}</h2>
            <small>{{ materialMeta }}</small>
            </div>
          </div>
          <div class="material-preview-controls">
            <div v-if="hasParsedPreview || hasFilePreview" class="material-preview-tabs">
              <button type="button" :class="{ active: mode === 'parsed' }" :disabled="!hasParsedPreview" @click="mode = 'parsed'">解析预览</button>
              <button v-if="hasFilePreview" type="button" :class="{ active: mode === 'file' }" @click="mode = 'file'">原文件</button>
            </div>
            <div class="material-preview-actions">
              <button v-if="material.id" type="button" class="material-preview-action secondary" @click="$emit('download', material)"><Download :size="16" />下载</button>
              <button type="button" class="material-preview-action primary" @click="$emit('close')"><X :size="16" />关闭</button>
            </div>
          </div>
        </header>
        <div class="material-preview-body">
          <div v-if="loading" class="material-preview-loading" role="status" aria-label="资料加载中">
            <LoadingMark :label="false" />
          </div>
          <div v-else-if="mode === 'parsed' && hasParsedPreview" class="material-preview-markdown markdown-body" v-html="parsedPreviewHtml"></div>
          <DocumentPreviewSurface v-else-if="mode === 'file' && hasFilePreview" :material="material" compact />
          <div v-else class="material-preview-empty">
            <FileText :size="30" />
            <span>暂无可预览内容</span>
          </div>
        </div>
      </article>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { Download, FileText, X } from "../icons";
import DocumentPreviewSurface from "./DocumentPreviewSurface.vue";
import LoadingMark from "./LoadingMark.vue";
import type { MaterialDetail } from "../types";
import { extractStructuredText, renderRichText } from "../utils/richText";

type PreviewMaterialLike = {
  id?: number | null;
  title?: string | null;
  original_filename?: string | null;
  material_type?: string | null;
  preview_url?: string | null;
  extracted_text?: string | null;
  size_bytes?: number | null;
};

const props = defineProps<{
  open: boolean;
  item?: PreviewMaterialLike | null;
  detail?: MaterialDetail | null;
  loading?: boolean;
}>();

defineEmits<{ close: []; download: [material: PreviewMaterialLike] }>();

const mode = ref<"parsed" | "file">("parsed");
const material = computed<PreviewMaterialLike | null>(() => props.detail?.material || props.item || null);

function typeText(type?: string | null) {
  return {
    ppt: "PPT",
    pptx: "PPTX",
    pdf: "PDF",
    doc: "DOC",
    docx: "DOCX",
    txt: "Markdown / TXT",
  }[String(type || "").toLowerCase()] || String(type || "资料").toUpperCase();
}

function sizeLabel(size?: number | null) {
  const value = Number(size || 0);
  if (!value) return "未知大小";
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / 1024 / 1024).toFixed(1)} MB`;
  return `${(value / 1024 / 1024 / 1024).toFixed(1)} GB`;
}

const parsedPreviewText = computed(() => {
  const pagesPayload = Array.isArray(props.detail?.pages) ? props.detail.pages : [];
  if (pagesPayload.length) {
    return pagesPayload
      .map((page) => {
        const title = page.page_title || `第${page.page_number || ""}页`;
        const body = extractStructuredText(page.page_text);
        if (!body) return "";
        return `## ${title}\n\n${body}`;
      })
      .filter(Boolean)
      .join("\n\n---\n\n");
  }
  return extractStructuredText(props.detail?.material?.extracted_text || material.value?.extracted_text || "");
});

const parsedPreviewHtml = computed(() => renderRichText(parsedPreviewText.value || "暂无可预览内容"));
const hasParsedPreview = computed(() => Boolean(parsedPreviewText.value.trim()));
const materialMeta = computed(() => material.value ? `${typeText(material.value.material_type)} · ${sizeLabel(material.value.size_bytes)}` : "");
const hasFilePreview = computed(() => ["pdf", "ppt", "pptx", "doc", "docx", "txt", "md", "markdown"].includes(String(material.value?.material_type || "").toLowerCase()) && Boolean(material.value?.id));

watch(
  [() => props.open, () => material.value?.id, hasParsedPreview, hasFilePreview],
  ([open]) => {
    if (!open) return;
    mode.value = hasParsedPreview.value ? "parsed" : hasFilePreview.value ? "file" : "parsed";
  },
  { immediate: true }
);
</script>

<style scoped>
.material-preview-mask {
  z-index: var(--z-modal);
  padding: 20px;
}

.material-preview-modal {
  width: min(1120px, 92vw);
  height: min(820px, 90vh);
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  overflow: hidden;
  border: 1px solid var(--color-border-default);
  border-radius: 28px;
  background:
    linear-gradient(180deg, color-mix(in srgb, var(--color-bg-surface) 96%, var(--color-primary-50) 4%), var(--color-bg-surface));
  box-shadow: var(--shadow-xl);
  padding: 18px;
  gap: 14px;
}

.material-preview-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  min-width: 0;
  writing-mode: horizontal-tb;
  text-orientation: mixed;
  border: 1px solid var(--color-border-default);
  border-radius: 22px;
  background:
    linear-gradient(135deg, color-mix(in srgb, var(--color-bg-surface) 86%, var(--color-primary-50) 14%), var(--color-bg-surface));
  padding: 16px 18px;
}

.material-preview-hero {
  min-width: 0;
  flex: 1;
  display: flex;
  align-items: center;
  flex-direction: row;
  gap: 14px;
}

.material-preview-icon {
  width: 44px;
  height: 44px;
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 14px;
  background: linear-gradient(135deg, var(--color-primary-50), color-mix(in srgb, var(--color-primary-100) 72%, white));
  color: var(--color-primary-700);
  box-shadow: var(--shadow-xs);
}

.material-preview-controls {
  min-width: 0;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  flex-direction: row;
  justify-content: flex-end;
  gap: 12px;
}

.material-preview-actions {
  display: inline-flex;
  align-items: center;
  flex-direction: row;
  gap: 10px;
}

.material-preview-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  min-height: 40px;
  min-width: 92px;
  border: 1px solid transparent;
  border-radius: var(--radius-full);
  padding: 0 15px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  text-decoration: none;
  white-space: nowrap;
  transition:
    background var(--duration-fast) var(--ease-out),
    border-color var(--duration-fast) var(--ease-out),
    color var(--duration-fast) var(--ease-out),
    transform var(--duration-fast) var(--ease-out),
    box-shadow var(--duration-fast) var(--ease-out);
}

.material-preview-action.secondary {
  border-color: var(--color-border-default);
  background: var(--color-bg-surface);
  color: var(--color-text-secondary);
  box-shadow: var(--shadow-xs);
}

.material-preview-action.primary {
  background: linear-gradient(135deg, var(--color-primary-600), var(--color-primary-500));
  color: white;
  box-shadow: 0 12px 24px rgba(14, 116, 144, 0.18);
}

.material-preview-action.secondary:hover {
  border-color: var(--color-border-strong);
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
  box-shadow: var(--shadow-sm);
  transform: translateY(-1px);
}

.material-preview-action.primary:hover {
  color: white;
  transform: translateY(-1px);
  box-shadow: 0 16px 28px rgba(14, 116, 144, 0.24);
}

.material-preview-action:active {
  transform: scale(0.98);
}

.material-preview-action svg {
  color: inherit;
}

.material-preview-title {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 2px;
}

.material-preview-head,
.material-preview-head *,
.material-preview-body,
.material-preview-body * {
  writing-mode: horizontal-tb;
  text-orientation: mixed;
}

.material-preview-title h2 {
  margin: 0;
  overflow: hidden;
  color: var(--color-text-primary);
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: clamp(18px, 2vw, 22px);
  line-height: 1.2;
}

.material-preview-title small {
  color: var(--color-text-muted);
  font-size: 12px;
  line-height: 1.4;
}

.material-preview-tabs {
  display: inline-flex;
  overflow: hidden;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: var(--color-bg-muted);
  padding: 3px;
}

.material-preview-tabs button {
  min-height: 30px;
  border: 0;
  border-radius: 7px;
  background: transparent;
  color: var(--color-text-secondary);
  padding: 0 12px;
  font-size: 12px;
  font-weight: 700;
}

.material-preview-tabs button:hover:not(:disabled) {
  background: var(--color-bg-surface);
  color: var(--color-primary-700);
}

.material-preview-tabs button.active {
  background: var(--color-bg-surface);
  color: var(--color-primary-700);
  box-shadow: var(--shadow-xs);
}

.material-preview-tabs button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.material-preview-body {
  min-height: 0;
  position: relative;
  overflow: hidden;
  border: 1px solid var(--color-border-default);
  border-radius: 22px;
  background: var(--color-bg-muted);
}

.material-preview-loading,
.material-preview-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  align-content: center;
  gap: 10px;
  color: var(--color-text-secondary);
  text-align: center;
}

.material-preview-loading {
  z-index: 2;
  background: color-mix(in srgb, var(--color-bg-surface) 86%, transparent);
  backdrop-filter: blur(4px);
}

.material-preview-loading .loading-mark {
  width: 80px;
  height: 80px;
  filter: drop-shadow(0 14px 24px rgba(15, 23, 42, 0.14));
}

.material-preview-markdown {
  height: 100%;
  overflow: auto;
  background: var(--color-bg-surface);
  color: var(--color-text-body);
  padding: 28px 34px 44px;
  line-height: 1.78;
}

.material-preview-markdown :deep(h1),
.material-preview-markdown :deep(h2),
.material-preview-markdown :deep(h3) {
  margin: 1.1em 0 0.55em;
  color: var(--color-text-primary);
  line-height: 1.35;
}

.material-preview-markdown :deep(h1:first-child),
.material-preview-markdown :deep(h2:first-child),
.material-preview-markdown :deep(h3:first-child) {
  margin-top: 0;
}

.material-preview-markdown :deep(p),
.material-preview-markdown :deep(ul),
.material-preview-markdown :deep(ol),
.material-preview-markdown :deep(blockquote),
.material-preview-markdown :deep(pre),
.material-preview-markdown :deep(table) {
  margin: 0 0 14px;
}

.material-preview-markdown :deep(ul),
.material-preview-markdown :deep(ol) {
  padding-left: 1.35em;
}

.material-preview-markdown :deep(li + li) {
  margin-top: 6px;
}

.material-preview-markdown :deep(code) {
  border-radius: 6px;
  background: var(--color-bg-muted);
  color: var(--color-danger-700);
  padding: 2px 6px;
  font-family: var(--font-family-mono);
  font-size: 0.92em;
}

.material-preview-markdown :deep(pre) {
  overflow: auto;
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-md);
  background: #0F172A;
  color: #E2E8F0;
  padding: 14px 16px;
}

.material-preview-markdown :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}

.material-preview-markdown :deep(blockquote) {
  border-left: 4px solid var(--color-primary-200);
  border-radius: 0 var(--radius-md) var(--radius-md) 0;
  background: var(--color-primary-50);
  color: var(--color-text-secondary);
  padding: 10px 14px;
}

.material-preview-markdown :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

.material-preview-markdown :deep(th),
.material-preview-markdown :deep(td) {
  border: 1px solid var(--color-border-default);
  padding: 9px 11px;
  text-align: left;
  vertical-align: top;
}

.material-preview-markdown :deep(th) {
  background: var(--color-bg-muted);
  color: var(--color-text-primary);
}

.material-preview-markdown :deep(hr) {
  height: 1px;
  border: 0;
  background: var(--color-border-default);
  margin: 22px 0;
}

.material-preview-markdown :deep(.katex-display) {
  overflow-x: auto;
  overflow-y: hidden;
  padding: 8px 0;
}

@media (max-width: 760px) {
  .material-preview-mask {
    padding: 10px;
  }

  .material-preview-modal {
    width: min(100vw - 20px, 100vw);
    height: min(100dvh - 24px, 92vh);
    border-radius: 24px;
    padding: 12px;
  }

  .material-preview-head {
    flex-direction: column;
    align-items: stretch;
    padding: 14px;
  }

  .material-preview-hero,
  .material-preview-controls {
    width: 100%;
  }

  .material-preview-controls {
    flex-direction: column;
    align-items: stretch;
  }

  .material-preview-tabs,
  .material-preview-actions {
    width: 100%;
  }

  .material-preview-tabs button,
  .material-preview-action {
    flex: 1;
  }

  .material-preview-title h2 {
    white-space: normal;
  }

  .material-preview-markdown {
    padding: 22px 18px 30px;
  }
}
</style>
