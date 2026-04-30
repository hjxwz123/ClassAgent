<template>
  <section v-if="classroomLesson" class="classroom">
    <header class="slim">
      <button class="btn btn-ghost" @click="classroomLesson = null"><ArrowLeft :size="16" />返回</button>
      <strong>{{ classroomLesson.lesson.title }}</strong>
      <div class="progress" role="progressbar" :aria-valuenow="progressValue" aria-valuemin="0" aria-valuemax="100">
        <span :style="{ width: `${progressValue}%` }"></span>
      </div>
      <button class="btn btn-ghost icon-btn" aria-label="设置"><Settings :size="16" /></button>
    </header>
    <main class="learn">
      <section class="slide">
        <aside class="thumbs">
          <button
            v-for="page in classroomLesson.pages"
            :key="page.id"
            class="thumb"
            :class="{ active: page.page_number === currentPage }"
            @click="currentPage = page.page_number"
          >
            {{ page.page_number }}
          </button>
        </aside>
        <article class="ppt">
          <h2>{{ activePage?.page_title || `第${currentPage}页` }}</h2>
          <p>{{ activePage?.page_text }}</p>
        </article>
        <div v-if="activePage?.subtitle_text" class="subtitle">{{ activePage.subtitle_text }}</div>
        <div class="player">
          <button class="btn btn-ghost icon-btn" aria-label="上一页" @click="prevPage"><SkipBack :size="18" /></button>
          <button class="btn btn-primary icon-btn" aria-label="播放"><Play :size="18" /></button>
          <button class="btn btn-ghost icon-btn" aria-label="下一页" @click="nextPage"><SkipForward :size="18" /></button>
          <audio v-if="activePage?.audio_url" :src="activePage.audio_url" controls></audio>
          <button class="btn btn-secondary" @click="saveProgress(false)">进度</button>
          <button class="btn btn-secondary" @click="saveProgress(true)">完成</button>
        </div>
      </section>
      <aside class="ai-panel">
        <div class="tabbar">
          <button class="btn btn-sm" :class="classroomTab === 'script' ? 'btn-primary' : 'btn-ghost'" @click="classroomTab = 'script'">文稿</button>
          <button class="btn btn-sm" :class="classroomTab === 'qa' ? 'btn-primary' : 'btn-ghost'" @click="classroomTab = 'qa'">问答</button>
        </div>
        <section v-if="classroomTab === 'script'" class="ai-box">
          <span class="tag tag-ai"><Sparkles :size="12" />AI</span>
          <p>{{ activePage?.script_text || "暂无文稿" }}</p>
        </section>
        <section v-else>
          <div class="messages">
            <div v-for="item in qaMessages" :key="item.id" class="bubble" :class="item.role">
              <span v-if="item.role === 'ai'" class="avatar"><Bot :size="16" /></span>
              <p>{{ item.text }}</p>
            </div>
          </div>
          <form class="askbar" @submit.prevent="askInClass">
            <input v-model="qaQuestion" class="input" placeholder="输入问题" />
            <button class="btn btn-ai"><Send :size="16" />提问</button>
          </form>
          <p class="ai-note">AI 回答仅供学习参考，可能存在不准确的情况，请结合课程材料综合判断。</p>
        </section>
      </aside>
    </main>
  </section>

  <section v-else class="shell">
    <header class="topbar">
      <div class="logo"><span><Bot :size="18" /></span><strong>课程学习助手</strong></div>
      <div class="userbox">
        <Bell :size="18" />
        <span>{{ user.nickname }}</span>
        <button class="btn btn-ghost btn-sm" @click="$emit('logout')">退出</button>
      </div>
    </header>
    <aside class="sidebar">
      <nav>
        <button v-for="item in nav" :key="item.key" class="nav-item" :class="{ active: active === item.key }" @click="active = item.key">
          <component :is="item.icon" :size="20" />{{ item.label }}
        </button>
      </nav>
    </aside>
    <main class="workspace">
      <div class="page-head">
        <h1 class="page-title">{{ currentTitle }}</h1>
        <button class="btn btn-secondary" @click="refresh"><RefreshCw :size="16" />刷新</button>
      </div>

      <section v-if="active === 'courses'" class="page">
        <div class="toolbar">
          <input v-if="user.role === 'student'" v-model="joinCode" class="input short" placeholder="课程码" />
          <button v-if="user.role === 'student'" class="btn btn-primary" @click="joinCourse"><Plus :size="16" />加入</button>
          <button v-if="user.role !== 'student'" class="btn btn-primary" @click="showCourseForm = true"><Plus :size="16" />创建</button>
        </div>
        <div class="grid">
          <CourseCard v-for="course in courses" :key="course.id" :course="course" :count="course.course_code" @open="openCourse(course.id)" />
        </div>
      </section>

      <section v-if="active === 'courseDetail'" class="page">
        <div v-if="courseDetail" class="split">
          <section>
            <article class="card">
              <div class="card-head">
                <div>
                  <h2 class="card-title">{{ courseDetail.course.name }}</h2>
                  <p class="card-desc">{{ courseDetail.course.term }}</p>
                </div>
                <span class="tag tag-primary">{{ courseDetail.student_count }}人</span>
              </div>
              <div class="toolbar">
                <button v-if="user.role !== 'student'" class="btn btn-secondary" @click="updateCourse"><Pencil :size="16" />更新</button>
                <button v-if="user.role !== 'student'" class="btn btn-danger" @click="deactivateCourse"><XCircle :size="16" />停用</button>
                <button v-if="user.role === 'student'" class="btn btn-danger" @click="leaveCourse"><LogOut :size="16" />退出</button>
              </div>
              <div class="form-row" v-if="user.role !== 'student'">
                <input v-model="courseEdit.name" class="input" placeholder="课程名" />
                <input v-model="courseEdit.term" class="input" placeholder="学期" />
              </div>
              <textarea v-if="user.role !== 'student'" v-model="courseEdit.description" class="textarea" placeholder="简介"></textarea>
            </article>
            <article class="card">
              <div class="card-head">
                <h2 class="card-title">章节</h2>
                <button v-if="user.role !== 'student'" class="btn btn-secondary btn-sm" @click="createChapter"><Plus :size="14" />章节</button>
              </div>
              <div v-if="user.role !== 'student'" class="form-row">
                <input v-model="chapterForm.title" class="input" placeholder="标题" />
                <input v-model.number="chapterForm.order_index" class="input" type="number" placeholder="序号" />
              </div>
              <div class="list">
                <button v-for="chapter in courseDetail.chapters" :key="chapter.id" class="row" @click="selectedChapterId = chapter.id">
                  <span>{{ chapter.order_index }}. {{ chapter.title }}</span>
                  <span class="tag">{{ chapter.id }}</span>
                </button>
              </div>
            </article>
          </section>
          <aside class="card">
            <div class="card-head">
              <h2 class="card-title">成员</h2>
              <button class="btn btn-ghost btn-sm" @click="loadMembers">成员</button>
            </div>
            <div class="list">
              <div v-for="item in members" :key="item.id" class="row">
                <span>{{ item.user.nickname }}</span>
                <span class="tag">{{ item.user.role }}</span>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section v-if="active === 'materials'" class="page">
        <div class="toolbar">
          <select v-model.number="selectedCourseId" class="select short" @change="loadCourseScoped">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <input v-model="materialFilter.keyword" class="input short" placeholder="关键词" />
          <select v-model="materialFilter.category" class="select short">
            <option value="">分类</option>
            <option value="courseware">课件</option>
            <option value="handout">讲义</option>
            <option value="exercise">练习</option>
            <option value="reference">参考</option>
          </select>
          <button class="btn btn-secondary" @click="loadMaterials"><Search :size="16" />搜索</button>
          <button v-if="user.role !== 'student'" class="btn btn-primary" @click="openUpload"><Upload :size="16" />上传</button>
        </div>
        <div class="table-wrap">
          <table class="table">
            <thead><tr><th>标题</th><th>类型</th><th>解析</th><th>向量</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="item in materials" :key="item.id">
                <td>{{ item.title }}</td>
                <td>{{ item.material_type }}</td>
                <td><span class="tag" :class="statusClass(item.parse_status)">{{ item.parse_status }}</span></td>
                <td><span class="tag" :class="statusClass(item.vector_status)">{{ item.vector_status }}</span></td>
                <td class="ops">
                  <button class="btn btn-ghost btn-xs" @click="loadMaterialDetail(item.id)">查看</button>
                  <a v-if="item.preview_url" class="btn btn-ghost btn-xs" :href="item.preview_url" target="_blank">预览</a>
                  <button v-if="user.role !== 'student'" class="btn btn-ghost btn-xs" @click="reprocess(item.id)">重跑</button>
                  <button v-if="user.role !== 'student'" class="btn btn-ghost btn-xs" @click="deleteMaterial(item.id)">删除</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <MaterialPanel
          v-if="materialDetail"
          :detail="materialDetail"
          :editable="user.role !== 'student'"
          @close="materialDetail = null"
          @save="saveScript"
          @regen="regenScript"
          @update="updateMaterial"
        />
      </section>

      <section v-if="active === 'lessons'" class="page">
        <div class="toolbar">
          <select v-model.number="selectedCourseId" class="select short" @change="loadLessons">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
        </div>
        <div class="grid">
          <article v-for="lesson in lessons" :key="lesson.id" class="card">
            <div class="card-head">
              <div><h2 class="card-title">{{ lesson.title }}</h2><p class="card-desc">{{ lesson.page_count }}页</p></div>
              <span class="tag" :class="statusClass(lesson.status)">{{ lesson.status }}</span>
            </div>
            <div class="toolbar">
              <button class="btn btn-primary" @click="openLesson(lesson.id)"><Play :size="16" />学习</button>
              <button v-if="user.role !== 'student'" class="btn btn-secondary" @click="publishLesson(lesson.id, lesson.status !== 'published')">
                {{ lesson.status === 'published' ? '撤回' : '发布' }}
              </button>
            </div>
          </article>
        </div>
      </section>

      <section v-if="active === 'qa'" class="page split">
        <section class="card">
          <div class="card-head"><h2 class="card-title">提问</h2><span class="tag tag-ai"><Sparkles :size="12" />AI</span></div>
          <select v-model.number="selectedCourseId" class="select" @change="loadQaHistory">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <textarea v-model="qaQuestion" class="textarea" placeholder="输入问题"></textarea>
          <button class="btn btn-ai" @click="askQuestion"><Send :size="16" />提问</button>
          <div v-if="qaResult" class="ai-box result">
            <div v-if="qaResult.is_out_of_scope" class="alert alert-warning">
              <AlertTriangle :size="16" />
              <div><strong>超出范围</strong></div>
            </div>
            <p>{{ qaResult.answer }}</p>
            <div v-if="qaResult.sources?.length" class="source-list">
              <span v-for="(source, index) in qaResult.sources" :key="index" class="tag">
                {{ source.material_title || '资料' }} · {{ source.page_number || '-' }}
              </span>
            </div>
            <button class="btn btn-ghost btn-xs" @click="favoriteQa(qaResult.record_id, true)">收藏</button>
            <button class="btn btn-ghost btn-xs" @click="feedbackQa(qaResult.record_id, 'positive')">好评</button>
            <button class="btn btn-ghost btn-xs" @click="feedbackQa(qaResult.record_id, 'negative')">差评</button>
          </div>
        </section>
        <aside class="card">
          <div class="card-head"><h2 class="card-title">历史</h2><button class="btn btn-ghost btn-sm" @click="loadQaHistory">刷新</button></div>
          <input v-model="qaKeyword" class="input" placeholder="关键词" @keyup.enter="loadQaHistory" />
          <div class="list">
            <div v-for="item in qaHistory" :key="item.id" class="history">
              <strong>{{ item.question }}</strong>
              <p>{{ item.answer }}</p>
              <span v-if="item.is_favorite" class="tag tag-primary">收藏</span>
            </div>
          </div>
        </aside>
      </section>

      <section v-if="active === 'tutoring'" class="page split">
        <section class="card">
          <div class="card-head"><h2 class="card-title">题目</h2><span class="tag tag-ai">AI</span></div>
          <select v-model.number="selectedCourseId" class="select">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <textarea v-model="problemText" class="textarea" placeholder="题干"></textarea>
          <div class="toolbar">
            <button class="btn btn-ai" @click="createTextProblem"><Sparkles :size="16" />文本</button>
            <input ref="problemFile" type="file" class="file" @change="createImageProblem" />
          </div>
          <div v-if="activeProblem" class="ai-box">
            <textarea v-model="correctedText" class="textarea"></textarea>
            <button class="btn btn-secondary" @click="confirmProblem">确认</button>
            <div v-if="activeProblem.common_mistakes?.length" class="source-list">
              <span v-for="item in activeProblem.common_mistakes" :key="item" class="tag tag-warning">{{ item }}</span>
            </div>
            <div class="guided">
              <button class="row" @click="loadGuidance(1)"><ChevronDown :size="16" />思路</button>
              <p v-if="guidance[1]">{{ guidance[1].content }}</p>
              <button class="row" @click="loadGuidance(2)"><ChevronDown :size="16" />步骤</button>
              <p v-if="guidance[2]">{{ guidance[2].content }}</p>
              <button class="row" @click="loadGuidance(3)"><Lock :size="16" />解析</button>
              <p v-if="guidance[3]">{{ guidance[3].content }}</p>
              <div v-if="guidance[3]?.similar_questions?.length" class="source-list">
                <span v-for="item in guidance[3].similar_questions" :key="item" class="tag">{{ item }}</span>
              </div>
            </div>
          </div>
        </section>
        <aside class="card">
          <div class="card-head"><h2 class="card-title">记录</h2><button class="btn btn-ghost btn-sm" @click="loadProblemHistory">刷新</button></div>
          <div class="list">
            <button v-for="item in problemHistory" :key="item.id" class="row" @click="selectProblem(item)">
              <span>{{ item.corrected_text || item.ocr_text || item.raw_text }}</span>
            </button>
          </div>
        </aside>
      </section>

      <section v-if="active === 'learning'" class="page">
        <div class="toolbar">
          <select v-model.number="selectedCourseId" class="select short" @change="loadLearning">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <button class="btn btn-secondary" @click="loadLearning">刷新</button>
        </div>
        <div class="grid stats">
          <StatCard :icon="Layers" label="知识点" :value="knowledge.length" />
          <StatCard :icon="ClipboardList" label="测验" :value="quizzes.length" />
          <StatCard :icon="BookMarked" label="错题" :value="wrongQuestions.length" danger />
          <StatCard :icon="CalendarCheck" label="计划" :value="plans.length" />
          <StatCard v-if="records" :icon="MessageCircle" label="问答" :value="records.qa_count || 0" />
          <StatCard v-if="records" :icon="Play" label="学习" :value="records.progress_count || 0" />
        </div>
        <div class="split">
          <section class="card">
            <div class="card-head"><h2 class="card-title">测验</h2><button class="btn btn-ai btn-sm" @click="generateQuiz"><Sparkles :size="14" />生成</button></div>
            <div class="form-row">
              <input v-model="quizForm.title" class="input" placeholder="标题" />
              <select v-model="quizForm.quiz_type" class="select">
                <option value="practice">练习</option>
                <option value="wrong_book">错题</option>
                <option v-if="user.role !== 'student'" value="course">课程</option>
              </select>
            </div>
            <div class="list">
              <button v-for="quiz in quizzes" :key="quiz.id" class="row" @click="loadQuiz(quiz.id)">
                <span>{{ quiz.title }}</span>
                <span class="tag">{{ quiz.status }}</span>
              </button>
            </div>
            <div v-if="quizDetail" class="quiz">
              <h3>{{ quizDetail.quiz.title }}</h3>
              <div v-for="question in quizDetail.questions" :key="question.id" class="question">
                <strong>{{ question.stem }}</strong>
                <div v-if="question.question_type === 'multiple_choice' && question.options" class="checks">
                  <label v-for="(option, index) in question.options" :key="index" class="check">
                    <input type="checkbox" :value="index" @change="toggleMultiFromEvent(question.id, Number(index), $event)" />
                    {{ option }}
                  </label>
                </div>
                <select v-else-if="question.options" v-model="quizAnswers[question.id]" class="select">
                  <option v-for="(option, index) in question.options" :key="index" :value="index">{{ option }}</option>
                </select>
                <textarea v-else v-model="quizAnswers[question.id]" class="textarea"></textarea>
              </div>
              <div class="toolbar">
                <button v-if="user.role === 'student'" class="btn btn-primary" @click="submitQuiz">提交</button>
                <button v-if="user.role !== 'student'" class="btn btn-secondary" @click="publishQuiz">发布</button>
              </div>
              <span v-if="attempt" class="tag tag-success">得分 {{ attempt.score }}</span>
            </div>
          </section>
          <aside class="card">
            <div class="card-head"><h2 class="card-title">知识</h2><button class="btn btn-ghost btn-sm" @click="loadWrongPractice">重练</button></div>
            <select v-model="knowledgeLevel" class="select">
              <option value="beginner">入门</option><option value="standard">标准</option><option value="advanced">进阶</option>
            </select>
            <div class="list">
              <div v-for="item in knowledge" :key="item.id" class="ai-box mini">
                <span class="tag tag-ai">AI</span>
                <strong>{{ item.name }}</strong>
                <p>{{ knowledgeText(item) }}</p>
              </div>
              <div v-for="item in wrongQuestions" :key="item.wrong_question_id" class="row">
                <span>{{ item.knowledge_point_name || item.question.stem }}</span><span class="tag tag-danger">{{ item.wrong_count }}</span>
              </div>
              <div v-for="item in weakPoints" :key="item.knowledge_point" class="row">
                <span>{{ item.knowledge_point }}</span><span class="tag tag-warning">{{ item.wrong_count }}</span>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section v-if="active === 'plans'" class="page split">
        <section class="card">
          <div class="card-head"><h2 class="card-title">计划</h2><button class="btn btn-ai btn-sm" @click="createPlan"><Sparkles :size="14" />生成</button></div>
          <select v-model.number="selectedCourseId" class="select">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <input v-model="planForm.title" class="input" placeholder="标题" />
          <textarea v-model="planForm.goal" class="textarea" placeholder="目标"></textarea>
          <div class="form-row">
            <input v-model.number="planForm.available_days" class="input" type="number" />
            <input v-model.number="planForm.daily_minutes" class="input" type="number" />
          </div>
          <div class="list">
            <button v-for="plan in plans" :key="plan.id" class="row" @click="loadTasks(plan.id)">
              <span>{{ plan.title }}</span><span class="tag">{{ plan.status }}</span>
            </button>
          </div>
        </section>
        <aside class="card">
          <div class="card-head"><h2 class="card-title">任务</h2></div>
          <div class="list">
            <div v-for="task in tasks" :key="task.id" class="row">
              <span>{{ task.title }}</span>
              <button class="btn btn-secondary btn-xs" @click="checkinTask(task.id)">打卡</button>
            </div>
          </div>
        </aside>
      </section>

      <section v-if="active === 'analytics'" class="page">
        <div class="toolbar">
          <select v-model.number="selectedCourseId" class="select short" @change="loadAnalytics">
            <option :value="0">课程</option>
            <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
          </select>
          <input v-model.number="analyticsDays" class="input tiny" type="number" />
          <button class="btn btn-secondary" @click="loadAnalytics">查看</button>
        </div>
        <div v-if="analytics" class="grid stats">
          <StatCard :icon="MessageCircle" label="高频问" :value="analytics.high_frequency_questions?.length || 0" />
          <StatCard :icon="BookMarked" label="薄弱点" :value="analytics.weak_points?.length || 0" danger />
          <StatCard :icon="Users" label="低活跃" :value="analytics.inactive_students?.length || 0" />
          <StatCard :icon="BarChart2" label="完成率" :value="`${analytics.completion_rate || 0}%`" />
        </div>
        <div v-if="analytics" class="split">
          <article class="card"><RadarChart :items="radarItems" /></article>
          <article class="ai-box"><span class="tag tag-ai">AI</span><p>{{ analytics.suggestion }}</p></article>
        </div>
      </section>

      <AdminPanels
        v-if="isAdminPanel"
        :active="active"
        :notice="emitNotice"
      />

      <section v-if="active === 'profile'" class="page split">
        <section class="card">
          <div class="card-head"><h2 class="card-title">资料</h2><button class="btn btn-primary" @click="saveProfile">保存</button></div>
          <input v-model="profileForm.nickname" class="input" placeholder="昵称" />
          <input v-model="profileForm.avatar_url" class="input" placeholder="头像" />
          <textarea v-model="profileForm.bio" class="textarea" placeholder="简介"></textarea>
        </section>
        <aside class="card">
          <div class="card-head"><h2 class="card-title">密码</h2><button class="btn btn-primary" @click="changePassword">保存</button></div>
          <input v-model="passwordForm.old_password" class="input" type="password" placeholder="旧密码" />
          <input v-model="passwordForm.new_password" class="input" type="password" placeholder="新密码" />
        </aside>
      </section>
    </main>
  </section>

  <ModalPanel :open="showCourseForm" title="创建课程" @close="showCourseForm = false">
    <input v-model="courseForm.name" class="input" placeholder="课程名" />
    <input v-model="courseForm.term" class="input" placeholder="学期" />
    <textarea v-model="courseForm.description" class="textarea" placeholder="简介"></textarea>
    <template #footer>
      <button class="btn btn-secondary" @click="showCourseForm = false">取消</button>
      <button class="btn btn-primary" @click="createCourse">创建</button>
    </template>
  </ModalPanel>

  <ModalPanel :open="showUpload" title="上传资料" @close="showUpload = false">
    <select v-model.number="uploadForm.course_id" class="select" @change="loadUploadChapters">
      <option :value="0">课程</option>
      <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
    </select>
    <select v-model.number="uploadForm.chapter_id" class="select">
      <option :value="0">章节</option>
      <option v-for="chapter in uploadChapters" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
    </select>
    <input v-model="uploadForm.title" class="input" placeholder="标题" />
    <select v-model="uploadForm.category" class="select">
      <option value="courseware">课件</option>
      <option value="handout">讲义</option>
      <option value="exercise">练习</option>
      <option value="reference">参考</option>
    </select>
    <input type="file" class="input" @change="pickUploadFile" />
    <template #footer>
      <button class="btn btn-secondary" @click="showUpload = false">取消</button>
      <button class="btn btn-primary" @click="uploadMaterial">上传</button>
    </template>
  </ModalPanel>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import {
  AlertTriangle, ArrowLeft, BarChart2, Bell, BookMarked, BookOpen, Bot, CalendarCheck, ChevronDown,
  ClipboardList, GraduationCap, Layers, Lock, LogOut, MessageCircle, Pencil, Play, Plus, RefreshCw,
  Search, Send, Settings, Shield, SkipBack, SkipForward, Sparkles, Upload, User, Users, XCircle
} from "lucide-vue-next";
import { api } from "../api/client";
import CourseCard from "../components/CourseCard.vue";
import ModalPanel from "../components/ModalPanel.vue";
import RadarChart from "../components/RadarChart.vue";
import StatCard from "../components/StatCard.vue";
import type { Chapter, Course, CourseDetail, Lesson, LessonPage, Material, MaterialDetail, Quiz, User as UserType } from "../types";
import AdminPanels from "./admin/AdminPanels.vue";
import MaterialPanel from "./parts/MaterialPanel.vue";

