<template>
  <section ref="studyRoomRef" class="study-room" :class="{ panelClosed: !aiPanelOpen, compactLesson: compactLessonLayout, fullscreen: lessonFullscreen, 'slide-fitted': slideViewportFitScale < 0.999 }" :style="slideViewportStyle" @mousemove="revealChrome">
    <transition name="study-top">
      <header v-show="chromeVisible || !audioPlaying" class="study-head">
        <div>
          <button class="glass-btn" @click="closeClassroom"><ArrowLeft :size="17" />返回</button>
          <span>{{ activeCourse?.name || classroomLesson?.lesson.title }}</span>
          <ChevronRight :size="14" />
          <strong>{{ classroomLesson?.lesson.title }}</strong>
        </div>
        <code>{{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</code>
        <div>
          <Clock :size="16" />
          <code>{{ studyClock }}</code>
          <button v-if="!compactLessonLayout" class="icon-glass" @click="aiPanelOpen = !aiPanelOpen"><PanelRight :size="18" /></button>
          <button class="icon-glass" @click="settingsOpen = !settingsOpen"><Settings :size="18" /></button>
        </div>
      </header>
    </transition>

    <main ref="studyMainRef" class="study-main" :style="studyLayoutStyle">
      <transition name="thumb-panel">
        <aside v-if="thumbOpen" class="thumb-panel">
          <strong>全部 {{ classroomLesson?.pages.length || 0 }} 页</strong>
          <div class="thumb-grid">
            <button
              v-for="page in classroomLesson?.pages || []"
              :key="page.id"
              :class="{ active: page.page_number === currentPage, learned: page.page_number < currentPage }"
              @click="jumpPage(page.page_number)"
            >
              <span>P{{ page.page_number }}</span>
              <Check v-if="page.page_number < currentPage" :size="12" />
            </button>
          </div>
        </aside>
      </transition>

      <section ref="slideStageRef" class="slide-stage" :class="{ 'has-original-preview': !!classroomOriginalMaterial }" @mouseup="scheduleLessonSelectionCheck" @scroll.passive="hideLessonSelectionMenu">
        <transition :name="classroomOriginalMaterial ? 'fade-slide' : (pageDirection === 'next' ? 'slide-next' : 'slide-prev')" mode="out-in">
          <DocumentPreviewSurface
            v-if="classroomOriginalMaterial"
            :key="`material-${classroomOriginalMaterial.id}`"
            class="lesson-original-preview"
            :material="classroomOriginalMaterial"
            :page-number="currentPage"
            bare
          />
          <div v-else :key="activePage?.id || currentPage" class="slide-card-shell" :style="slideCardShellStyle">
            <article class="slide-card" :class="{ 'slide-card--scaled': slideViewportFitScale < 0.999 }">
              <span class="page-badge">P{{ currentPage }}</span>
              <span class="knowledge-dot" aria-label="AI知识点"><Sparkles :size="14" /></span>
              <h1>{{ activePage?.page_title || `第${currentPage}页` }}</h1>
              <div class="slide-content lesson-markdown" v-html="activePageHtml"></div>
            </article>
          </div>
        </transition>
        <transition name="subtitle">
          <div v-if="subtitleMode !== 'hide' && activeSubtitleText" class="subtitle-line">
            <div class="lesson-markdown" v-html="activeSubtitleHtml"></div>
          </div>
        </transition>
        <transition name="player-pop">
          <div v-show="chromeVisible || !audioPlaying" class="player-bar" :class="{ 'no-audio': !hasActiveAudio }">
            <button class="round-btn ghost" title="上一页" @click="prevPage"><ChevronLeft :size="18" /></button>
            <template v-if="hasActiveAudio">
              <button class="round-btn primary" @click="toggleAudio"><component :is="audioPlaying ? Pause : Play" :size="20" /></button>
            </template>
            <button class="round-btn ghost" title="下一页" @click="nextPage"><ChevronRight :size="18" /></button>
            <template v-if="hasActiveAudio">
              <span class="time">{{ audioTime }}</span>
              <AppSlider v-model="audioProgress" class="range" :min="0" :max="100" @input="seekAudio" />
              <span class="time">{{ audioDuration }}</span>
              <PopoverButton :items="speedItems" :label="`${playbackRate}x`" placement="top" @select="setRate" />
            </template>
            <button class="round-btn ghost" @click="thumbOpen = !thumbOpen"><Grid2X2 :size="18" /></button>
            <button class="round-btn ghost" :title="lessonFullscreen ? '退出全屏' : '进入全屏'" @click="toggleLessonFullscreen"><Maximize :size="18" /></button>
            <audio v-if="activePage?.audio_url" ref="audioRef" :src="activePage.audio_url" @timeupdate="updateAudio" @loadedmetadata="updateAudio" @ended="handleAudioEnded" @play="audioPlaying = true" @pause="audioPlaying = false"></audio>
          </div>
        </transition>
      </section>

      <button
        v-show="aiPanelOpen && !compactLessonLayout"
        class="study-resizer"
        type="button"
        aria-label="拖动调整课件和互动区域宽度"
        title="拖动调整宽度"
        @pointerdown="startLessonResize"
      >
        <span></span>
      </button>

      <aside class="lesson-ai">
        <div class="study-tabs">
          <button :class="{ active: classroomTab === 'script' }" @click="classroomTab = 'script'"><FileText :size="16" />文稿</button>
          <button :class="{ active: classroomTab === 'activity' }" @click="classroomTab = 'activity'"><Zap :size="16" />活动</button>
          <button :class="{ active: classroomTab === 'qa' }" @click="classroomTab = 'qa'"><MessageCircle :size="16" />问答</button>
          <button :class="{ active: classroomTab === 'note' }" @click="classroomTab = 'note'"><ListChecks :size="16" />笔记</button>
        </div>
        <transition name="fade-slide" mode="out-in">
          <section v-if="classroomTab === 'script'" key="script" class="script-view">
            <div class="sticky-tools"><span>当前页 {{ currentPage }} / {{ classroomLesson?.pages.length || 1 }}</span><button @click="copyText(activeScriptText || activePageText)"><Copy :size="14" />复制</button></div>
            <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
            <div class="reading lesson-markdown" v-html="activeScriptHtml"></div>
          </section>
          <section v-else-if="classroomTab === 'activity'" key="activity" class="activity-view">
            <div class="activity-hero">
              <span><Sparkles :size="16" />页面活动层</span>
              <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
              <p>{{ pageSummaryActivity?.summary || pageSummaryActivity?.content || activePageText.slice(0, 120) || '暂无页面摘要' }}</p>
            </div>
            <div v-if="learningObjectiveItems.length || keyPointItems.length" class="activity-band">
              <section v-if="learningObjectiveItems.length">
                <h3><Layers :size="15" />目标</h3>
                <ul><li v-for="item in learningObjectiveItems" :key="item">{{ item }}</li></ul>
              </section>
              <section v-if="keyPointItems.length">
                <h3><Zap :size="15" />重点</h3>
                <ul><li v-for="item in keyPointItems" :key="item">{{ item }}</li></ul>
              </section>
            </div>
            <div v-if="problemTemplateActivities.length" class="activity-section">
              <h3><Pencil :size="16" />例题模板</h3>
              <article v-for="item in problemTemplateActivities" :key="item.id" class="activity-item example">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <div v-if="misconceptionActivities.length" class="activity-section">
              <h3><Shield :size="16" />易错点</h3>
              <article v-for="item in misconceptionActivities" :key="item.id" class="activity-item mistake">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <div v-if="quickCheckActivities.length" class="activity-section">
              <h3><MessageCircle :size="16" />快问</h3>
              <button v-for="item in quickCheckActivities" :key="item.id" class="activity-question" type="button" @click="sendQuickClass(activityQuestion(item))">{{ activityQuestion(item) }}</button>
            </div>
            <div v-if="discussionDemoActivities.length" class="activity-section">
              <h3><Presentation :size="16" />讨论与演示</h3>
              <article v-for="item in discussionDemoActivities" :key="item.id" class="activity-item">
                <strong>{{ item.title }}</strong>
                <div class="lesson-markdown" v-html="activityHtml(item)"></div>
              </article>
            </div>
            <EmptyState v-if="!activePageActivities.length" text="本页暂无活动层，重新解析课件后会生成结构化教学对象" />
          </section>
          <section v-else-if="classroomTab === 'qa'" key="qa" class="class-chat">
            <div class="class-chat-scroll">
              <div v-if="classConversationLoading && !classMessages.length" class="chat-local-loading compact"><LoadingMark :label="false" /></div>
              <ChatList :messages="classMessages" :thinking="classThinking" :user-avatar-url="currentAvatarUrl" :user-name="profileForm.nickname || user.nickname" @toggle-thought="toggleThought" @copy="copyText" @feedback="feedbackQaMessage" @jump-source="jumpToSource" />
            </div>
            <div class="class-chat-dock">
              <div v-if="classQaAttachments.length" class="qa-attachment-strip compact">
                <div v-for="(item, index) in classQaAttachments" :key="`${item.url}-${index}`" class="qa-attachment-chip">
                  <img :src="item.url" alt="" />
                  <span>{{ item.filename || '图片' }}</span>
                  <button type="button" @click="removeQaAttachment('class', index)"><X :size="13" /></button>
                </div>
              </div>
              <div v-if="lessonAskContext" class="lesson-qa-selection-context" :title="lessonAskContext">
                <Quote :size="14" />
                <span>{{ lessonAskContextPreview }}</span>
                <button type="button" aria-label="移除选中文本" @click="clearLessonAskContext"><X :size="13" /></button>
              </div>
              <form class="chat-input compact" @submit.prevent="askInClass">
                <input ref="classQaImageInput" class="qa-image-input" type="file" accept="image/*" @change="handleQaImageChange($event, 'class')" />
                <button type="button" class="attach-btn" :data-loading="classQaImageUploading" :disabled="classThinking || (classConversationLoading && !classMessages.length) || classQaImageUploading || classQaAttachments.length >= 3" title="上传图片" @click="classQaImageInput?.click()"><Camera :size="17" /></button>
                <MathTextField
                  ref="classMathField"
                  v-model="classQuestion"
                  :placeholder="classQuestionPlaceholder"
                  @submit="askInClass"
                />
                <button v-if="classThinking" type="button" class="send-btn send-btn-stop" title="停止生成" aria-label="停止生成" @click="stopClassGeneration"><Square :size="16" /></button>
                <button v-else :disabled="(!classQuestion.trim() && !classQaAttachments.length) || (classConversationLoading && !classMessages.length) || classQaImageUploading" class="send-btn"><Send :size="18" /></button>
              </form>
              <div class="quick-tags lesson-quick-tags">
                <button v-for="item in quickPageQuestions" :key="item" :title="item" @click="sendQuickClass(item)">{{ item }}</button>
              </div>
            </div>
          </section>
          <section v-else key="note" class="note-view">
            <div class="note-tools" role="toolbar" aria-label="笔记格式工具">
              <button type="button" title="加粗" @click="formatNote('bold')"><strong>B</strong></button>
              <button type="button" title="斜体" @click="formatNote('italic')"><i>I</i></button>
              <button type="button" title="标记重点" @click="formatNote('mark')"><Flag :size="14" />标记</button>
              <span class="note-state" :class="{ dirty: noteState !== '已保存' }">{{ noteState }}</span>
            </div>
            <textarea ref="pageNoteArea" v-model="pageNote" class="note-editor" placeholder="记录你对这一页的理解、疑问或总结..." @input="queueNoteSave"></textarea>
            <footer class="note-footer"><button class="btn btn-primary btn-sm" :data-loading="noteState === '保存中'" :disabled="noteState === '保存中'" @click="saveCurrentNote">保存笔记</button><span>{{ noteSavedAt }}</span></footer>
          </section>
        </transition>
      </aside>
    </main>

    <transition name="selection-pop">
      <div
        v-if="lessonSelectionMenu.open"
        class="lesson-selection-popover"
        :style="lessonSelectionMenuStyle"
        @pointerdown.stop
        @mousedown.prevent.stop
      >
        <button type="button" @click="explainLessonSelection">解释</button>
        <button type="button" @click="prepareLessonSelectionQuestion">提问</button>
      </div>
    </transition>

    <Teleport to="body">
      <transition name="modal-pop">
        <div v-if="completeOpen" class="modal-mask student-modal-scope">
          <article class="complete-modal">
            <div class="confetti"><i v-for="n in 28" :key="n" :style="confettiStyle(n)"></i></div>
            <CheckCircle :size="56" />
            <h2>恭喜完成</h2>
            <p>{{ classroomLesson?.lesson.title }}</p>
            <div class="done-stats"><span>本次 {{ Math.max(1, Math.round(studySeconds / 60)) }} 分钟</span><span>{{ classroomLesson?.pages.length || 0 }} 页</span><span>{{ classMessages.filter((m) => m.role === 'user').length }} 次提问</span></div>
            <div class="ai-summary"><Info :size="16" />{{ completionSummary }}</div>
            <footer><button class="btn btn-primary" @click="nextLessonAfterComplete">下一课时</button><button class="btn btn-secondary" @click="returnCourse">回课程</button><button class="btn btn-ghost" @click="openQuizSelection('practice')">做练习</button></footer>
          </article>
        </div>
      </transition>
    </Teleport>

    <transition name="fade-slide">
      <div v-if="settingsOpen" class="settings-pop">
        <button :class="{ active: subtitleMode === 'full' }" @click="subtitleMode = 'full'">完整字幕</button>
        <button :class="{ active: subtitleMode === 'keyword' }" @click="subtitleMode = 'keyword'">关键词</button>
        <button :class="{ active: subtitleMode === 'hide' }" @click="subtitleMode = 'hide'">隐藏字幕</button>
      </div>
    </transition>
  </section>
</template>

<script setup lang="ts">
// 课堂/上课模式（study-room）：幻灯舞台、文稿/活动/问答/笔记标签页、音频条、翻页、缩略图、
// 全屏、划词提问、课堂问答流式与页笔记。原为 StudentView 外壳内联区块，抽为独立页面组件。
// 由外壳以 <StudentLessonStudy v-else-if="classroomOpen" /> 渲染：外壳持有课时加载/路由/进度
// (loadLessonStudyRoute/openLesson/leaveClassroom/saveProgress/翻页/学习计时) 并经 ctx 注入，
// 组件仅在课时已加载且 classroomOpen 时挂载，自持课堂内交互态（音频、幻灯适配、划词、笔记、
// 课堂问答输入与流式），复用 useQaEngine（课堂问答 follow=false，滚动跟随钩子为空实现）。
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  ArrowLeft, Camera, Check, CheckCircle, ChevronLeft, ChevronRight, Clock, Copy, FileText, Flag,
  Grid2X2, Info, Layers, ListChecks, Maximize, MessageCircle, PanelRight, Pause, Pencil, Play,
  Presentation, Quote, Send, Settings, Shield, Sparkles, Square, X, Zap,
} from "../../../icons";
import { api } from "../../../api/client";
import { extractStructuredText, renderRichText } from "../../../utils/richText";
import MathTextField from "../../../components/MathTextField.vue";
import { timeLabel, timestampMs, relativeTime } from "../../../utils/datetime";
import type { Material, PageActivity } from "../../../types";
import AppSlider from "../../../components/AppSlider.vue";
import DocumentPreviewSurface from "../../../components/DocumentPreviewSurface.vue";
import LoadingMark from "../../../components/LoadingMark.vue";
import { PopoverButton } from "../components/PopoverButton";
import { EmptyState } from "../components/primitives";
import ChatList from "../components/ChatList";
import { useQaEngine, type QaAttachment, type ChatMessage } from "../useQaEngine";
import { useStudentCtx } from "../context";

const ctx = useStudentCtx();
// 共享来源（外壳持有并经 ctx 注入）：身份/课程作用域、请求包装与通知、导航与打开其它课时/练习；
// 课时数据与路由/进度耦合状态（课时详情、当前页、翻页方向、学习秒数、完成弹窗、字幕/缩略/划词菜单）、
// 翻页与进度保存、离开课堂/回课程/下一课时、来源页解析、问答通用助手（复制/反馈/思考展开/记录转消息）。
const {
  user, currentAvatarUrl, profileForm, selectedCourseId, courses, run, notice, go, openLesson, openQuizSelection,
  classroomOpen, classroomLesson, currentPage, pageDirection, studySeconds, completeOpen, settingsOpen, thumbOpen,
  lessonSelectionMenu, pendingSourcePageNumber, pendingSourcePageId,
  jumpPage, prevPage, nextPage, saveProgress, hideLessonSelectionMenu, closeClassroom, returnCourse,
  nextLessonAfterComplete, resolveSourcePageNumber, copyText, feedbackQaMessage, toggleThought, qaRecordsToMessages,
} = ctx;

// —— 课件与互动区域宽度分栏（拖拽调整，落 localStorage）——
const LESSON_LAYOUT_STORAGE_KEY = "student_lesson_panel_ratio_v2";
const LESSON_LAYOUT_DEFAULT_RATIO = 0.24;
const LESSON_LAYOUT_MIN_RATIO = 0.18;
const LESSON_LAYOUT_MAX_RATIO = 0.62;
const LESSON_RESIZER_WIDTH = 18;
const LESSON_LAYOUT_MIN_RIGHT = 336;

function savedLessonPanelRatio() {
  const value = Number(localStorage.getItem(LESSON_LAYOUT_STORAGE_KEY));
  return Number.isFinite(value) && value > 0 ? Math.min(LESSON_LAYOUT_MAX_RATIO, Math.max(LESSON_LAYOUT_MIN_RATIO, value)) : LESSON_LAYOUT_DEFAULT_RATIO;
}

const studyRoomRef = ref<HTMLElement | null>(null);
const studyMainRef = ref<HTMLElement | null>(null);
const slideStageRef = ref<HTMLElement | null>(null);
const slideCardMeasureRef = ref({ width: 0, height: 0 });
const lessonPanelRatio = ref(savedLessonPanelRatio());
const lessonPanelRatioCustomized = ref(false);
const lessonResizeActive = ref(false);
const compactLessonLayout = ref(false);
const lessonFullscreen = ref(false);
const lessonLayoutWidth = ref(typeof window === "undefined" ? 0 : window.innerWidth || 0);
const slideViewportFitScale = ref(1);
const classroomTab = ref<"script" | "activity" | "qa" | "note">("script");
const classMessages = ref<ChatMessage[]>([]);
const classQuestion = ref("");
const classThinking = ref(false);
let classAbortController: AbortController | null = null;
const classConversationLoading = ref(false);
const classConversationId = ref<number | null>(null);
const classQaImageInput = ref<HTMLInputElement | null>(null);
const classQaAttachments = ref<QaAttachment[]>([]);
const classQaImageUploading = ref(false);
// 公式输入栏（文本框 + 内联公式块）引用，供聚焦等使用；fx 公式编辑器已内聚在组件内。
const classMathField = ref<InstanceType<typeof MathTextField> | null>(null);
const lessonAskContext = ref("");
const aiPanelOpen = ref(true);
const chromeVisible = ref(true);
const subtitleMode = ref<"full" | "keyword" | "hide">("hide");
const audioRef = ref<HTMLAudioElement | null>(null);
const audioPlaying = ref(false);
const playbackRate = ref(1);
const audioProgress = ref(0);
const pageNote = ref("");
const pageNoteArea = ref<HTMLTextAreaElement | null>(null);
const noteState = ref("已保存");
const noteSavedAt = ref("尚未保存");
let chromeTimer: number | undefined;
let noteTimer: number | undefined;
let lessonSelectionTimer: number | undefined;
let classConversationLoadSeq = 0;
let slideStageResizeObserver: ResizeObserver | undefined;

const speedItems = ["0.5", "0.75", "1", "1.25", "1.5", "2"].map((value) => ({ label: `${value}x`, value }));

// QA 流式引擎（课堂问答专用实例）。课堂问答均以 follow=false 入缓冲，跟随滚动钩子不会被调用，
// 因此传入空实现即可（与外壳全局问答共用引擎时课堂分支行为一致）。
const {
  patchChatMessage, flushQaDeltas, queueQaDelta, applyQaStreamEvent,
} = useQaEngine({ isNearLatest: () => false, keepAtLatest: () => {} });

const activeCourse = computed(() => courses.value.find((course) => course.id === selectedCourseId.value) || courses.value[0] || null);
const activePage = computed(() => classroomLesson.value?.pages.find((page) => page.page_number === currentPage.value) || classroomLesson.value?.pages[0] || null);
const classroomOriginalMaterial = computed<Material | null>(() => {
  const material = classroomLesson.value?.material || null;
  if (!material?.id) return null;
  const type = String(material.material_type || "").toLowerCase();
  return ["pdf", "ppt", "pptx", "doc", "docx", "txt", "md", "markdown"].includes(type) ? material : null;
});
const hasActiveAudio = computed(() => Boolean(activePage.value?.audio_url));
const lessonSelectionMenuStyle = computed(() => ({
  left: `${lessonSelectionMenu.x}px`,
  top: `${lessonSelectionMenu.y}px`,
}));
const lessonAskContextPreview = computed(() => selectionPreviewText(lessonAskContext.value));
const classQuestionPlaceholder = computed(() => lessonAskContext.value ? "需要问点什么？" : "问问 AI 这一页...");
const studyLayoutStyle = computed(() => {
  if (compactLessonLayout.value || !aiPanelOpen.value) return undefined;
  const totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0;
  const bounds = lessonPanelBounds(totalWidth);
  const ratio = clampLessonPanelRatio(lessonPanelRatio.value, totalWidth);
  const rightWidth = Math.round(Math.min(bounds.maxRight, Math.max(bounds.minRight, ratio * bounds.availableWidth)));
  return {
    gridTemplateColumns: `minmax(min(${bounds.minLeft}px,72vw),1fr) ${LESSON_RESIZER_WIDTH}px minmax(${bounds.minRight}px,${rightWidth}px)`,
  };
});
const activePageActivities = computed<PageActivity[]>(() => activePage.value?.pedagogy || []);
const pageSummaryActivity = computed(() => activePageActivities.value.find((item) => item.type === "page_summary") || null);
const conceptActivities = computed(() => activePageActivities.value.filter((item) => item.type === "concept_card"));
const problemTemplateActivities = computed(() => activePageActivities.value.filter((item) => item.type === "problem_template"));
const misconceptionActivities = computed(() => activePageActivities.value.filter((item) => item.type === "misconception_card"));
const quickCheckActivities = computed(() => activePageActivities.value.filter((item) => item.type === "quick_check"));
const discussionActivities = computed(() => activePageActivities.value.filter((item) => item.type === "discussion_prompt"));
const demoActivities = computed(() => activePageActivities.value.filter((item) => item.type === "demo"));
const discussionDemoActivities = computed(() => [...discussionActivities.value, ...demoActivities.value]);
const learningObjectiveItems = computed(() => payloadList(pageSummaryActivity.value, "learning_objectives"));
const keyPointItems = computed(() => {
  const items = payloadList(pageSummaryActivity.value, "key_points");
  if (items.length) return items;
  return conceptActivities.value.map((item) => item.payload?.knowledge_point || item.title.replace("：知识点", "")).filter(Boolean).slice(0, 6);
});
const activePageText = computed(() => extractStructuredText(activePage.value?.page_text || "") || String(activePage.value?.page_text || "").trim());
const activeScriptText = computed(() => extractStructuredText(activePage.value?.script_text || activePage.value?.page_text || "") || String(activePage.value?.script_text || activePage.value?.page_text || "").trim());
const activeSubtitleText = computed(() => {
  const text = extractStructuredText(activePage.value?.subtitle_text || activePage.value?.script_text || activePage.value?.page_text || "");
  if (subtitleMode.value === "keyword") {
    const firstSentence = text.match(/^[\s\S]*?[。！？!?]/)?.[0]?.trim() || text;
    return firstSentence.slice(0, 140);
  }
  return text;
});
const activePageHtml = computed(() => renderRichText(activePageText.value || "暂无页面内容"));
const activeScriptHtml = computed(() => renderRichText(activeScriptText.value || "暂无文稿"));
const activeSubtitleHtml = computed(() => renderRichText(activeSubtitleText.value));
const slideViewportStyle = computed(() => ({
  "--lesson-slide-fit-scale": String(slideViewportFitScale.value),
}));
const slideCardShellStyle = computed(() => {
  const scale = slideViewportFitScale.value;
  const baseWidth = Math.max(slideCardMeasureRef.value.width, 1160);
  const baseHeight = Math.max(slideCardMeasureRef.value.height, 620);
  return {
    "--lesson-slide-base-width": `${baseWidth}px`,
    "--lesson-slide-base-height": `${baseHeight}px`,
    "--lesson-slide-shell-width": `${Math.max(1, Math.round(baseWidth * scale))}px`,
    "--lesson-slide-shell-height": `${Math.max(1, Math.round(baseHeight * scale))}px`,
  };
});
const quickPageQuestions = computed(() => {
  const structured = [...quickCheckActivities.value, ...discussionActivities.value].map(activityQuestion).filter(Boolean);
  if (structured.length) return Array.from(new Set(structured)).slice(0, 4);
  const title = activePage.value?.page_title || classroomLesson.value?.lesson?.title || "当前页面";
  return [`${title} 的重点？`, `用例子解释 ${title}`, `根据 ${title} 出道题`, `总结 ${title}`];
});
const studyClock = computed(() => `${String(Math.floor(studySeconds.value / 60)).padStart(2, "0")}:${String(studySeconds.value % 60).padStart(2, "0")}`);
const audioTime = computed(() => timeLabel(audioRef.value?.currentTime || 0));
const audioDuration = computed(() => timeLabel(audioRef.value?.duration || activePage.value?.audio_duration_seconds || 0));
// #66：基于本次会话真实数据(学习时长/页数/提问数)的事实性小结，不冒充 AI 生成。
const completionSummary = computed(() => {
  const minutes = Math.max(1, Math.round(studySeconds.value / 60));
  const pages = classroomLesson.value?.pages.length || 0;
  const questions = classMessages.value.filter((m) => m.role === "user").length;
  const parts = [`本次学习约 ${minutes} 分钟`];
  if (pages) parts.push(`共 ${pages} 页`);
  parts.push(questions ? `提问 ${questions} 次` : "本次没有提问");
  return `${parts.join("，")}。建议继续完成配套练习并整理课时笔记。`;
});

function payloadList(activity: PageActivity | null | undefined, key: string) {
  const value = activity?.payload?.[key];
  if (Array.isArray(value)) return value.map((item) => String(item || "").trim()).filter(Boolean).slice(0, 8);
  if (typeof value === "string" && value.trim()) return value.split(/[\n；;]+/).map((item) => item.trim()).filter(Boolean).slice(0, 8);
  return [];
}
function activityQuestion(activity: PageActivity) {
  return String(activity.payload?.question || activity.payload?.prompt || activity.summary || activity.title || "").trim();
}
function activityHtml(activity: PageActivity) {
  return renderRichText(activity.content || activity.summary || "");
}

function normalizeLessonSelectionText(text: string) {
  return text
    .replace(/\u00a0/g, " ")
    .replace(/[ \t]+/g, " ")
    .replace(/\s*\n\s*/g, "\n")
    .trim()
    .slice(0, 1200);
}

function selectionPreviewText(text: string) {
  const raw = text.trim();
  const oneLine = raw.replace(/\s+/g, " ");
  if (!oneLine) return "";
  const hasLineBreak = raw.includes("\n");
  const maxLength = 54;
  if (oneLine.length > maxLength) return `${oneLine.slice(0, maxLength)}...`;
  return hasLineBreak ? `${oneLine}...` : oneLine;
}

function readSlideViewportFitScale() {
  const stage = slideStageRef.value;
  if (!stage || classroomOriginalMaterial.value || compactLessonLayout.value) {
    slideViewportFitScale.value = 1;
    return;
  }
  const stageRect = stage.getBoundingClientRect();
  const style = window.getComputedStyle(stage);
  const paddingX = Number.parseFloat(style.paddingLeft || "0") + Number.parseFloat(style.paddingRight || "0");
  const paddingY = Number.parseFloat(style.paddingTop || "0") + Number.parseFloat(style.paddingBottom || "0");
  const gap = Number.parseFloat(style.rowGap || style.gap || "0") * 2;
  const availableWidth = Math.max(stageRect.width - paddingX, 1);
  const availableHeight = Math.max(stageRect.height - paddingY - gap, 1);

  const baseWidth = Math.max(slideCardMeasureRef.value.width, 1160);
  const baseHeight = Math.max(slideCardMeasureRef.value.height, 620);
  const widthScale = availableWidth / baseWidth;
  const heightScale = availableHeight / baseHeight;
  slideViewportFitScale.value = Math.min(1, widthScale, heightScale);
}

function measureSlideCardSize() {
  if (classroomOriginalMaterial.value) {
    slideViewportFitScale.value = 1;
    return;
  }
  const card = slideStageRef.value?.querySelector<HTMLElement>(".slide-card");
  if (card) {
    const cardStyle = window.getComputedStyle(card);
    const paddingY = Number.parseFloat(cardStyle.paddingTop || "0") + Number.parseFloat(cardStyle.paddingBottom || "0");
    const paddingX = Number.parseFloat(cardStyle.paddingLeft || "0") + Number.parseFloat(cardStyle.paddingRight || "0");
    const rowGap = Number.parseFloat(cardStyle.rowGap || cardStyle.gap || "0");
    const title = card.querySelector<HTMLElement>("h1");
    const content = card.querySelector<HTMLElement>(".slide-content");
    const fullContentHeight = content
      ? paddingY + (title?.scrollHeight || title?.offsetHeight || 0) + rowGap + content.scrollHeight
      : card.scrollHeight;
    const fullContentWidth = content ? paddingX + Math.max(content.scrollWidth, title?.scrollWidth || 0) : card.scrollWidth;
    slideCardMeasureRef.value = {
      width: Math.max(fullContentWidth, card.scrollWidth, card.offsetWidth, card.clientWidth),
      height: Math.max(fullContentHeight, card.scrollHeight, card.offsetHeight, card.clientHeight),
    };
  }
  readSlideViewportFitScale();
}

function syncSlideStageResizeObserver() {
  slideStageResizeObserver?.disconnect();
  slideStageResizeObserver = undefined;
  const stage = slideStageRef.value;
  if (!stage || typeof ResizeObserver === "undefined") return;
  slideStageResizeObserver = new ResizeObserver(() => measureSlideCardSize());
  slideStageResizeObserver.observe(stage);
}

function clearLessonAskContext() {
  lessonAskContext.value = "";
}

function clearBrowserSelection() {
  window.getSelection()?.removeAllRanges();
}

function lessonSelectionNodeInStage(node: Node | null) {
  const stage = slideStageRef.value;
  if (!stage || !node) return false;
  return stage.contains(node);
}

function clampSelectionPopoverX(x: number) {
  return Math.min(Math.max(x, 76), Math.max(76, window.innerWidth - 76));
}

function updateLessonSelectionMenu() {
  if (!classroomOpen.value || lessonResizeActive.value) {
    hideLessonSelectionMenu();
    return;
  }
  const selection = window.getSelection();
  if (!selection || selection.isCollapsed || !selection.rangeCount) {
    hideLessonSelectionMenu();
    return;
  }
  const selectedText = normalizeLessonSelectionText(selection.toString());
  if (selectedText.length < 2) {
    hideLessonSelectionMenu();
    return;
  }
  const range = selection.getRangeAt(0);
  if (!lessonSelectionNodeInStage(range.commonAncestorContainer) && !lessonSelectionNodeInStage(selection.anchorNode) && !lessonSelectionNodeInStage(selection.focusNode)) {
    hideLessonSelectionMenu();
    return;
  }
  const rects = Array.from(range.getClientRects()).filter((rect) => rect.width > 0 && rect.height > 0);
  const rect = rects[0] || range.getBoundingClientRect();
  if (!rect || (!rect.width && !rect.height)) {
    hideLessonSelectionMenu();
    return;
  }
  lessonSelectionMenu.text = selectedText;
  lessonSelectionMenu.x = clampSelectionPopoverX(rect.left + rect.width / 2);
  lessonSelectionMenu.y = Math.max(56, rect.top - 12);
  lessonSelectionMenu.open = true;
}

function scheduleLessonSelectionCheck() {
  if (lessonSelectionTimer) window.clearTimeout(lessonSelectionTimer);
  lessonSelectionTimer = window.setTimeout(updateLessonSelectionMenu, 80);
}

async function openClassQaFromSelection() {
  if (!compactLessonLayout.value) aiPanelOpen.value = true;
  classroomTab.value = "qa";
  await nextTick();
}

async function explainLessonSelection() {
  const text = lessonSelectionMenu.text;
  if (!text || classThinking.value) return;
  hideLessonSelectionMenu();
  clearLessonAskContext();
  clearBrowserSelection();
  await openClassQaFromSelection();
  classQuestion.value = `请为我解释“${text}”`;
  await askInClass();
}

async function prepareLessonSelectionQuestion() {
  const text = lessonSelectionMenu.text;
  if (!text) return;
  hideLessonSelectionMenu();
  clearBrowserSelection();
  lessonAskContext.value = text;
  classQuestion.value = "";
  await openClassQaFromSelection();
  classMathField.value?.focus();
}

function lessonPanelBounds(totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0) {
  const availableWidth = Math.max(totalWidth - LESSON_RESIZER_WIDTH, 1);
  const minLeft = classroomOriginalMaterial.value ? 760 : 700;
  const minRight = LESSON_LAYOUT_MIN_RIGHT;
  const preferredMaxRight = classroomOriginalMaterial.value ? availableWidth * 0.38 : availableWidth * 0.42;
  const hardMaxRight = classroomOriginalMaterial.value ? 640 : 680;
  const maxRight = Math.min(hardMaxRight, Math.max(420, preferredMaxRight), Math.max(minRight, availableWidth - minLeft));
  return { availableWidth, minLeft, minRight, maxRight };
}

function clampLessonPanelRatio(value: number, totalWidth = studyMainRef.value?.clientWidth || lessonLayoutWidth.value || 0) {
  if (totalWidth > 900) {
    const { availableWidth, minLeft, minRight, maxRight } = lessonPanelBounds(totalWidth);
    const minRatio = minRight / availableWidth;
    const maxRatio = Math.min(maxRight / availableWidth, (availableWidth - minLeft) / availableWidth, LESSON_LAYOUT_MAX_RATIO);
    if (maxRatio > minRatio) return Math.min(maxRatio, Math.max(minRatio, value));
  }
  return Math.min(LESSON_LAYOUT_MAX_RATIO, Math.max(LESSON_LAYOUT_MIN_RATIO, value));
}
function updateLessonPanelRatio(clientX: number) {
  if (compactLessonLayout.value) return;
  const element = studyMainRef.value;
  if (!element) return;
  const rect = element.getBoundingClientRect();
  const width = Math.max(rect.width, 1);
  lessonPanelRatio.value = clampLessonPanelRatio((rect.right - clientX) / width, width);
}
function onLessonResizePointerMove(event: PointerEvent) {
  if (!lessonResizeActive.value) return;
  updateLessonPanelRatio(event.clientX);
}
function stopLessonResize() {
  if (!lessonResizeActive.value) return;
  lessonResizeActive.value = false;
  lessonPanelRatioCustomized.value = true;
  document.body.classList.remove("lesson-resizing");
  window.removeEventListener("pointermove", onLessonResizePointerMove);
  window.removeEventListener("pointerup", stopLessonResize);
  window.removeEventListener("pointercancel", stopLessonResize);
  localStorage.setItem(LESSON_LAYOUT_STORAGE_KEY, String(lessonPanelRatio.value));
}
function startLessonResize(event: PointerEvent) {
  if (!aiPanelOpen.value || compactLessonLayout.value) return;
  event.preventDefault();
  lessonResizeActive.value = true;
  (event.currentTarget as HTMLElement | null)?.setPointerCapture?.(event.pointerId);
  updateLessonPanelRatio(event.clientX);
  document.body.classList.add("lesson-resizing");
  window.addEventListener("pointermove", onLessonResizePointerMove);
  window.addEventListener("pointerup", stopLessonResize);
  window.addEventListener("pointercancel", stopLessonResize);
}
function revealChrome() { chromeVisible.value = true; if (chromeTimer) window.clearTimeout(chromeTimer); chromeTimer = window.setTimeout(() => { if (audioPlaying.value) chromeVisible.value = false; }, 3000); }
function updateCompactLessonLayout() {
  const width = window.innerWidth || document.documentElement.clientWidth || 0;
  lessonLayoutWidth.value = width;
  const nextCompact = width > 0 && width < 1180;
  const wasCompact = compactLessonLayout.value;
  compactLessonLayout.value = nextCompact;
  if (nextCompact) {
    aiPanelOpen.value = false;
    thumbOpen.value = false;
    settingsOpen.value = false;
  } else if (wasCompact) {
    aiPanelOpen.value = true;
  }
  requestAnimationFrame(() => measureSlideCardSize());
}
async function toggleLessonFullscreen() {
  const element = studyRoomRef.value;
  if (!element) return;
  try {
    if (document.fullscreenElement === element) {
      await document.exitFullscreen();
      return;
    }
    if (!document.fullscreenElement) {
      await element.requestFullscreen();
      return;
    }
    await document.exitFullscreen();
    await element.requestFullscreen();
  } catch (error) {
    notice("warning", (error as Error)?.message || "当前环境不支持全屏");
  }
}
function onLessonFullscreenChange() {
  lessonFullscreen.value = document.fullscreenElement === studyRoomRef.value;
}

watch(
  () => classroomLesson.value?.lesson.id,
  () => {
    lessonPanelRatio.value = savedLessonPanelRatio();
    lessonPanelRatioCustomized.value = false;
    slideViewportFitScale.value = 1;
    slideCardMeasureRef.value = { width: 0, height: 0 };
  }
);
watch(
  () => [aiPanelOpen.value, lessonFullscreen.value],
  () => {
    void nextTick(() => {
      syncSlideStageResizeObserver();
      measureSlideCardSize();
      requestAnimationFrame(() => measureSlideCardSize());
    });
  }
);
watch(
  () => [currentPage.value, classroomOriginalMaterial.value?.id, activePageHtml.value, activeSubtitleHtml.value],
  () => {
    void nextTick(() => {
      syncSlideStageResizeObserver();
      measureSlideCardSize();
      requestAnimationFrame(() => measureSlideCardSize());
    });
  },
  { immediate: true }
);
watch(activePage, async (page, oldPage) => {
  // 翻页前先把上一页未保存的笔记落盘：否则防抖(1200ms)还没触发就被 loadNote 覆盖，笔记静默丢失且状态误显“已保存”。
  if (noteTimer) { window.clearTimeout(noteTimer); noteTimer = undefined; }
  if (oldPage?.id && noteState.value === "未保存") {
    await flushNote(oldPage.id, pageNote.value);
  }
  if (audioRef.value) {
    audioRef.value.pause();
    audioRef.value.currentTime = 0;
  }
  audioPlaying.value = false;
  audioProgress.value = 0;
  if (page) await loadNote(page.id);
}, { immediate: false });
// 把指定页的笔记内容即时落盘（翻页前抢救上一页未保存内容用；不改 UI 状态，由后续 loadNote 统一刷新）。
async function flushNote(pageId: number, content: string) {
  if (!pageId) return;
  await run<any>(() => api.put(`/student/pages/${pageId}/note`, { content }));
}

async function toggleAudio() { if (!audioRef.value) return; audioRef.value.playbackRate = playbackRate.value; if (audioRef.value.paused) { try { await audioRef.value.play(); } catch (error) { audioPlaying.value = false; notice("error", "音频无法播放，请检查音频文件或浏览器自动播放设置"); return; } } else audioRef.value.pause(); revealChrome(); }
function setRate(value: string) { playbackRate.value = Number(value); if (audioRef.value) audioRef.value.playbackRate = playbackRate.value; }
function updateAudio() { if (!audioRef.value) return; audioProgress.value = audioRef.value.duration ? Math.round(audioRef.value.currentTime / audioRef.value.duration * 100) : 0; }
function seekAudio() { if (audioRef.value?.duration) audioRef.value.currentTime = audioRef.value.duration * audioProgress.value / 100; }
async function handleAudioEnded() { if (!classroomLesson.value) return; if (currentPage.value >= classroomLesson.value.pages.length) { await saveProgress(true, true); completeOpen.value = true; } else await nextPage(); }
async function loadNote(pageId: number) { if (!pageId) return; const note = await run<any>(() => api.get(`/student/pages/${pageId}/note`)); pageNote.value = note?.content || ""; noteState.value = "已保存"; noteSavedAt.value = note?.updated_at ? `上次保存：${relativeTime(note.updated_at)}` : "尚未保存"; }
function queueNoteSave() { noteState.value = "未保存"; if (noteTimer) window.clearTimeout(noteTimer); noteTimer = window.setTimeout(saveCurrentNote, 1200); }
async function saveCurrentNote() { if (!activePage.value) return; noteState.value = "保存中"; const note = await run<any>(() => api.put(`/student/pages/${activePage.value!.id}/note`, { content: pageNote.value })); if (note) { noteState.value = "已保存"; noteSavedAt.value = `上次保存：${relativeTime(note.updated_at)}`; } }
function formatNote(kind: "bold" | "italic" | "mark") {
  const textarea = pageNoteArea.value;
  if (!textarea) return;
  const start = textarea.selectionStart ?? 0;
  const end = textarea.selectionEnd ?? start;
  const selected = pageNote.value.slice(start, end) || (kind === "mark" ? "重点" : "文字");
  const [prefix, suffix] = kind === "bold" ? ["**", "**"] : kind === "italic" ? ["*", "*"] : ["==", "=="];
  pageNote.value = `${pageNote.value.slice(0, start)}${prefix}${selected}${suffix}${pageNote.value.slice(end)}`;
  const cursor = start + prefix.length + selected.length + suffix.length;
  nextTick(() => {
    textarea.focus();
    textarea.setSelectionRange(cursor, cursor);
  });
  queueNoteSave();
}
function confettiStyle(n: number) { return { left: `${(n * 37) % 100}%`, background: ["#00B8D4", "#00E5FF", "#2E7D32", "#D9A05B", "#D94925"][n % 5], animationDelay: `${(n % 8) * 0.05}s` }; }

function removeQaAttachment(_scope: "class", index: number) {
  classQaAttachments.value.splice(index, 1);
}

async function handleQaImageChange(event: Event, _scope: "class") {
  const input = event.target as HTMLInputElement;
  const file = (input.files || [])[0];
  input.value = "";
  if (!file) return;
  const courseId = classroomLesson.value?.lesson.course_id;
  if (!courseId) {
    notice("warning", "请先选择课程");
    return;
  }
  if (!file.type.startsWith("image/")) {
    notice("warning", "请上传图片文件");
    return;
  }
  if (classQaAttachments.value.length >= 3) {
    notice("warning", "最多上传 3 张图片");
    return;
  }
  const form = new FormData();
  form.set("course_id", String(courseId));
  form.set("file", file);
  classQaImageUploading.value = true;
  try {
    const attachment = await run<QaAttachment>(() => api.post("/qa/attachments/image", form), "图片已上传");
    if (attachment) classQaAttachments.value.push(attachment);
  } finally {
    classQaImageUploading.value = false;
  }
}

async function askInClass() {
  if ((!classQuestion.value.trim() && !classQaAttachments.value.length) || !classroomLesson.value || classThinking.value || (classConversationLoading.value && !classMessages.value.length) || classQaImageUploading.value) return;
  const lessonPageId = Number(activePage.value?.id || 0);
  if (!lessonPageId) {
    notice("warning", "当前课件页还未加载完成，请稍后再提问。");
    return;
  }
  const rawQuestion = classQuestion.value.trim();
  const selectedContext = lessonAskContext.value.trim();
  const question = rawQuestion || "请分析这张图片";
  const requestQuestion = selectedContext
    ? `请基于以下选中的课件内容回答：\n“${selectedContext}”\n\n我的问题：${question}`
    : question;
  const attachments = classQaAttachments.value.map((item) => ({ ...item }));
  classQuestion.value = "";
  clearLessonAskContext();
  classQaAttachments.value = [];
  classMessages.value.push({ id: Date.now(), role: "user", text: question, attachments });
  const aiMessageId = Date.now() + 1;
  const aiMessage: ChatMessage = { id: aiMessageId, role: "ai", text: "", thought: "", sources: [], streaming: true };
  classMessages.value.push(aiMessage);
  const controller = new AbortController();
  classAbortController = controller;
  classThinking.value = true;
  try {
    await api.streamPost("/qa/ask/stream", {
      course_id: classroomLesson.value.lesson.course_id,
      conversation_id: classConversationId.value,
      lesson_page_id: lessonPageId,
      question: requestQuestion,
      attachments
    }, (event, data) => {
      if (event === "delta") {
        queueQaDelta(classMessages, aiMessageId, data, false);
      } else {
        flushQaDeltas();
        applyQaStreamEvent(classMessages, aiMessageId, event, data);
      }
      if (event === "created" || event === "final") classConversationId.value = data.conversation_id ?? classConversationId.value;
    }, undefined, controller.signal);
  } catch (error) {
    // 用户主动停止：保留已生成内容，不提示错误
    flushQaDeltas();
    if (!controller.signal.aborted) {
      const current = classMessages.value.find((message) => message.id === aiMessageId);
      if (!current?.text) patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, text: "请求失败，请稍后重试。" }));
      notice("error", (error as Error).message);
    }
  } finally {
    flushQaDeltas();
    patchChatMessage(classMessages, aiMessageId, (message) => ({ ...message, streaming: false }));
    classThinking.value = false;
    if (classAbortController === controller) classAbortController = null;
  }
}
function stopClassGeneration() { classAbortController?.abort(); }
function sendQuickClass(text: string) {
  // 先切到“问答”标签（compact 布局下同时展开 AI 面板），让用户立即看到问题进入问答流与思考态，
  // 否则停在“活动”页点快问会像点了没反应（回答只渲染在问答标签里）。
  classroomTab.value = "qa";
  if (compactLessonLayout.value) aiPanelOpen.value = true;
  classQuestion.value = text;
  void nextTick(() => askInClass());
}

