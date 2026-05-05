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
    <div class="cover">
      <BookOpen :size="24" />
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
import { BookOpen, Clock, Users } from "lucide-vue-next";
import type { Course } from "../types";

defineProps<{ course: Course; count?: number | string }>();
defineEmits<{ open: [] }>();
</script>

<style scoped>
.course-card {
  width: 100%;
  overflow: hidden;
  background: var(--color-bg-surface);
  border: 1px solid var(--color-border-default);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: transform var(--duration-base) var(--ease-out), box-shadow var(--duration-base) var(--ease-out);
}
.course-card:hover { transform: translateY(-4px); box-shadow: var(--shadow-lg); }
.cover {
  position: relative;
  display: flex;
  height: 150px;
  align-items: center;
  justify-content: center;
  color: var(--color-text-inverse);
  background: var(--ca-color-slate);
}
.cover svg {
  color: var(--ca-role-student-glow);
}
.cover svg { transition: transform var(--duration-base) var(--ease-out); }
.course-card:hover .cover svg { transform: scale(1.05); }
.cover .tag {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
}
.body { padding: var(--space-4); }
h3 {
  display: -webkit-box;
  margin: 0;
  min-height: 48px;
  color: var(--color-text-primary);
  font-size: var(--text-h4);
  line-height: 24px;
  font-weight: var(--font-weight-semibold);
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
</style>
