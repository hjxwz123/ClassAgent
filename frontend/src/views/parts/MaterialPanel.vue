<template>
  <ModalPanel :open="true" :title="detail.material.title" @close="$emit('close')">
    <div class="material-head">
      <span class="tag">{{ detail.material.material_type }}</span>
      <span class="tag" :class="detail.material.parse_status === 'ready' ? 'tag-success' : 'tag-warning'">{{ detail.material.parse_status }}</span>
      <span class="tag" :class="detail.material.vector_status === 'ready' ? 'tag-success' : 'tag-warning'">{{ detail.material.vector_status }}</span>
      <a v-if="detail.material.preview_url" class="btn btn-secondary btn-sm" :href="detail.material.preview_url" target="_blank" rel="noreferrer">下载</a>
    </div>
    <div v-if="editable" class="form-row edit-row">
      <input v-model="edit.title" class="input" placeholder="标题" />
      <AppSelect v-model="edit.category" :options="categoryOptions" />
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
        <button v-if="page.audio_url" class="audio-chip" :class="{ playing: playingPageId === page.id }" @click="toggleAudio(page.id, page.audio_url)">
          <Volume2 :size="15" />{{ playingPageId === page.id ? "暂停音频" : "播放音频" }}
        </button>
        <div v-if="editable" class="toolbar">
          <button class="btn btn-secondary btn-sm" @click="$emit('save', page.id, page.script_text || '')">保存</button>
          <button class="btn btn-ai btn-sm" @click="$emit('regen', page.id)">生成</button>
        </div>
      </article>
    </section>
  </ModalPanel>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, reactive, ref, watch } from "vue";
import { Volume2 } from "../../icons";
import AppSelect from "../../components/AppSelect.vue";
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
const categoryOptions = [{ label: "课件", value: "courseware" }, { label: "讲义", value: "handout" }, { label: "练习", value: "exercise" }, { label: "参考", value: "reference" }];
const playingPageId = ref<number | null>(null);
let audio: HTMLAudioElement | null = null;

function toggleAudio(pageId: number, url: string) {
  if (playingPageId.value === pageId && audio) {
    audio.pause();
    playingPageId.value = null;
    return;
  }
  audio?.pause();
  audio = new Audio(url);
  playingPageId.value = pageId;
  audio.addEventListener("ended", () => { playingPageId.value = null; }, { once: true });
  void audio.play();
}
watch(
  () => props.detail.material,
  (material) => Object.assign(edit, { title: material.title, category: material.category }),
  { deep: true }
);
onBeforeUnmount(() => audio?.pause());
</script>

<style scoped>
.material-head { display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4); }
.edit-row { grid-template-columns: minmax(0, 1fr) 180px auto; margin-bottom: var(--space-4); }
.pages { display: grid; gap: var(--space-4); }
.page-card { box-shadow: none; }
.source {
  max-height: 120px;
  overflow: auto;
  margin: 0 0 var(--space-3);
  border-left: 2px solid var(--color-border-default);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
  padding-left: 10px;
  line-height: 1.7;
}
.audio-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  min-height: 44px;
  border: 1px solid var(--color-primary-200);
  border-radius: var(--radius-full);
  background: var(--ca-role-light, var(--color-primary-50));
  color: var(--ca-role-primary-hover, var(--color-primary-700));
  padding: 0 12px;
  transition: transform var(--duration-fast) var(--ease-out), box-shadow var(--duration-fast) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.audio-chip:hover { box-shadow: var(--shadow-sm); border-color: var(--ca-role-primary, var(--color-primary-600)); }
.audio-chip:active { transform: scale(.97); }
.audio-chip.playing { background: var(--ca-role-student-light); color: var(--ca-role-student-primary-hover); }

@media (max-width: 640px) {
  .material-head,
  .toolbar {
    flex-wrap: wrap;
  }

  .edit-row {
    grid-template-columns: 1fr;
  }
}
</style>
