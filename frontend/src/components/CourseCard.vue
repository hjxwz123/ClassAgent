<template>
  <article
    class="course-card"
    role="button"
    tabindex="0"
    :aria-label="`打开课程 ${course.name}`"
    @click="$emit('open')"
    @keydown.enter="$emit('open')"
    @keydown.space.prevent="$emit('open')"
  >
    <div class="cover" :class="{ 'has-image': course.cover_url }" :style="coverStyle">
      <strong v-if="!course.cover_url" class="cover-title">{{ coverText }}</strong>
      <span class="tag tag-primary">{{ course.status }}</span>
    </div>
    <div class="body">
      <h3>{{ course.name }}</h3>
      <p>{{ course.term }}</p>
      <div class="meta">
        <span><Users :size="14" />{{ count }}</span>
        <span><Clock :size="14" />{{ course.course_code }}</span>
      </div>
    </div>
  </article>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { Clock, Users } from "../icons";
import type { Course } from "../types";

const props = defineProps<{ course: Course; count?: number | string }>();
defineEmits<{ open: [] }>();

const coverText = computed(() => (props.course.name || "课程").replace(/\s+/g, "").slice(0, 4) || "课程");
const coverStyle = computed(() => {
  if (props.course.cover_url) {
    return {
      backgroundImage: `linear-gradient(180deg, rgba(18,22,20,0.06), rgba(18,22,20,0.42)), url(${props.course.cover_url})`,
      backgroundSize: "cover",
      backgroundPosition: "center",
    };
  }
  return { background: props.course.cover_color || "linear-gradient(135deg,#121614,#00B8D4)" };
});
</script>

<style scoped>
.course-card {
  width: 100%;
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out), border-color var(--duration-fast) var(--ease-out);
}
.course-card:hover { transform: translateY(-4px); border-color: var(--color-border-strong); box-shadow: var(--shadow-lg); }
.course-card:focus-visible {
  outline: none;
  box-shadow: 0 0 0 2px var(--color-bg-surface), 0 0 0 4px var(--ca-role-primary, var(--color-primary-500));
}
.cover {
  position: relative;
  display: flex;
  height: 150px;
  align-items: center;
  justify-content: center;
  color: var(--color-text-inverse);
  background: var(--ca-color-slate);
}
.cover::after {
  content: "";
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="n"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23n)" opacity="0.05"/%3E%3C/svg%3E');
}
.cover-title {
  position: relative;
  z-index: 1;
  display: grid;
  place-items: center;
  min-width: 96px;
  min-height: 58px;
  border: 1px solid rgba(244,244,240,.34);
  border-radius: 14px;
  background: rgba(244,244,240,.18);
  font-family: var(--font-family-serif);
  font-size: 22px;
  font-weight: 800;
  letter-spacing: 0.02em;
  text-shadow: 0 2px 10px rgba(0,0,0,.2);
}
.cover-title { transition: transform var(--duration-base) var(--ease-out); }
.course-card:hover .cover-title { transform: scale(1.05); }
.cover .tag {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  z-index: 1;
}
.body { padding: var(--space-4); }
h3 {
  display: -webkit-box;
  margin: 0;
  min-height: 48px;
  color: var(--color-text-primary);
  font-family: var(--font-family-serif);
  font-size: var(--text-h4);
  line-height: 24px;
  font-weight: var(--font-weight-bold);
  letter-spacing: -0.01em;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
p { margin: var(--space-2) 0 var(--space-4); color: var(--color-text-muted); font-size: var(--text-caption); }
.meta {
  display: flex;
  justify-content: space-between;
  border-top: 1px solid var(--color-border-subtle);
  padding-top: var(--space-3);
  color: var(--color-text-secondary);
  font-size: var(--text-caption);
}
.meta span { display: inline-flex; align-items: center; gap: 6px; }
.meta span:last-child { font-family: var(--font-family-mono); font-variant-numeric: tabular-nums; letter-spacing: 0.02em; }
</style>