const props = defineProps<{ user: UserType }>();
const emit = defineEmits<{ logout: []; notice: [type: "success" | "warning" | "error" | "info", text: string] }>();

const active = ref("courses");
const courses = ref<Course[]>([]);
const selectedCourseId = ref(0);
const courseDetail = ref<CourseDetail | null>(null);
const members = ref<any[]>([]);
const lessons = ref<Lesson[]>([]);
const classroomLesson = ref<{ lesson: Lesson; pages: LessonPage[] } | null>(null);
const currentPage = ref(1);
const classroomTab = ref<"script" | "qa">("script");
const materials = ref<Material[]>([]);
const materialDetail = ref<MaterialDetail | null>(null);
const qaHistory = ref<any[]>([]);
const qaResult = ref<any | null>(null);
const qaMessages = ref<Array<{ id: number; role: "user" | "ai"; text: string }>>([]);
const problemHistory = ref<any[]>([]);
const activeProblem = ref<any | null>(null);
const knowledge = ref<any[]>([]);
const quizzes = ref<Quiz[]>([]);
const quizDetail = ref<any | null>(null);
const wrongQuestions = ref<any[]>([]);
const weakPoints = ref<any[]>([]);
const plans = ref<any[]>([]);
const tasks = ref<any[]>([]);
const records = ref<any | null>(null);
const analytics = ref<any | null>(null);
const uploadChapters = ref<Chapter[]>([]);

