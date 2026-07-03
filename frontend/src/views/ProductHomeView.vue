<template>
  <PageLoader v-if="enteringWorkbench" />
  <main v-else class="ph">
    <!-- 全局点击火花 -->
    <ClickSpark spark-color="#00E5FF" :spark-count="11" :spark-radius="26" :duration="480" />

    <!-- 全页统一背景：一层贯穿全站的星野，消除分区之间的割裂感 -->
    <div class="ph-canvas" aria-hidden="true">
      <ParticleField :count="150" :colors="['#00E5FF', '#FFD54F', '#FF5722']" :speed="0.26" :link-distance="0" :parallax="0.04" />
    </div>

    <!-- ============ 导航 ============ -->
    <nav class="ph-nav">
      <div class="ph-nav-inner">
        <RouterLink to="/" class="ph-logo" aria-label="智学黑板首页">
          <BrandLogo class="ph-logo-mark" />
          <span class="ph-logo-text">智学黑板</span>
        </RouterLink>
        <div class="ph-nav-links">
          <a href="#magic">伴学魔法</a>
          <a href="#showcase">黑板会思考</a>
          <a href="#rooms">多端教室</a>
        </div>
        <div class="ph-nav-actions">
          <template v-if="user">
            <button type="button" class="ph-btn ph-btn-solid" @click="openWorkbench">进入工作台</button>
          </template>
          <template v-else>
            <RouterLink to="/auth" class="ph-btn ph-btn-ghost">登录</RouterLink>
            <RouterLink to="/auth?mode=register" class="ph-btn ph-btn-solid">免费注册</RouterLink>
          </template>
        </div>
      </div>
    </nav>

    <!-- ============ 英雄区 ============ -->
    <header class="ph-hero">
      <div class="ph-hero-aurora">
        <AuroraBackground :color-stops="['#00E5FF', '#FF5722', '#FFD54F']" :amplitude="1.3" :blend="0.5" :speed="0.9" />
      </div>
      <div class="ph-hero-veil" aria-hidden="true"></div>

      <div class="ph-hero-inner">
        <div class="ph-kicker">
          <Sparkles :size="15" />
          <ShinyText text="会思考的黑板 · ClassAgent" :speed="4.5" />
        </div>

        <h1 class="ph-title">
          <SplitText text="今天，黑板开始思考。" split-type="chars" :delay="55" :duration="720" :y-from="34" />
        </h1>

        <p class="ph-tagline">
          随时问懂
          <RotatingText
            class="ph-rotating"
            :texts="['每道难题', '每个概念', '每一章内容', '每道错题']"
            :interval="2100"
            :duration="520"
          />
          像有位专属老师
        </p>

        <p class="ph-sub">
          老师上传的课件与试卷，被 AI 化作只属于你的数字导师。<br />
          每一次提问，都基于你的课程作答——<strong>告别死记硬背。</strong>
        </p>

        <div class="ph-hero-cta">
          <StarBorder as="button" color="#00E5FF" :speed="5" class="ph-star" @click="goLearn">
            <span class="ph-star-label">开始我的自学<ArrowRight :size="18" /></span>
          </StarBorder>
          <button type="button" class="ph-btn-line" @click="goTeacher">
            <Presentation :size="18" />我是老师
          </button>
        </div>

        <div class="ph-scroll" aria-hidden="true">
          向下滚动，见证课堂进化
          <span class="ph-scroll-bar"></span>
        </div>
      </div>
    </header>

    <!-- ============ 数据条 ============ -->
    <section class="ph-stats">
      <AnimatedContent :distance="50" :duration="720">
        <div class="ph-stats-grid">
          <div class="ph-stat">
            <div class="ph-stat-num"><CountUp :to="5" :duration="1600" /><i>类题型</i></div>
            <p>选择 · 判断 · 填空 · 简答 · 计算，全自动出题</p>
          </div>
          <div class="ph-stat">
            <div class="ph-stat-num"><CountUp :to="3" :duration="1600" /><i>端教室</i></div>
            <p>学生 · 教师 · 教务，一套系统协同贯通</p>
          </div>
          <div class="ph-stat">
            <div class="ph-stat-num"><CountUp :to="24" :duration="1800" /><i>h 伴学</i></div>
            <p>随时提问，基于你的课程资料即时作答</p>
          </div>
          <div class="ph-stat">
            <div class="ph-stat-num"><CountUp :to="0" :duration="1400" /><i>题海</i></div>
            <p>只练薄弱点，把时间花在真正需要的地方</p>
          </div>
        </div>
      </AnimatedContent>
    </section>

    <!-- ============ 伴学魔法 ============ -->
    <section id="magic" class="ph-magic">
      <div class="ph-section-inner">
        <header class="ph-head">
          <span class="ph-eyebrow"><DecryptedText text="AI · 伴学魔法" trigger="view" :speed="42" /></span>
          <h2><GradientText :animation-speed="7">把整门课，变成会讲课的老师</GradientText></h2>
          <p>不是又一个搜索框，而是真正读懂你课程的伴学大脑。</p>
        </header>

        <div class="ph-magic-grid">
          <AnimatedContent v-for="(item, index) in magicCards" :key="item.title" :distance="60" :delay="index * 90" :duration="700">
            <SpotlightCard class="ph-magic-card" :spotlight-color="item.spot" :radius="340">
              <div class="ph-magic-icon" :style="{ '--mg': item.glow }">
                <component :is="item.icon" :size="24" />
              </div>
              <h3>{{ item.title }}</h3>
              <p>{{ item.desc }}</p>
              <span class="ph-magic-step">0{{ index + 1 }}</span>
            </SpotlightCard>
          </AnimatedContent>
        </div>
      </div>
    </section>

    <!-- ============ 黑板会思考(展示) ============ -->
    <section id="showcase" class="ph-showcase">
      <div class="ph-section-inner">
        <header class="ph-head">
          <span class="ph-eyebrow">LIVING BLACKBOARD</span>
          <h2><SplitText text="一块会读懂你的黑板" split-type="chars" :delay="45" /></h2>
        </header>

        <div class="ph-bento">
          <TiltedCard class="ph-bento-hero" :rotate-amplitude="9" :scale="1.03">
            <div class="ph-bento-panel ph-bento-chat">
              <div class="ph-chat-badge"><WandSparkles :size="14" />AI 伴学大脑</div>
              <p class="ph-chat-q">“这道动量题为什么车祸破坏力那么大？”</p>
              <p class="ph-chat-a">
                <ShinyText text="因为 F·Δt = Δp。碰撞时 Δt 极短，动量变化又固定，所以 F 会急剧增大——这正是安全气囊延长受力时间的意义。" :speed="6" />
              </p>
            </div>
          </TiltedCard>

          <SpotlightCard class="ph-bento-cell" spotlight-color="rgba(0,229,255,0.22)">
            <MessageCircle :size="22" class="ph-cell-ic cyan" />
            <h4>课程内精准问答</h4>
            <p>回答只来自你的课件，讲清“为什么”，不是空泛百科。</p>
          </SpotlightCard>

          <SpotlightCard class="ph-bento-cell" spotlight-color="rgba(255,87,34,0.22)">
            <BookOpen :size="22" class="ph-cell-ic orange" />
            <h4>错题变式重练</h4>
            <p>做错的题自动归档，AI 出同知识点新题，学会而非背答案。</p>
          </SpotlightCard>

          <SpotlightCard class="ph-bento-cell ph-bento-wide" spotlight-color="rgba(255,213,79,0.2)">
            <Cpu :size="22" class="ph-cell-ic gold" />
            <h4>看不见的学情雷达</h4>
            <p>系统默默追踪薄弱点，生成知识雷达图，靶向提升，摒弃盲目题海。</p>
          </SpotlightCard>
        </div>
      </div>
    </section>

    <!-- ============ 多端教室 ============ -->
    <section id="rooms" class="ph-rooms">
      <div class="ph-section-inner">
        <header class="ph-head">
          <span class="ph-eyebrow">THREE ROOMS · ONE CAMPUS</span>
          <h2><GradientText :animation-speed="8" :colors="['#00E5FF', '#FFD54F', '#FF5722', '#00E5FF']">不只是课本，更是教室</GradientText></h2>
          <p>三端协同，串起校园里每一次教与学。</p>
        </header>

        <div class="ph-rooms-grid">
          <TiltedCard v-for="role in roleCards" :key="role.title" class="ph-room" :rotate-amplitude="10" :scale="1.04">
            <article class="ph-room-body" :class="role.key">
              <div class="ph-room-icon"><component :is="role.icon" :size="26" /></div>
              <h3>{{ role.title }}</h3>
              <ul>
                <li v-for="line in role.lines" :key="line"><Check :size="15" />{{ line }}</li>
              </ul>
            </article>
          </TiltedCard>
        </div>
      </div>
    </section>

    <!-- ============ 结尾 CTA ============ -->
    <section class="ph-cta">
      <div class="ph-cta-inner">
        <h2 class="ph-cta-title"><GradientText :animation-speed="6">让每一次学习，都有回响。</GradientText></h2>
        <p class="ph-cta-sub">
          无论你是想彻底弄懂一道题的学生，还是想省下批改时间的老师——<br />
          现在就翻开这块会思考的黑板。
        </p>
        <div class="ph-cta-actions">
          <StarBorder as="button" color="#FFD54F" :speed="5" class="ph-star" @click="goLearn">
            <span class="ph-star-label"><Play :size="16" />免费开始</span>
          </StarBorder>
          <button v-if="!user" type="button" class="ph-btn-line" @click="goTeacher">
            <GraduationCap :size="18" />教师账号入口
          </button>
        </div>
      </div>
    </section>

    <!-- ============ 页脚 ============ -->
    <footer class="ph-footer">
      <div class="ph-footer-brand">
        <BrandLogo class="ph-logo-mark" />
        <span>智学黑板</span>
      </div>
      <p>让知识在校园里生长。</p>
      <span class="ph-footer-copy">© 2026 ClassAgent · 智学黑板</span>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRouter } from "vue-router";
