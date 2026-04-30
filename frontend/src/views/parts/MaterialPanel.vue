<template>
  <ModalPanel :open="true" :title="detail.material.title" @close="$emit('close')">
    <div class="material-head">
      <span class="tag">{{ detail.material.material_type }}</span>
      <span class="tag" :class="detail.material.parse_status === 'ready' ? 'tag-success' : 'tag-warning'">{{ detail.material.parse_status }}</span>
      <span class="tag" :class="detail.material.vector_status === 'ready' ? 'tag-success' : 'tag-warning'">{{ detail.material.vector_status }}</span>
      <a v-if="detail.material.preview_url" class="btn btn-secondary btn-sm" :href="detail.material.preview_url" target="_blank">预览</a>
    </div>
    <div v-if="editable" class="form-row edit-row">
      <input v-model="edit.title" class="input" placeholder="标题" />
      <select v-model="edit.category" class="select">
        <option value="courseware">课件</option>
        <option value="handout">讲义</option>
        <option value="exercise">练习</option>
        <option value="reference">参考</option>
      </select>
      <button class="btn btn-secondary" @click="$emit('update', detail.material.id, edit)">更新</button>
    </div>
    <section class="pages">
      <article v-for="page in localPages" :key="page.id" class="card page-card">
        <div class="card-head">
          <h3 class="card-title">第{{ page.page_number }}页</h3>
          <span class="tag tag-ai">AI</span>
        </div>
        <p class="source">{{ page.page_text }}</p>
        <textarea v-if="editable" v-model="page.script_text" class="textarea"></textarea>
        <p v-else>{{ page.script_text }}</p>
        <audio v-if="page.audio_url" :src="page.audio_url" controls></audio>
        <div v-if="editable" class="toolbar">
          <button class="btn btn-secondary btn-sm" @click="$emit('save', page.id, page.script_text || '')">保存</button>
          <button class="btn btn-ai btn-sm" @click="$emit('regen', page.id)">生成</button>
        </div>
      </article>
    </section>
  </ModalPanel>
</template>

<script setup lang="ts">
import { computed, reactive, watch } from "vue";
import ModalPanel from "../../components/ModalPanel.vue";
import type { MaterialDetail } from "../../types";

const props = defineProps<{ detail: MaterialDetail; editable: boolean }>();
defineEmits<{
  close: [];
  save: [pageId: number, script: string];
  regen: [pageId: number];
  update: [materialId: number, payload: { title: string; category: string }];
}>();
const localPages = computed(() => props.detail.pages);
const edit = reactive({ title: props.detail.material.title, category: props.detail.material.category });
watch(
  () => props.detail.material,
  (material) => Object.assign(edit, { title: material.title, category: material.category }),
  { deep: true }
);
</script>

<style scoped>
.material-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4); }
.edit-row { grid-template-columns: 1fr 180px auto; margin-bottom: var(--space-4); }
.pages { display: grid; gap: var(--space-4); }
.page-card { box-shadow: none; }
.source {
  max-height: 120px;
  overflow: auto;
  margin: 0 0 var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
audio { width: 100%; height: 34px; margin-top: var(--space-3); }
</style>