const joinCode = ref("");
const showCourseForm = ref(false);
const showUpload = ref(false);
const selectedChapterId = ref<number | null>(null);
const qaQuestion = ref("");
const qaKeyword = ref("");
const problemText = ref("");
const correctedText = ref("");
const guidance = reactive<Record<number, any>>({});
const quizAnswers = reactive<Record<number, any>>({});
const attempt = ref<any | null>(null);
const analyticsDays = ref(30);
const uploadFile = ref<File | null>(null);
const knowledgeLevel = ref<"beginner" | "standard" | "advanced">("standard");

const courseForm = reactive({ name: "", term: "", description: "" });
const courseEdit = reactive({ name: "", term: "", description: "" });
const chapterForm = reactive({ title: "", description: "", order_index: 1 });
const materialFilter = reactive({ keyword: "", category: "" });
const uploadForm = reactive({ course_id: 0, chapter_id: 0, title: "", category: "courseware" });
const quizForm = reactive({ title: "章节练习", quiz_type: props.user.role === "student" ? "practice" : "course", question_count: 5 });
const planForm = reactive({ title: "复习计划", goal: "", available_days: 7, daily_minutes: 30 });
const profileForm = reactive({ nickname: props.user.nickname, avatar_url: props.user.avatar_url || "", bio: props.user.bio || "" });
const passwordForm = reactive({ old_password: "", new_password: "" });