import BrandLogo from "../components/BrandLogo.vue";
import PageLoader from "../components/PageLoader.vue";
import {
  ArrowRight,
  BookOpen,
  Check,
  Cpu,
  GraduationCap,
  Layers,
  MessageCircle,
  Play,
  Presentation,
  SlidersHorizontal,
  Sparkles,
  WandSparkles,
  Zap,
} from "../icons";
import { defaultRouteForRole } from "../router/pageMap";
import type { User } from "../types";
// React Bits 特效（已移植为 Vue）
import AuroraBackground from "../components/reactbits/AuroraBackground.vue";
import ParticleField from "../components/reactbits/ParticleField.vue";
import ClickSpark from "../components/reactbits/ClickSpark.vue";
import SplitText from "../components/reactbits/SplitText.vue";
import GradientText from "../components/reactbits/GradientText.vue";
import ShinyText from "../components/reactbits/ShinyText.vue";
import RotatingText from "../components/reactbits/RotatingText.vue";
import DecryptedText from "../components/reactbits/DecryptedText.vue";
import CountUp from "../components/reactbits/CountUp.vue";
import SpotlightCard from "../components/reactbits/SpotlightCard.vue";
import TiltedCard from "../components/reactbits/TiltedCard.vue";
import StarBorder from "../components/reactbits/StarBorder.vue";
import AnimatedContent from "../components/reactbits/AnimatedContent.vue";