async function loadClassQaHistory() {
  if (!classroomLesson.value) return;
  const lessonId = classroomLesson.value.lesson.id;
  const courseId = classroomLesson.value.lesson.course_id;
  const summaries = (await run<any[]>(() => api.get("/qa/history", { course_id: courseId, lesson_id: lessonId }))) || [];
  const latest = [...summaries].sort((left, right) => timestampMs(right.created_at) - timestampMs(left.created_at) || Number(right.id || 0) - Number(left.id || 0))[0];
  const conversationId = Number(latest?.conversation_id || 0);
  if (!conversationId) {
    classMessages.value = [];
    classConversationId.value = null;
    return;
  }
  const loadSeq = ++classConversationLoadSeq;
  classConversationLoading.value = true;
  classMessages.value = [];
  try {
    const records = await api.get<any[]>(`/qa/conversations/${conversationId}`);
    if (loadSeq !== classConversationLoadSeq || classroomLesson.value?.lesson.id !== lessonId) return;
    const ordered = [...(records || [])].sort((left, right) => timestampMs(left.created_at) - timestampMs(right.created_at) || Number(left.id || 0) - Number(right.id || 0));
    classMessages.value = qaRecordsToMessages(ordered);
    classConversationId.value = conversationId;
  } catch (error) {
    if (loadSeq === classConversationLoadSeq) notice("error", (error as Error).message);
  } finally {
    if (loadSeq === classConversationLoadSeq) classConversationLoading.value = false;
  }
}

