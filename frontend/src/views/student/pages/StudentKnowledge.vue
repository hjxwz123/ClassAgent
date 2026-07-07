<template>
  <PageTitle title="知识点精讲"><CourseSelect v-model="selectedCourseId" :courses="courses" @reload="ctx.loadActive" @join="ctx.openJoin" /></PageTitle>
  <div class="knowledge-layout">
    <aside class="knowledge-tree">
      <div class="pretty-input"><Search :size="15" /><input v-model="knowledgeKeyword" placeholder="搜索知识点" /></div>
      <strong class="kn-tree-label">章节</strong>
      <button v-for="chapter in courseHome.chapters || []" :key="chapter.id" :class="{ active: selectedChapterId === chapter.id }" @click="selectChapter(chapter.id)"><ChevronRight :size="14" />{{ chapter.title }}</button>
      <strong class="kn-tree-label">知识点</strong>
      <button v-for="item in filteredKnowledge" :key="item.id" class="kn-point" :class="{ active: selectedKnowledgeId === item.id }" @click="selectKnowledge(item.id)"><Layers :size="14" />{{ item.name }}</button>
      <p v-if="!filteredKnowledge.length" class="kn-tree-empty">{{ knowledgeKeyword ? '没有匹配的知识点' : '本章暂无知识点' }}</p>
      <div v-if="weakPoints.length" class="weak-tags">
        <strong><Zap :size="14" />薄弱知识点</strong>
        <button v-for="item in weakPoints.slice(0, 3)" :key="item.knowledge_point" type="button" class="tag tag-danger" title="定位到该知识点" @click="jumpToWeakPoint(item.knowledge_point)">{{ item.knowledge_point }}</button>
      </div>
    </aside>
    <section class="knowledge-content">
      <article class="knowledge-head">
        <h1>{{ selectedKnowledge?.name || '选择知识点' }}</h1>
        <p>所属：{{ ctx.chapterName(selectedKnowledge?.chapter_id) }}</p>
        <span class="tag" :class="knowledgeMasteryClass">{{ knowledgeMasteryText }}</span>
      </article>
      <div class="segmented">
        <button v-for="item in levelItems" :key="item.value" type="button" :class="{ active: knowledgeLevel === item.value }" @click="knowledgeLevel = String(item.value)">{{ item.label }}</button>
      </div>
      <article class="knowledge-body">
        <KnowledgeBlock icon="Quote" title="定义" :content="knowledgeContent.definition" />
        <KnowledgeBlock icon="Layers" title="核心原理" :content="knowledgeContent.principle" ai />
        <KnowledgeBlock icon="Pencil" title="例题解析" :content="knowledgeContent.example" />
        <KnowledgeBlock icon="AlertTriangle" title="常见易错点" warning :content="knowledgeContent.common_mistake" />
        <div class="practice-cta">
          <Sparkles :size="16" />生成练习题
          <button :data-loading="practiceGenerating" :disabled="practiceGenerating" @click="generatePractice(5)">练习5题</button>
          <button :data-loading="practiceGenerating" :disabled="practiceGenerating" @click="generatePractice(10)">练习10题</button>
        </div>
      </article>
    </section>
  </div>
</template>

<script setup lang="ts">
// 知识点精讲页。原为 StudentView 内联区块，抽为独立页面组件。
// 共享的当前课程/章节/薄弱点/课程结构/出题生成经 useStudentCtx 注入；本页自持知识点列表与档位等局部状态。
import { computed, onMounted, ref, watch } from "vue";
import { api } from "../../../api/client";
import { AlertTriangle, ChevronRight, Layers, Pencil, Quote, Search, Sparkles, Zap } from "../../../icons";
import { PageTitle, KnowledgeBlock } from "../components/primitives";
import { CourseSelect } from "../components/course";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
const { selectedCourseId, courses, courseHome, selectedChapterId, selectedKnowledgeId, weakPoints } = ctx;