const props = defineProps<{ user: User | null }>();
const router = useRouter();
const enteringWorkbench = ref(false);
const user = computed(() => props.user);
const workbenchPath = computed(() => defaultRouteForRole(props.user?.role));

async function openWorkbench() {
  if (enteringWorkbench.value) return;
  enteringWorkbench.value = true;
  const failure = await router.push(workbenchPath.value);
  if (failure) enteringWorkbench.value = false;
}

function goLearn() {
  if (props.user) {
    void openWorkbench();
    return;
  }
  void router.push("/auth?mode=register");
}

function goTeacher() {
  if (props.user?.role === "teacher") {
    void router.push("/teacher");
    return;
  }
  if (props.user) {
    void openWorkbench();
    return;
  }
  void router.push("/auth");
}

const magicCards = [
  { title: "开箱即用", desc: "老师上传的课件与试卷，被自动切片成你能随时对话的知识库。", icon: Layers, spot: "rgba(0,229,255,0.22)", glow: "#00E5FF" },
  { title: "直击本质", desc: "每个回答都基于你的课程资料，讲清“为什么”，而不是甩给你一段百科。", icon: WandSparkles, spot: "rgba(255,87,34,0.22)", glow: "#FF5722" },
  { title: "错题成长", desc: "做错的题自动进错题本，AI 出同知识点的变式题，让你真正学会而非背答案。", icon: BookOpen, spot: "rgba(255,213,79,0.2)", glow: "#FFD54F" },
  { title: "学情看得见", desc: "系统默默记录薄弱点，生成知识雷达，让复习靶向而高效。", icon: Zap, spot: "rgba(0,229,255,0.22)", glow: "#00E5FF" },
] as const;