const nav = computed(() => {
  if (props.user.role === "admin") {
    return [
      { key: "adminUsers", label: "用户管理", icon: Users },
      { key: "adminCourses", label: "课程管理", icon: BookOpen },
      { key: "adminMaterials", label: "资料审核", icon: Upload },
      { key: "adminModels", label: "模型配置", icon: Sparkles },
      { key: "adminServices", label: "服务配置", icon: Settings },
      { key: "adminSystem", label: "系统参数", icon: Shield },
      { key: "adminMonitor", label: "监控", icon: BarChart2 },
      { key: "adminLogs", label: "日志", icon: ClipboardList },
      { key: "adminBackups", label: "数据备份", icon: BookMarked },
      { key: "profile", label: "个人中心", icon: User }
    ];
  }
  if (props.user.role === "teacher") {
    return [
      { key: "courses", label: "我的课程", icon: BookOpen },
      { key: "materials", label: "课程资料", icon: Upload },
      { key: "lessons", label: "课堂学习", icon: GraduationCap },
      { key: "learning", label: "测验练习", icon: ClipboardList },
      { key: "analytics", label: "教学分析", icon: BarChart2 },
      { key: "courseDetail", label: "学生管理", icon: Users },
      { key: "profile", label: "个人中心", icon: User }
    ];
  }
  return [
    { key: "courses", label: "我的课程", icon: BookOpen },
    { key: "lessons", label: "课堂学习", icon: GraduationCap },
    { key: "qa", label: "问答历史", icon: MessageCircle },
    { key: "tutoring", label: "题目辅导", icon: Pencil },
    { key: "learning", label: "学习支持", icon: Layers },
    { key: "plans", label: "学习计划", icon: CalendarCheck },
    { key: "profile", label: "个人中心", icon: User }
  ];
});
const currentTitle = computed(() => nav.value.find((item) => item.key === active.value)?.label || "工作台");
const isAdminPanel = computed(() => active.value.startsWith("admin"));
const activePage = computed(() => classroomLesson.value?.pages.find((item) => item.page_number === currentPage.value));
const progressValue = computed(() => {
  const total = classroomLesson.value?.pages.length || 1;
  return Math.round((currentPage.value / total) * 100);
});
const radarItems = computed(() => (weakPoints.value.length ? weakPoints.value : analytics.value?.weak_points || []).map((item: any) => ({ name: item.knowledge_point || item.name || "知识点", value: item.wrong_count || 1 })));