async function jumpToSource(source: any) {
  if (!source) return;
  const lessonId = Number(source.lesson_id || 0);
  const lessonPageId = Number(source.lesson_page_id || 0);
  const rawPageNumber = Number(source.page_number || 0);
  // 课堂内问答：来源属于当前打开的课时，直接定位到对应页面
  if (classroomOpen.value && classroomLesson.value && (!lessonId || classroomLesson.value.lesson.id === lessonId)) {
    const targetPage = resolveSourcePageNumber(source);
    if (targetPage) {
      if (classroomTab.value === "qa") classroomTab.value = "script";
      await jumpPage(targetPage);
    }
    return;
  }
  // 全局问答或来源属于其它课时：打开来源所属课时，再定位到对应页面
  if (lessonId) {
    pendingSourcePageNumber.value = rawPageNumber || null;
    pendingSourcePageId.value = lessonPageId || null;
    await openLesson(lessonId);
    return;
  }
  // 没有课时信息但能解析出当前课时的页码时也尝试跳转
  const fallbackPage = resolveSourcePageNumber(source);
  if (fallbackPage && classroomOpen.value) await jumpPage(fallbackPage);
}

onMounted(async () => {
  document.addEventListener("selectionchange", scheduleLessonSelectionCheck);
  document.addEventListener("fullscreenchange", onLessonFullscreenChange);
  window.addEventListener("resize", updateCompactLessonLayout);
  updateCompactLessonLayout();
  syncSlideStageResizeObserver();
  // 课时详情/当前页由外壳在挂载前经 loadLessonStudyRoute 填好，这里补做课堂内初始化：
  // 载入当前页笔记与本课时最近一段课堂问答历史（原为 loadLessonStudyRoute 尾部执行）。
  await loadNote(activePage.value?.id || 0);
  void loadClassQaHistory();
});
onBeforeUnmount(() => {
  document.removeEventListener("selectionchange", scheduleLessonSelectionCheck);
  document.removeEventListener("fullscreenchange", onLessonFullscreenChange);
  window.removeEventListener("resize", updateCompactLessonLayout);
  slideStageResizeObserver?.disconnect();
  slideStageResizeObserver = undefined;
  if (lessonSelectionTimer) window.clearTimeout(lessonSelectionTimer);
  stopLessonResize();
  if (chromeTimer) clearTimeout(chromeTimer);
  if (noteTimer) clearTimeout(noteTimer);
  // 离开课堂时中止仍在进行的课堂问答流，避免流回调在组件卸载后继续触发。
  classAbortController?.abort();
});
</script>