const roleCards = [
  {
    key: "student",
    title: "学生自学空间",
    icon: GraduationCap,
    lines: ["沉浸式课件播放与阅读", "课程范围内的精准伴学问答", "错题归档与考前复习卷"],
  },
  {
    key: "teacher",
    title: "教师执教台",
    icon: Presentation,
    lines: ["上传即用的资料库", "随堂测验一键下发与秒批", "班级掌握度一目了然"],
  },
  {
    key: "admin",
    title: "教务管理",
    icon: SlidersHorizontal,
    lines: ["账号、班级与课程井井有条", "权限清晰、数据各归其位", "安心照看整个校园的学习"],
  },
] as const;
</script>

<style scoped>
.ph {
  --ph-bg: #060809;
  --ph-ink: #eef2f5;
  --ph-muted: #93a0aa;
  --ph-cyan: #00e5ff;
  --ph-orange: #ff5722;
  --ph-gold: #ffd54f;
  position: relative;
  width: 100%;
  min-height: 100vh;
  background: var(--ph-bg);
  color: var(--ph-ink);
  font-family: var(--ca-font-sans, -apple-system, "PingFang SC", sans-serif);
  overflow-x: hidden;
}

/* 背景层通用 */
.ph-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.ph-bg-soft { opacity: 0.7; }
.ph-bg-dim { opacity: 0.5; }
/* 全页统一星野：固定铺满，贯穿所有分区，消除背景割裂 */
.ph-canvas {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.5;
}
.ph-hero-aurora {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}

/* ============ 导航 ============ */
.ph-nav {
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(18px);
  background: rgba(6, 8, 9, 0.55);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}