const knowledge = ref<any[]>([]);
const knowledgeKeyword = ref("");
const knowledgeLevel = ref("standard");
const levelItems = [{ label: "入门", value: "beginner" }, { label: "标准", value: "standard" }, { label: "进阶", value: "advanced" }];

const selectedKnowledge = computed(() => knowledge.value.find((item) => item.id === selectedKnowledgeId.value) || knowledge.value[0] || null);
// 掌握度只依据后端真实薄弱点信号(weak_score / wrong_count)给出定性评估，不编造百分比。
const selectedKnowledgeWeak = computed(() => weakPoints.value.find((item: any) => item.knowledge_point === selectedKnowledge.value?.name) || null);
const knowledgeMasteryAssessed = computed(() => !!selectedKnowledgeWeak.value);
const knowledgeMasteryText = computed(() => {
  if (!knowledgeMasteryAssessed.value) return "暂无评估";
  const impact = Number(selectedKnowledgeWeak.value?.weak_score ?? selectedKnowledgeWeak.value?.wrong_count ?? 0);
  return impact >= 3 ? "薄弱" : "待加强";
});
const knowledgeMasteryClass = computed(() => {
  if (!knowledgeMasteryAssessed.value) return "tag";
  const impact = Number(selectedKnowledgeWeak.value?.weak_score ?? selectedKnowledgeWeak.value?.wrong_count ?? 0);
  return impact >= 3 ? "tag-danger" : "tag-warning";
});
const knowledgeContent = computed(() => selectedKnowledge.value?.content_by_level?.[knowledgeLevel.value] || {});
// 搜索框现在真正过滤知识点列表（此前只绑定不生效）。
const filteredKnowledge = computed(() => {
  const keyword = knowledgeKeyword.value.trim().toLowerCase();
  if (!keyword) return knowledge.value;
  return knowledge.value.filter((item: any) => String(item.name || "").toLowerCase().includes(keyword));
});

async function loadKnowledge() {
  if (!selectedCourseId.value) return;
  knowledge.value = (await ctx.run<any[]>(() => api.get("/learning/knowledge-points", { course_id: selectedCourseId.value, chapter_id: selectedChapterId.value || undefined }))) || [];
  if (!selectedKnowledgeId.value && knowledge.value[0]) selectedKnowledgeId.value = knowledge.value[0].id;
  weakPoints.value = (await ctx.run<any[]>(() => api.get("/learning/weak-points", { course_id: selectedCourseId.value }))) || [];
  if (!courseHome.value.course) await ctx.loadCourseHome();
}
function selectChapter(chapterId: number) {
  // 只改章节，由下方 watch 统一触发加载，避免重复请求。
  selectedChapterId.value = chapterId;
}
// 点选具体知识点（此前左侧只有章节、无法选知识点，正文永远停在每章第一个）。
function selectKnowledge(id: number) {
  selectedKnowledgeId.value = id;
}
// 点薄弱知识点标签定位：当前列表内直接选中；不在（属其它章节）则清章节过滤 + 关键词过滤surface 出来。
function jumpToWeakPoint(name: string) {
  const found = knowledge.value.find((item: any) => item.name === name);
  if (found) { selectedKnowledgeId.value = found.id; return; }
  selectedChapterId.value = null;
  knowledgeKeyword.value = name;
}
const practiceGenerating = ref(false);
async function generatePractice(count: number) {
  if (practiceGenerating.value) return;
  practiceGenerating.value = true;
  try { await ctx.generateKnowledgeQuiz(count, { name: selectedKnowledge.value?.name, chapterId: selectedKnowledge.value?.chapter_id }); }
  finally { practiceGenerating.value = false; }
}

// 换课或换章节（含全局搜索跳转设置的章节）都重新拉取知识点。
watch([selectedCourseId, selectedChapterId], () => { void loadKnowledge(); });
onMounted(loadKnowledge);
</script>