function emitNotice(type: "success" | "warning" | "error" | "info", text: string) {
  emit("notice", type, text);
}
function statusClass(status: string) {
  if (["ready", "published", "active"].includes(status)) return "tag-success";
  if (["pending", "review"].includes(status)) return "tag-warning";
  if (["failed", "inactive"].includes(status)) return "tag-danger";
  return "";
}
function knowledgeText(item: any) {
  const content = item.content_by_level?.[knowledgeLevel.value];
  if (!content) return item.description || "";
  return [content.definition, content.principle, content.example, content.common_mistake].filter(Boolean).join(" ");
}
function toggleMulti(questionId: number, index: number, checked: boolean) {
  const current = Array.isArray(quizAnswers[questionId]) ? [...quizAnswers[questionId]] : [];
  quizAnswers[questionId] = checked ? [...new Set([...current, index])] : current.filter((item) => item !== index);
}
function toggleMultiFromEvent(questionId: number, index: number, event: Event) {
  toggleMulti(questionId, index, (event.target as HTMLInputElement).checked);
}
async function run<T>(task: () => Promise<T>, ok?: string) {
  try {
    const data = await task();
    if (ok) emitNotice("success", ok);
    return data;
  } catch (error) {
    emitNotice("error", (error as Error).message);
    return null;
  }
}
async function refresh() {
  if (active.value === "courses") await loadCourses();
  if (active.value === "materials") await loadMaterials();
  if (active.value === "lessons") await loadLessons();
  if (active.value === "qa") await loadQaHistory();
  if (active.value === "learning") await loadLearning();
  if (active.value === "plans") await loadPlans();
  if (active.value === "analytics") await loadAnalytics();
}
async function loadCourses() {
  const path = props.user.role === "student" ? "/courses/enrolled" : "/courses/teaching";
  courses.value = (await run(() => api.get<Course[]>(path))) || [];
  if (!selectedCourseId.value && courses.value[0]) selectedCourseId.value = courses.value[0].id;
}
async function openCourse(id: number) {
  selectedCourseId.value = id;
  const detail = await run(() => api.get<CourseDetail>(`/courses/${id}`));
  if (!detail) return;
  courseDetail.value = detail;
  Object.assign(courseEdit, {
    name: detail.course.name,
    term: detail.course.term,
    description: detail.course.description || ""
  });
  active.value = "courseDetail";
  await Promise.all([loadMembers(), loadCourseScoped()]);
}
async function createCourse() {
  await run(() => api.post<Course>("/courses", courseForm), "已创建");
  showCourseForm.value = false;
  Object.assign(courseForm, { name: "", term: "", description: "" });
  await loadCourses();
}
async function updateCourse() {
  if (!selectedCourseId.value) return;
  await run(() => api.patch(`/courses/${selectedCourseId.value}`, courseEdit), "已更新");
  await openCourse(selectedCourseId.value);
}
async function deactivateCourse() {
  if (!selectedCourseId.value) return;
  await run(() => api.post(`/courses/${selectedCourseId.value}/deactivate`), "已停用");
  await loadCourses();
}
async function joinCourse() {
  await run(() => api.post("/courses/join", { course_code: joinCode.value }), "已加入");
  joinCode.value = "";
  await loadCourses();
}
async function leaveCourse() {
  if (!selectedCourseId.value) return;
  await run(() => api.post(`/courses/${selectedCourseId.value}/leave`), "已退出");
  courseDetail.value = null;
  active.value = "courses";
  await loadCourses();
}
async function createChapter() {
  if (!selectedCourseId.value) return;
  await run(() => api.post(`/courses/${selectedCourseId.value}/chapters`, chapterForm), "已创建");
  Object.assign(chapterForm, { title: "", description: "", order_index: 1 });
  await openCourse(selectedCourseId.value);
}
async function loadMembers() {
  if (!selectedCourseId.value) return;
  members.value = (await run(() => api.get<any[]>(`/courses/${selectedCourseId.value}/members`))) || [];
}
async function loadCourseScoped() {
  await Promise.all([loadMaterials(), loadLessons(), loadLearning(), loadPlans()]);
}
async function loadMaterials() {
  materials.value = (await run(() => api.get<Material[]>("/materials", {
    course_id: selectedCourseId.value || undefined,
    keyword: materialFilter.keyword,
    category: materialFilter.category
  }))) || [];
}
async function loadMaterialDetail(id: number) {
  materialDetail.value = await run(() => api.get<MaterialDetail>(`/materials/${id}`));
}
function pickUploadFile(event: Event) {
  uploadFile.value = ((event.target as HTMLInputElement).files || [])[0] || null;
}
async function openUpload() {
  uploadForm.course_id = selectedCourseId.value || courses.value[0]?.id || 0;
  uploadForm.chapter_id = selectedChapterId.value || 0;
  await loadUploadChapters();
  showUpload.value = true;
}
async function loadUploadChapters() {
  uploadChapters.value = [];
  if (!uploadForm.course_id) return;
  const detail = await run(() => api.get<CourseDetail>(`/courses/${uploadForm.course_id}`));
  uploadChapters.value = detail?.chapters || [];
}
async function uploadMaterial() {
  if (!uploadFile.value || !uploadForm.course_id) return;
  const form = new FormData();
  form.set("course_id", String(uploadForm.course_id));
  form.set("title", uploadForm.title);
  form.set("category", uploadForm.category);
  if (uploadForm.chapter_id) form.set("chapter_id", String(uploadForm.chapter_id));
  form.set("file", uploadFile.value);
  await run(() => api.post("/materials", form), "已上传");
  showUpload.value = false;
  await loadMaterials();
}
async function reprocess(id: number) {
  await run(() => api.post(`/materials/${id}/reprocess`), "已重跑");
  await loadMaterials();
}
async function deleteMaterial(id: number) {
  await run(() => api.delete(`/materials/${id}`), "已删除");
  await loadMaterials();
}
async function updateMaterial(id: number, payload: { title: string; category: string }) {
  await run(() => api.patch(`/materials/${id}`, payload), "已更新");
  await loadMaterialDetail(id);
  await loadMaterials();
}
async function saveScript(pageId: number, script: string) {
  await run(() => api.patch(`/materials/pages/${pageId}/script`, { script_text: script }), "已保存");
  if (materialDetail.value) await loadMaterialDetail(materialDetail.value.material.id);
}
async function regenScript(pageId: number) {
  await run(() => api.post(`/materials/pages/${pageId}/script/regenerate`), "已生成");
  if (materialDetail.value) await loadMaterialDetail(materialDetail.value.material.id);
}
async function loadLessons() {
  if (!selectedCourseId.value) return;
  lessons.value = (await run(() => api.get<Lesson[]>("/lessons", { course_id: selectedCourseId.value }))) || [];
}
async function openLesson(id: number) {
  const detail = await run(() => api.get<{ lesson: Lesson; pages: LessonPage[] }>(`/lessons/${id}`));
  if (!detail) return;
  classroomLesson.value = detail;
  currentPage.value = 1;
  const progress = await run(() => api.get<any>(`/lessons/${id}/progress`));
  if (progress?.current_page) currentPage.value = progress.current_page;
}
async function publishLesson(id: number, publish: boolean) {
  await run(() => api.post(`/lessons/${id}/${publish ? "publish" : "unpublish"}`), publish ? "已发布" : "已撤回");
  await loadLessons();
}
function prevPage() { currentPage.value = Math.max(1, currentPage.value - 1); }
function nextPage() { currentPage.value = Math.min(classroomLesson.value?.pages.length || 1, currentPage.value + 1); }
async function saveProgress(completed: boolean) {
  if (!classroomLesson.value) return;
  await run(() => api.post(`/lessons/${classroomLesson.value!.lesson.id}/progress`, { current_page: currentPage.value, added_seconds: 60, completed }), "已保存");
}
async function askInClass() {
  if (!classroomLesson.value || !qaQuestion.value.trim()) return;
  const question = qaQuestion.value;
  qaMessages.value.push({ id: Date.now(), role: "user", text: question });
  qaQuestion.value = "";
  const data = await run(() => api.post<any>("/qa/ask", {
    course_id: classroomLesson.value!.lesson.course_id,
    lesson_page_id: activePage.value?.id,
    question
  }));
  if (data) qaMessages.value.push({ id: Date.now() + 1, role: "ai", text: data.answer });
}
async function askQuestion() {
  if (!selectedCourseId.value) return;
  qaResult.value = await run(() => api.post("/qa/ask", { course_id: selectedCourseId.value, question: qaQuestion.value }));
  qaQuestion.value = "";
  await loadQaHistory();
}
async function loadQaHistory() {
  qaHistory.value = (await run(() => api.get<any[]>("/qa/history", { course_id: selectedCourseId.value || undefined, keyword: qaKeyword.value }))) || [];
}
async function favoriteQa(id: number, value: boolean) {
  await run(() => api.post(`/qa/${id}/favorite`, { is_favorite: value }), "已收藏");
  await loadQaHistory();
}
async function feedbackQa(id: number, feedback: string) {
  await run(() => api.post(`/qa/${id}/feedback`, { feedback }), "已评价");
}
async function createTextProblem() {
  if (!selectedCourseId.value) return;
  activeProblem.value = await run(() => api.post("/tutoring/problems/text", { course_id: selectedCourseId.value, text: problemText.value }), "已提交");
  correctedText.value = activeProblem.value?.corrected_text || problemText.value;
  await loadProblemHistory();
}
async function createImageProblem(event: Event) {
  const file = ((event.target as HTMLInputElement).files || [])[0];
  if (!file || !selectedCourseId.value) return;
  const form = new FormData();
  form.set("course_id", String(selectedCourseId.value));
  form.set("file", file);
  activeProblem.value = await run(() => api.post("/tutoring/problems/image", form), "已识别");
  correctedText.value = activeProblem.value?.ocr_text || "";
  await loadProblemHistory();
}
function selectProblem(item: any) {
  activeProblem.value = item;
  correctedText.value = item.corrected_text || item.ocr_text || item.raw_text || "";
}
async function confirmProblem() {
  if (!activeProblem.value) return;
  activeProblem.value = await run(() => api.post(`/tutoring/problems/${activeProblem.value.id}/confirm`, { corrected_text: correctedText.value }), "已确认");
}
async function loadGuidance(level: number) {
  if (!activeProblem.value) return;
  guidance[level] = await run(() => api.get(`/tutoring/problems/${activeProblem.value.id}/guidance`, { level }));
}
async function loadProblemHistory() {
  problemHistory.value = (await run(() => api.get<any[]>("/tutoring/history", { course_id: selectedCourseId.value || undefined }))) || [];
}
async function loadLearning() {
  if (!selectedCourseId.value) return;
  knowledge.value = (await run(() => api.get<any[]>("/learning/knowledge-points", { course_id: selectedCourseId.value, chapter_id: selectedChapterId.value || undefined }))) || [];
  quizzes.value = (await run(() => api.get<Quiz[]>("/learning/quizzes", { course_id: selectedCourseId.value }))) || [];
  wrongQuestions.value = props.user.role === "student" ? ((await run(() => api.get<any[]>("/learning/wrong-questions", { course_id: selectedCourseId.value }))) || []) : [];
  weakPoints.value = (await run(() => api.get<any[]>("/learning/weak-points", { course_id: selectedCourseId.value }))) || [];
  records.value = props.user.role === "student" ? await run(() => api.get("/learning/records", { course_id: selectedCourseId.value })) : null;
}
async function generateQuiz() {
  if (!selectedCourseId.value) return;
  await run(() => api.post("/learning/quizzes/generate", { ...quizForm, course_id: selectedCourseId.value, chapter_id: selectedChapterId.value, question_count: Number(quizForm.question_count || 5) }), "已生成");
  await loadLearning();
}
async function loadQuiz(id: number) {
  quizDetail.value = await run(() => api.get(`/learning/quizzes/${id}`));
  attempt.value = null;
}
async function submitQuiz() {
  if (!quizDetail.value) return;
  const answers = Object.entries(quizAnswers).map(([question_id, answer]) => ({ question_id: Number(question_id), answer }));
  attempt.value = await run(() => api.post(`/learning/quizzes/${quizDetail.value.quiz.id}/submit`, { answers }), "已提交");
}
async function publishQuiz() {
  if (!quizDetail.value) return;
  await run(() => api.post(`/learning/quizzes/${quizDetail.value.quiz.id}/publish`), "已发布");
  await loadLearning();
}
async function loadWrongPractice() {
  if (!selectedCourseId.value) return;
  const quiz = await run(() => api.post<Quiz>("/learning/wrong-questions/practice", undefined, { course_id: selectedCourseId.value }), "已生成");
  if (quiz) await loadQuiz(quiz.id);
}
async function loadPlans() {
  plans.value = (await run(() => api.get<any[]>("/learning/plans", { course_id: selectedCourseId.value || undefined }))) || [];
}
async function createPlan() {
  if (!selectedCourseId.value) return;
  const data = await run(() => api.post<any>("/learning/plans", { ...planForm, course_id: selectedCourseId.value }), "已生成");
  if (data) tasks.value = data.tasks;
  await loadPlans();
}
async function loadTasks(planId: number) {
  tasks.value = (await run(() => api.get<any[]>(`/learning/plans/${planId}/tasks`))) || [];
}
async function checkinTask(taskId: number) {
  await run(() => api.post(`/learning/tasks/${taskId}/checkin`, { notes: "" }), "已打卡");
}
async function loadAnalytics() {
  if (!selectedCourseId.value) return;
  analytics.value = await run(() => api.get(`/analytics/courses/${selectedCourseId.value}`, { days: analyticsDays.value }));
}
async function saveProfile() {
  await run(() => api.patch("/auth/me", profileForm), "已保存");
}
async function changePassword() {
  await run(() => api.post("/auth/me/password", passwordForm), "已保存");
  Object.assign(passwordForm, { old_password: "", new_password: "" });
}