.ph-nav-inner {
  max-width: 1200px;
  margin: 0 auto;
  padding: 14px 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
}
.ph-logo {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  text-decoration: none;
  color: var(--ph-ink);
}
.ph-logo-mark { width: 30px; height: 30px; }
.ph-logo-text { font-weight: 800; font-size: 18px; letter-spacing: 0.02em; }
.ph-nav-links { display: flex; gap: 28px; }
.ph-nav-links a {
  color: var(--ph-muted);
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}
.ph-nav-links a:hover { color: var(--ph-cyan); }
.ph-nav-actions { display: flex; align-items: center; gap: 12px; }
.ph-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 9px 18px;
  border-radius: 999px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;
  border: 1px solid transparent;
  transition: transform 0.18s, background 0.2s, border-color 0.2s;
}
.ph-btn-ghost { color: var(--ph-ink); border-color: rgba(255, 255, 255, 0.16); background: transparent; }
.ph-btn-ghost:hover { border-color: var(--ph-cyan); color: var(--ph-cyan); }
.ph-btn-solid {
  color: #041014;
  background: linear-gradient(120deg, var(--ph-cyan), #7ff0ff);
  box-shadow: 0 6px 22px rgba(0, 229, 255, 0.28);
}
.ph-btn-solid:hover { transform: translateY(-2px); }

/* ============ 英雄区 ============ */
.ph-hero {
  position: relative;
  min-height: 92vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  padding: 80px 24px 100px;
}
.ph-hero-veil {
  position: absolute;
  inset: 0;
  z-index: 1;
  background:
    radial-gradient(60% 50% at 50% 42%, transparent 40%, rgba(6, 8, 9, 0.55) 100%),
    linear-gradient(to bottom, rgba(6, 8, 9, 0.35), transparent 30%, rgba(6, 8, 9, 0.9) 100%);
  pointer-events: none;
}
.ph-hero-inner {
  position: relative;
  z-index: 2;
  max-width: 900px;
  text-align: center;
}
.ph-kicker {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  border-radius: 999px;
  border: 1px solid rgba(0, 229, 255, 0.28);
  background: rgba(0, 229, 255, 0.06);
  color: var(--ph-cyan);
  font-size: 13px;
  letter-spacing: 0.04em;
  margin-bottom: 26px;
}
.ph-title {
  font-size: clamp(2.6rem, 7vw, 5.2rem);
  line-height: 1.08;
  font-weight: 900;
  letter-spacing: -0.01em;
  margin: 0 0 22px;
  text-shadow: 0 4px 40px rgba(0, 229, 255, 0.18);
}
.ph-tagline {
  font-size: clamp(1.1rem, 2.6vw, 1.6rem);
  font-weight: 600;
  color: #d7dee3;
  margin: 0 0 18px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: center;
}
.ph-rotating {
  color: var(--ph-cyan);
  font-weight: 800;
  padding: 0 4px;
}
.ph-sub {
  font-size: clamp(0.98rem, 2vw, 1.18rem);
  line-height: 1.9;
  color: var(--ph-muted);
  margin: 0 auto 38px;
  max-width: 680px;
}
.ph-sub strong { color: var(--ph-gold); font-weight: 700; }
.ph-hero-cta {
  display: flex;
  gap: 16px;
  justify-content: center;
  align-items: center;
  flex-wrap: wrap;
}
.ph-star { font-weight: 700; }
.ph-star-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ph-ink);
  font-size: 15px;
}
.ph-btn-line {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 13px 26px;
  border-radius: 14px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.02);
  color: var(--ph-ink);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.18s, background 0.2s;
}
.ph-btn-line:hover { border-color: var(--ph-orange); color: var(--ph-orange); transform: translateY(-2px); }
.ph-scroll {
  margin-top: 60px;
  color: var(--ph-muted);
  font-size: 12px;
  letter-spacing: 0.1em;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
}
.ph-scroll-bar {
  width: 1px;
  height: 42px;
  background: linear-gradient(to bottom, var(--ph-cyan), transparent);
  animation: ph-scroll-pulse 1.8s ease-in-out infinite;
}
@keyframes ph-scroll-pulse {
  0%, 100% { opacity: 0.3; transform: scaleY(0.6); }
  50% { opacity: 1; transform: scaleY(1); }
}

/* ============ 数据条 ============ */
.ph-stats {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 0 auto;
  padding: 10px 24px 60px;
}
.ph-stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  padding: 34px;
  border-radius: 22px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.04), rgba(255, 255, 255, 0.01));
  backdrop-filter: blur(8px);
}
.ph-stat { text-align: center; }
.ph-stat-num {
  font-size: clamp(2rem, 4vw, 2.8rem);
  font-weight: 900;
  background: linear-gradient(120deg, var(--ph-cyan), var(--ph-gold));
  -webkit-background-clip: text;
  background-clip: text;
  -webkit-text-fill-color: transparent;
  display: inline-flex;
  align-items: baseline;
}
.ph-stat-num i {
  font-size: 0.9rem;
  font-style: normal;
  font-weight: 700;
  color: var(--ph-muted);
  -webkit-text-fill-color: var(--ph-muted);
  margin-left: 4px;
}
.ph-stat p { margin: 8px 0 0; font-size: 13px; color: var(--ph-muted); line-height: 1.6; }

/* ============ 分区通用 ============ */
.ph-magic,
.ph-showcase,
.ph-rooms,
.ph-cta {
  position: relative;
  overflow: hidden;
  padding: 110px 24px;
}
/* 每区一抹极淡的品牌辉光作为变化，但共用同一星野底，不再是硬色块 */
.ph-magic::before,
.ph-showcase::before,
.ph-rooms::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
}
.ph-magic::before { background: radial-gradient(46% 40% at 12% 6%, rgba(255, 87, 34, 0.07), transparent 68%); }
.ph-showcase::before { background: radial-gradient(48% 44% at 88% 16%, rgba(0, 229, 255, 0.07), transparent 68%); }
.ph-rooms::before { background: radial-gradient(60% 42% at 50% 104%, rgba(255, 213, 79, 0.06), transparent 70%); }
/* CTA：三色柔光模拟极光收束，纯 CSS，避免裁切文字叠在 WebGL 上碎裂 */
.ph-cta::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background:
    radial-gradient(52% 60% at 50% 42%, rgba(0, 229, 255, 0.12), transparent 70%),
    radial-gradient(42% 52% at 18% 82%, rgba(255, 87, 34, 0.09), transparent 70%),
    radial-gradient(42% 52% at 82% 88%, rgba(255, 213, 79, 0.08), transparent 70%);
}
.ph-section-inner {
  position: relative;
  z-index: 2;
  max-width: 1200px;
  margin: 0 auto;
}
.ph-head { text-align: center; margin-bottom: 60px; }
.ph-eyebrow {
  display: inline-block;
  font-size: 12px;
  letter-spacing: 0.24em;
  color: var(--ph-cyan);
  font-weight: 700;
  margin-bottom: 16px;
  font-family: var(--ca-font-mono, monospace);
}
.ph-head h2 {
  font-size: clamp(1.8rem, 4.4vw, 3rem);
  font-weight: 900;
  margin: 0 0 14px;
  line-height: 1.2;
}
.ph-head p { color: var(--ph-muted); font-size: clamp(0.95rem, 2vw, 1.1rem); margin: 0; }

/* ============ 伴学魔法 ============ */
.ph-magic-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 22px;
}
.ph-magic-card {
  position: relative;
  padding: 30px 26px 34px;
  border-radius: 20px;
  min-height: 230px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: rgba(255, 255, 255, 0.025);
  height: 100%;
}
.ph-magic-icon {
  width: 52px;
  height: 52px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: var(--mg);
  background: color-mix(in srgb, var(--mg) 14%, transparent);
  border: 1px solid color-mix(in srgb, var(--mg) 40%, transparent);
  box-shadow: 0 0 26px color-mix(in srgb, var(--mg) 30%, transparent);
  margin-bottom: 20px;
}
.ph-magic-card h3 { margin: 0 0 10px; font-size: 19px; font-weight: 800; }
.ph-magic-card p { margin: 0; color: var(--ph-muted); font-size: 14px; line-height: 1.75; }
.ph-magic-step {
  position: absolute;
  top: 22px;
  right: 24px;
  font-family: var(--ca-font-mono, monospace);
  font-size: 26px;
  font-weight: 900;
  color: rgba(255, 255, 255, 0.07);
}