onMounted(async () => {
  await loadCourses();
  if (props.user.role === "admin") active.value = "adminUsers";
});
</script>

<style scoped>
.shell {
  display: grid;
  grid-template-columns: var(--sidebar-width) 1fr;
  grid-template-rows: var(--header-height) 1fr;
  min-height: 100vh;
}
.topbar {
  grid-column: 1 / -1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--space-8);
  border-bottom: 1px solid var(--color-border-default);
  background: var(--color-bg-surface);
}
.logo, .userbox { display: flex; align-items: center; gap: var(--space-3); }
.logo span {
  display: inline-flex;
  width: 34px;
  height: 34px;
  align-items: center;
  justify-content: center;
  color: var(--color-text-inverse);
  border-radius: var(--radius-md);
  background: var(--color-ai-gradient);
}
.sidebar {
  border-right: 1px solid var(--color-border-default);
  background: var(--color-bg-surface);
  padding: var(--space-6);
}
.nav-item {
  width: 100%;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  min-height: 40px;
  border: 0;
  border-radius: var(--radius-md);
  background: transparent;
  color: var(--color-text-secondary);
  padding: 0 var(--space-3);
  margin-bottom: var(--space-1);
  transition: all var(--duration-fast) var(--ease-out);
}
.nav-item:hover { background: var(--color-bg-muted); color: var(--color-text-primary); }
.nav-item.active { background: var(--color-primary-50); color: var(--color-primary-700); font-weight: var(--font-weight-medium); }
.workspace { padding: var(--space-8); overflow: auto; }
.short { max-width: 220px; }
.tiny { max-width: 96px; }
.ops { white-space: nowrap; }
.list { display: grid; gap: var(--space-2); }
.source-list, .checks {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin: var(--space-3) 0;
}
.check {
  display: inline-flex;
  align-items: center;
  gap: var(--space-2);
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
}
.row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  width: 100%;
  min-height: 40px;
  border: 1px solid var(--color-border-subtle);
  border-radius: var(--radius-md);
  background: var(--color-bg-surface);
  color: var(--color-text-body);
  padding: var(--space-2) var(--space-3);
  text-align: left;
}
.history, .question, .mini {
  display: grid;
  gap: var(--space-2);
  border-bottom: 1px solid var(--color-border-subtle);
  padding: var(--space-3) 0;
}
.history p, .mini p { margin: 0; color: var(--color-text-secondary); font-size: var(--text-body-sm); }
.result { margin-top: var(--space-4); }
.file { color: var(--color-text-secondary); }
.classroom { min-height: 100vh; background: #0F172A; color: var(--color-text-inverse); }
.slim {
  display: grid;
  grid-template-columns: auto 1fr 220px auto;
  align-items: center;
  gap: var(--space-4);
  height: var(--header-height-slim);
  padding: 0 var(--space-4);
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
}
.progress { height: 6px; overflow: hidden; border-radius: var(--radius-full); background: var(--color-bg-muted); }
.progress span { display: block; height: 100%; background: var(--color-primary-600); }
.learn { display: grid; grid-template-columns: minmax(0, 1fr) var(--ai-panel-width); height: calc(100vh - var(--header-height-slim)); }
.slide { position: relative; display: grid; grid-template-columns: 88px 1fr; gap: var(--space-5); padding: var(--space-8); }
.thumbs { display: grid; align-content: start; gap: var(--space-2); }
.thumb {
  height: 56px;
  border: 1px solid rgba(255,255,255,0.2);
  border-radius: var(--radius-md);
  background: rgba(255,255,255,0.08);
  color: var(--color-text-inverse);
}
.thumb.active { border: 2px solid var(--color-primary-500); }
.ppt {
  display: grid;
  align-content: center;
  min-height: 60vh;
  background: var(--color-bg-surface);
  color: var(--color-text-primary);
  border-radius: var(--radius-lg);
  padding: var(--space-10);
}
.ppt h2 { font-size: var(--text-h1); }
.ppt p { font-size: var(--text-body-lg); line-height: 26px; }
.subtitle {
  position: absolute;
  left: 50%;
  bottom: 96px;
  max-width: 80%;
  transform: translateX(-50%);
  border-radius: var(--radius-full);
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(8px);
  padding: var(--space-3) var(--space-6);
  font-size: var(--text-body-lg);
}
.player {
  position: absolute;
  left: 50%;
  bottom: var(--space-6);
  display: flex;
  align-items: center;
  gap: var(--space-2);
  transform: translateX(-50%);
  border-radius: var(--radius-full);
  background: rgba(255,255,255,0.9);
  color: var(--color-text-primary);
  padding: var(--space-2) var(--space-4);
  box-shadow: var(--shadow-lg);
}
.player audio { height: 32px; max-width: 260px; }
.ai-panel { background: var(--color-bg-surface); color: var(--color-text-body); padding: var(--space-5); overflow: auto; }
.tabbar { display: flex; gap: var(--space-2); margin-bottom: var(--space-4); }
.messages { display: grid; gap: var(--space-3); min-height: 300px; }
.bubble { display: flex; gap: var(--space-2); }
.bubble.user { justify-content: flex-end; }
.bubble p {
  max-width: 82%;
  margin: 0;
  border-radius: var(--radius-lg);
  padding: var(--space-3);
  background: var(--color-primary-600);
  color: var(--color-text-inverse);
}
.bubble.ai p {
  border-left: 3px solid var(--color-ai-purple);
  background: var(--color-bg-muted);
  color: var(--color-text-body);
}
.avatar {
  display: inline-flex;
  width: 32px;
  height: 32px;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-full);
  color: var(--color-text-inverse);
  background: var(--color-ai-gradient);
}
.askbar { display: grid; grid-template-columns: 1fr auto; gap: var(--space-2); margin-top: var(--space-4); }
@media (max-width: 1023px) {
  .shell { grid-template-columns: 64px 1fr; }
  .sidebar { padding: var(--space-3); }
  .nav-item { justify-content: center; padding: 0; font-size: 0; }
  .learn { grid-template-columns: 1fr; }
  .ai-panel { max-height: 42vh; }
}
</style>