/* ============ 展示 bento ============ */
.ph-bento {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  grid-auto-rows: minmax(150px, auto);
  gap: 20px;
}
.ph-bento-hero { grid-row: span 2; }
.ph-bento-wide { grid-column: span 2; }
.ph-bento-panel,
.ph-bento-cell {
  height: 100%;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(10, 16, 18, 0.72);
  padding: 26px;
}
.ph-bento-hero :deep(.tilted-card),
.ph-bento-hero :deep([class*="tilt"]) { height: 100%; }
.ph-bento-chat { display: flex; flex-direction: column; gap: 16px; }
.ph-chat-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(0, 229, 255, 0.12);
  color: var(--ph-cyan);
  font-size: 12px;
  font-weight: 700;
}
.ph-chat-q { font-size: 18px; font-weight: 700; color: #dfe6ea; margin: 0; }
.ph-chat-a { font-size: 15px; line-height: 1.85; margin: 0; color: #b9c4ca; }
.ph-bento-cell { display: flex; flex-direction: column; gap: 8px; }
.ph-cell-ic { margin-bottom: 4px; }
.ph-cell-ic.cyan { color: var(--ph-cyan); }
.ph-cell-ic.orange { color: var(--ph-orange); }
.ph-cell-ic.gold { color: var(--ph-gold); }
.ph-bento-cell h4 { margin: 0; font-size: 16px; font-weight: 800; }
.ph-bento-cell p { margin: 0; font-size: 13.5px; line-height: 1.7; color: var(--ph-muted); }

/* ============ 多端教室 ============ */
.ph-rooms-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 24px;
}
.ph-room-body {
  height: 100%;
  padding: 34px 28px;
  border-radius: 20px;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: rgba(255, 255, 255, 0.025);
}
.ph-room-icon {
  width: 56px;
  height: 56px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  margin-bottom: 20px;
}
.ph-room-body h3 { margin: 0 0 18px; font-size: 20px; font-weight: 800; }
.ph-room-body ul { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 12px; }
.ph-room-body li {
  display: flex;
  align-items: flex-start;
  gap: 9px;
  font-size: 14px;
  color: #c4cdd2;
  line-height: 1.5;
}
.ph-room-body li svg { flex: none; margin-top: 3px; }
.ph-room-body.student .ph-room-icon { color: var(--ph-cyan); background: rgba(0, 229, 255, 0.12); box-shadow: 0 0 30px rgba(0, 229, 255, 0.3); }
.ph-room-body.student li svg { color: var(--ph-cyan); }
.ph-room-body.teacher .ph-room-icon { color: var(--ph-orange); background: rgba(255, 87, 34, 0.12); box-shadow: 0 0 30px rgba(255, 87, 34, 0.3); }
.ph-room-body.teacher li svg { color: var(--ph-orange); }
.ph-room-body.admin .ph-room-icon { color: var(--ph-gold); background: rgba(255, 213, 79, 0.12); box-shadow: 0 0 30px rgba(255, 213, 79, 0.28); }
.ph-room-body.admin li svg { color: var(--ph-gold); }

/* ============ 结尾 CTA ============ */
.ph-cta { text-align: center; padding: 130px 24px; }
.ph-cta-veil {
  position: absolute;
  inset: 0;
  z-index: 1;
  background: radial-gradient(70% 60% at 50% 50%, transparent 30%, rgba(6, 8, 9, 0.8) 100%);
  pointer-events: none;
}
.ph-cta-inner { position: relative; z-index: 2; max-width: 760px; margin: 0 auto; }
.ph-cta-title { font-size: clamp(2rem, 5.5vw, 3.6rem); font-weight: 900; line-height: 1.2; margin: 0 0 20px; }
.ph-cta-sub { color: #c2ccd2; font-size: clamp(1rem, 2.2vw, 1.2rem); line-height: 1.9; margin: 0 0 40px; }
.ph-cta-actions { display: flex; gap: 16px; justify-content: center; align-items: center; flex-wrap: wrap; }

/* ============ 页脚 ============ */
.ph-footer {
  position: relative;
  z-index: 2;
  text-align: center;
  padding: 50px 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}
.ph-footer-brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  font-weight: 800;
  font-size: 17px;
  margin-bottom: 10px;
}
.ph-footer-brand .ph-logo-mark { width: 26px; height: 26px; }
.ph-footer p { color: var(--ph-muted); margin: 0 0 8px; font-size: 14px; }
.ph-footer-copy { color: rgba(147, 160, 170, 0.6); font-size: 12px; }

/* ============ 响应式 ============ */
@media (max-width: 960px) {
  .ph-nav-links { display: none; }
  .ph-stats-grid { grid-template-columns: repeat(2, 1fr); }
  .ph-magic-grid { grid-template-columns: repeat(2, 1fr); }
  .ph-bento { grid-template-columns: 1fr 1fr; }
  .ph-bento-hero { grid-row: span 1; grid-column: span 2; }
  .ph-bento-wide { grid-column: span 2; }
  .ph-rooms-grid { grid-template-columns: 1fr; }
}
@media (max-width: 560px) {
  .ph-stats-grid,
  .ph-magic-grid,
  .ph-bento { grid-template-columns: 1fr; }
  .ph-bento-hero,
  .ph-bento-wide { grid-column: span 1; }
  .ph-hero { min-height: 88vh; padding: 60px 20px 80px; }
}
</style>
