<template>
  <main class="product-home">
    <div class="board-texture"></div>
    <div class="board-smudge"></div>

    <nav id="hero" class="product-nav">
      <div class="product-nav-inner">
        <RouterLink to="/" class="product-logo">智学黑板<span>.</span></RouterLink>
        <div class="product-nav-links">
          <a href="#hero">核心指引</a>
          <a href="#book-section">伴学魔法</a>
          <a href="#roles">多端教室</a>
        </div>
        <div class="product-nav-actions">
          <RouterLink to="/auth" class="login-link">登录账号</RouterLink>
          <RouterLink to="/auth" class="register-link">免费注册学生端</RouterLink>
        </div>
      </div>
    </nav>

    <div ref="trackRef" class="scroll-track">
      <div ref="stageRef" class="home-stage">
        <section ref="sceneBlackboardRef" class="scene-blackboard">
          <canvas ref="formulaCanvasRef" class="formula-writing-canvas" aria-hidden="true"></canvas>

          <div class="formula-corner left">
            <svg width="250" height="250" viewBox="0 0 250 250" class="chalk-svg" aria-hidden="true">
              <circle cx="100" cy="100" r="50" class="draw-path" />
              <path d="M100,100 L200,40" class="draw-path delay-1" />
              <path d="M100,100 L110,200" class="draw-path delay-2" />
              <text x="150" y="30" class="formula-text">F = m·a</text>
              <text x="120" y="180" class="formula-text">m·g</text>
            </svg>
          </div>

          <div class="formula-corner right">
            <svg width="200" height="200" viewBox="0 0 200 200" class="chalk-svg" aria-hidden="true">
              <polygon points="100,30 160,65 160,135 100,170 40,135 40,65" class="draw-path delay-1" />
              <line x1="100" y1="30" x2="100" y2="0" class="draw-path delay-3" />
            </svg>
          </div>

          <div class="classic-quote">“学而不思则罔，<br />思而不学则殆。”</div>

          <div class="hero-center">
            <p class="chalk-kicker">人类在黑板前仰望了三百年，</p>

            <div
              ref="heroTextRef"
              class="ai-scanner-container"
              @mousemove="handleHeroMouseMove"
              @mouseleave="handleHeroMouseLeave"
            >
              <span>今天，黑板开始思考。</span>
              <div ref="heroGlowRef" class="ai-reveal-layer">全知伴学引擎_已激活</div>
            </div>

            <p class="hero-copy">
              上传你的课本、试卷与错题。<br />
              系统将其化作专属于你的数字导师网。<br />
              <strong>告别死记硬背，每一次提问，都直击知识本质。</strong>
            </p>

            <div class="hero-actions">
              <RouterLink to="/home" class="hand-drawn-link">
                <span>进入我的自学空间</span>
                <ArrowRight :size="20" />
                <svg viewBox="0 0 100 40" preserveAspectRatio="none" aria-hidden="true">
                  <path d="M5,20 Q50,0 95,20 Q50,40 5,20" />
                </svg>
              </RouterLink>
              <RouterLink to="/teacher" class="teacher-console-link">
                <Presentation :size="22" />
                教师执教控制台
              </RouterLink>
            </div>

            <div class="scroll-hint">
              向下滚动，见证课堂的进化
              <i></i>
            </div>
          </div>
        </section>

        <div id="book-section" ref="sceneBookRef" class="scene-book">
          <div class="book">
            <div class="paper-texture"></div>
            <div class="book-spine"></div>

            <div class="book-base-left">
              <div class="book-final-left">
                <div class="book-icon-circle"><BookOpen :size="34" /></div>
                <h2>知识的重构</h2>
                <p>The Next Generation of Learning</p>
                <span class="page-footer-number left">Preface / IV</span>
              </div>
            </div>

            <div class="book-base-right">
              <div class="book-final-right">
                <span class="page-label">FIN.</span>
                <h2>这不是结束。</h2>
                <p>
                  这只是一本随时待命的字典。当你遇到难题，当你需要规划，当你想要深究背后的逻辑。<br /><br />
                  请随时翻开这本会思考的书。
                </p>
                <footer>
                  <p>向下滑动，探索多端教室配置</p>
                  <ArrowDown class="bounce-arrow" :size="28" />
                </footer>
              </div>
            </div>

            <div ref="page2Ref" class="book-page page-two">
              <div class="page-front">
                <div ref="shadow2FrontRef" class="page-shadow-front"></div>
                <span class="page-no right">03</span>
                <h3 class="living-book-title">现在，课本活了过来。</h3>
                <div class="paper-note">
                  “动量定理告诉我们，物体动量的变化量等于它所受合外力的冲量。即：
                  <br /><span class="formula-span">F·Δt = Δp</span>”
                  <div class="ai-sticker">
                    <div><WandSparkles :size="15" />AI 伴学大脑</div>
                    <p>
                      注意这个公式！如果把时间 Δt 极度缩短，力 F 会极大。这就解释了为何车祸破坏力惊人。
                    </p>
                  </div>
                </div>
              </div>

              <div class="page-back dark-page">
                <div ref="shadow2BackRef" class="page-shadow-back"></div>
                <span class="page-no left">04</span>
                <div class="data-network">
                  <h3>看不见的学情网络</h3>
                  <p>系统静默追踪错题，摒弃盲目题海，自动生成知识雷达图，进行靶向提升。</p>
                  <div class="radar-demo">
                    <svg viewBox="0 0 100 100" aria-hidden="true">
                      <polygon points="50,5 90,35 75,85 25,85 10,35" stroke-width="1" />
                      <polygon points="50,25 70,45 60,70 40,70 30,45" stroke-width="1" />
                      <circle cx="50" cy="50" r="2" fill="#fff" />
                    </svg>
                    <span>DATA_ACTIVE</span>
                  </div>
                </div>
              </div>
            </div>

            <div ref="page1Ref" class="book-page page-one">
              <div class="page-front">
                <div ref="shadow1FrontRef" class="page-shadow-front"></div>
                <span class="page-no right">01</span>
                <div class="chapter-label">CHAPTER I. THE PAST</div>
                <h3>曾经，<br />学习是一座孤岛。</h3>
                <p class="book-copy">
                  面对厚重的印刷讲义，跳跃的公式步骤总让人在深夜抓狂。不会做的错题，即使看了答案依然一知半解。在题海中盲目地刷着重复的卷子，却不知真正的薄弱点藏在哪里。
                </p>
                <div class="wrong-paper">
                  <p class="wrong-text">“这道几何题到底怎么做...”</p>
                  <div class="wrong-footer">
                    <span>Student Reflection Card</span>
                    <div class="wrong-x">X</div>
                  </div>
                </div>
              </div>

              <div class="page-back">
                <div ref="shadow1BackRef" class="page-shadow-back"></div>
                <span class="page-no left">02</span>
                <div class="turn-hint">
                  <ArrowRight :size="64" />
                  <strong>翻页，<br />唤醒沉睡的文字。</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <section id="roles" class="roles-section">
      <div class="section-inner">
        <header>
          <h2>不只是课本，更是教室。</h2>
          <p>三端协同，构建校园的数字化闭环</p>
        </header>

        <div class="role-grid">
          <article class="role-card student">
            <div class="role-icon"><GraduationCap :size="28" /></div>
            <h3>学生伴学控制台</h3>
            <ul>
              <li><Check :size="16" />沉浸式课件播放与阅读。</li>
              <li><Check :size="16" />课程范围内的精准伴学问答。</li>
              <li><Check :size="16" />错题归档与生成考前复习卷。</li>
            </ul>
          </article>

          <article class="role-card teacher">
            <div class="role-icon"><Presentation :size="28" /></div>
            <h3>教师教研指挥舱</h3>
            <ul>
              <li><Check :size="16" />极速上传资料，静默切片向量化。</li>
              <li><Check :size="16" />随堂测验下发与客观题秒批。</li>
              <li><Check :size="16" />班级掌握度雷达与预警推送。</li>
            </ul>
          </article>

          <article class="role-card admin">
            <div class="role-icon"><SlidersHorizontal :size="28" /></div>
            <h3>运维管理底层</h3>
            <ul>
              <li><Check :size="16" />灵活配置各家大模型接口路由。</li>
              <li><Check :size="16" />阿里云多模态服务无缝集成。</li>
              <li><Check :size="16" />RBAC 权限分配与数据隔离。</li>
            </ul>
          </article>
        </div>
      </div>
    </section>

    <footer class="product-footer">
      <h2>将知识留在校园。</h2>
      <p>
        支持教育机构完整私有化部署。后端基于 FastAPI，前端搭载 Vue3，接管核心教务数据资产，构建真正属于您自己的智能基建。
      </p>
      <div>
        <RouterLink to="/auth" class="trial-link">申请校园试用授权</RouterLink>
        <a href="/docs/api" class="docs-link">审阅 API 开发文档</a>
      </div>
    </footer>
  </main>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { ArrowDown, ArrowRight, BookOpen, Check, GraduationCap, Presentation, SlidersHorizontal, WandSparkles } from "lucide-vue-next";

const heroTextRef = ref<HTMLElement | null>(null);
const heroGlowRef = ref<HTMLElement | null>(null);
const trackRef = ref<HTMLElement | null>(null);
const stageRef = ref<HTMLElement | null>(null);
const sceneBlackboardRef = ref<HTMLElement | null>(null);
const sceneBookRef = ref<HTMLElement | null>(null);
const formulaCanvasRef = ref<HTMLCanvasElement | null>(null);
const page1Ref = ref<HTMLElement | null>(null);
const page2Ref = ref<HTMLElement | null>(null);
const shadow1FrontRef = ref<HTMLElement | null>(null);
const shadow1BackRef = ref<HTMLElement | null>(null);
const shadow2FrontRef = ref<HTMLElement | null>(null);
const shadow2BackRef = ref<HTMLElement | null>(null);

let frameId = 0;
let formulaFrameId = 0;
let formulaCycleStart = 0;
const homeActiveClass = "product-home-active";

const dynamicFormulas = [
  { text: "lim(x→0)  sin x / x = 1", x: 0.66, y: 0.82, size: 30, rotate: -4 },
  { text: "F = m · a", x: 0.68, y: 0.26, size: 42, rotate: 4 },
  { text: "a² + b² = c²", x: 0.16, y: 0.72, size: 38, rotate: 3 },
  { text: "∫ f(x) dx = F(x) + C", x: 0.56, y: 0.68, size: 34, rotate: -4 },
  { text: "E = hν = mc²", x: 0.62, y: 0.42, size: 36, rotate: 2 },
  { text: "pV = nRT", x: 0.18, y: 0.46, size: 40, rotate: -3 },
];

function prepareFormulaCanvas(canvas: HTMLCanvasElement) {
  const rect = canvas.getBoundingClientRect();
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const width = Math.max(1, Math.floor(rect.width));
  const height = Math.max(1, Math.floor(rect.height));
  const targetWidth = Math.floor(width * dpr);
  const targetHeight = Math.floor(height * dpr);
  if (canvas.width !== targetWidth || canvas.height !== targetHeight) {
    canvas.width = targetWidth;
    canvas.height = targetHeight;
  }
  const context = canvas.getContext("2d");
  if (!context) return null;
  context.setTransform(dpr, 0, 0, dpr, 0, 0);
  context.clearRect(0, 0, width, height);
  return { context, width, height };
}

function formulaFont(size: number) {
  return `${size}px "Hannotate SC", "HanziPen SC", "Wawati SC", "STXingkai", "华文行楷", "PingFang SC", serif`;
}

function drawChalkBackground(context: CanvasRenderingContext2D, width: number, height: number, now: number) {
  context.save();
  context.globalAlpha = 0.055;
  context.strokeStyle = "rgba(244,244,240,.13)";
  context.lineWidth = 1;
  for (let index = 0; index < 7; index += 1) {
    const y = ((index * 117 + (now / 70)) % (height + 120)) - 60;
    context.beginPath();
    context.moveTo(width * 0.08, y);
    context.quadraticCurveTo(width * 0.44, y + 12, width * 0.9, y - 6);
    context.stroke();
  }
  context.globalAlpha = 0.035;
  context.fillStyle = "#f4f4f0";
  context.font = formulaFont(Math.max(16, Math.min(24, width * 0.022)));
  dynamicFormulas.forEach((formula, index) => {
    const x = width * formula.x;
    const y = height * formula.y + Math.sin(now / 2600 + index) * 4;
    context.save();
    context.translate(x, y);
    context.rotate((formula.rotate * Math.PI) / 180);
    context.fillText(formula.text, 0, 0);
    context.restore();
  });
  context.restore();
}

function drawWritingFormula(
  context: CanvasRenderingContext2D,
  width: number,
  height: number,
  now: number,
) {
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const cycleMs = reduceMotion ? 1 : 7600;
  const elapsed = reduceMotion ? 0 : now - formulaCycleStart;
  const cycleIndex = Math.floor(elapsed / cycleMs) % dynamicFormulas.length;
  const cycleTime = reduceMotion ? 3200 : elapsed % cycleMs;
  const writeMs = 3100;
  const holdMs = 1500;
  const eraseMs = 1900;
  const formula = dynamicFormulas[cycleIndex];
  const text = Array.from(formula.text);
  const size = Math.max(24, Math.min(formula.size, width * 0.05));
  const x = width * formula.x;
  const y = height * formula.y;
  const rotate = (formula.rotate * Math.PI) / 180;
  const writeProgress = reduceMotion ? 1 : Math.min(1, cycleTime / writeMs);
  const eraseProgress = reduceMotion || cycleTime < writeMs + holdMs ? 0 : Math.min(1, (cycleTime - writeMs - holdMs) / eraseMs);
  const visibleCount = eraseProgress > 0 ? text.length : Math.max(1, Math.ceil(text.length * writeProgress));

  context.save();
  context.translate(x, y);
  context.rotate(rotate);
  context.font = formulaFont(size);
  context.textBaseline = "middle";
  context.lineCap = "round";
  context.lineJoin = "round";

  let cursor = 0;
  for (let index = 0; index < visibleCount; index += 1) {
    const char = text[index];
    const jitterX = Math.sin(index * 1.7 + now / 110) * 0.35;
    const jitterY = Math.cos(index * 1.3 + now / 130) * 0.45;
    context.globalAlpha = 0.46;
    context.fillStyle = "rgba(244,244,240,.82)";
    context.fillText(char, cursor + jitterX, jitterY);
    context.globalAlpha = 0.08;
    context.fillText(char, cursor + jitterX + 1.1, jitterY + 0.8);
    cursor += context.measureText(char).width;
    if (!reduceMotion && index === visibleCount - 1 && eraseProgress === 0 && writeProgress < 1) {
      context.save();
      context.globalAlpha = 0.32;
      context.strokeStyle = "rgba(244,244,240,.58)";
      context.beginPath();
      context.moveTo(cursor + 8, -size * 0.35);
      context.lineTo(cursor + 18, size * 0.25);
      context.stroke();
      context.restore();
    }
  }

  if (eraseProgress > 0) {
    const easedEraseProgress = 1 - Math.pow(1 - eraseProgress, 3);
    const eraseWidth = (cursor + size * 1.2) * easedEraseProgress;
    context.save();
    context.globalCompositeOperation = "destination-out";
    context.fillStyle = "rgba(0,0,0,1)";
    context.fillRect(-size * 0.72, -size * 1.08, eraseWidth, size * 2.16);
    context.restore();

    context.save();
    context.globalAlpha = 0.88;
    context.fillStyle = "#121614";
    context.fillRect(-size * 0.72, -size * 1.08, eraseWidth, size * 2.16);
    context.globalAlpha = 0.24 * (1 - eraseProgress * 0.45);
    context.fillStyle = "rgba(244,244,240,.72)";
    context.fillRect(eraseWidth - size * 0.5, -size * 0.82, size * 0.34, size * 1.64);
    context.globalAlpha = 0.18 * (1 - eraseProgress);
    for (let index = 0; index < 18; index += 1) {
      const dustX = eraseWidth - size * 0.28 + Math.sin(index * 2.1) * size * 0.46;
      const dustY = -size * 0.72 + ((index * 17) % Math.max(1, size * 1.44));
      context.fillRect(dustX, dustY, 1.4, 1.4);
    }
    context.restore();
  }

  context.restore();
}

function renderFormulaCanvas(now: number) {
  const canvas = formulaCanvasRef.value;
  if (!canvas) {
    formulaFrameId = requestAnimationFrame(renderFormulaCanvas);
    return;
  }
  const prepared = prepareFormulaCanvas(canvas);
  if (!prepared) {
    formulaFrameId = requestAnimationFrame(renderFormulaCanvas);
    return;
  }
  drawChalkBackground(prepared.context, prepared.width, prepared.height, now);
  drawWritingFormula(prepared.context, prepared.width, prepared.height, now);
  formulaFrameId = requestAnimationFrame(renderFormulaCanvas);
}

function handleHeroMouseMove(event: MouseEvent) {
  const heroText = heroTextRef.value;
  const heroGlow = heroGlowRef.value;
  if (!heroText || !heroGlow) return;
  const rect = heroText.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * 100;
  heroGlow.style.clipPath = `polygon(${x - 12}% 0, ${x + 12}% 0, ${x + 12}% 100%, ${x - 12}% 100%)`;
}

function handleHeroMouseLeave() {
  if (heroGlowRef.value) {
    heroGlowRef.value.style.clipPath = "polygon(0 0, 0 0, 0 100%, 0 100%)";
  }
}

function renderScrollScene() {
  const track = trackRef.value;
  const stage = stageRef.value;
  const sceneBlackboard = sceneBlackboardRef.value;
  const sceneBook = sceneBookRef.value;
  const page1 = page1Ref.value;
  const page2 = page2Ref.value;
  const shadow1Front = shadow1FrontRef.value;
  const shadow1Back = shadow1BackRef.value;
  const shadow2Front = shadow2FrontRef.value;
  const shadow2Back = shadow2BackRef.value;

  if (!track || !stage || !sceneBlackboard || !sceneBook || !page1 || !page2 || !shadow1Front || !shadow1Back || !shadow2Front || !shadow2Back) {
    frameId = requestAnimationFrame(renderScrollScene);
    return;
  }

  const scrollableDistance = Math.max(1, track.offsetHeight - window.innerHeight);
  const virtualY = window.scrollY - track.offsetTop;
  const progress = Math.max(0, Math.min(1, virtualY > 0 ? virtualY / scrollableDistance : 0));
  const inTrack = virtualY < track.offsetHeight;

  stage.style.visibility = inTrack ? "visible" : "hidden";
  stage.style.pointerEvents = inTrack ? "auto" : "none";

  if (progress < 0.15) {
    const p = progress / 0.15;
    sceneBlackboard.style.opacity = String(1 - p);
    sceneBlackboard.style.transform = `scale(${1 + p * 0.5})`;
    sceneBlackboard.style.pointerEvents = p > 0.5 ? "none" : "auto";
  } else {
    sceneBlackboard.style.opacity = "0";
    sceneBlackboard.style.pointerEvents = "none";
  }

  if (progress >= 0.12 && progress < 0.24) {
    const p = (progress - 0.12) / 0.12;
    sceneBook.style.opacity = String(p);
    sceneBook.style.transform = `translateY(${(1 - p) * 100}px) scale(${0.9 + p * 0.1})`;
    sceneBook.style.pointerEvents = "auto";
  } else if (progress >= 0.24) {
    sceneBook.style.opacity = "1";
    sceneBook.style.transform = "translateY(0) scale(1)";
    sceneBook.style.pointerEvents = "auto";
  } else {
    sceneBook.style.opacity = "0";
    sceneBook.style.pointerEvents = "none";
  }

  if (progress <= 0.30) {
    page1.style.transform = "rotateY(0deg)";
    shadow1Front.style.background = "linear-gradient(to right, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)";
  } else if (progress <= 0.60) {
    const p = (progress - 0.30) / 0.30;
    page1.style.transform = `rotateY(${-180 * p}deg)`;
    shadow1Front.style.background = `linear-gradient(to right, rgba(0,0,0,${0.1 + p * 0.4}) 0%, rgba(0,0,0,0) ${20 + p * 30}%)`;
    shadow1Back.style.background = `linear-gradient(to left, rgba(0,0,0,${0.5 - p * 0.4}) 0%, rgba(0,0,0,0) ${50 - p * 30}%)`;
  } else {
    page1.style.transform = "rotateY(-180deg)";
    shadow1Back.style.background = "linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)";
  }

  if (progress <= 0.60) {
    page2.style.transform = "rotateY(0deg)";
    shadow2Front.style.background = "linear-gradient(to right, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)";
  } else if (progress <= 0.90) {
    const p = (progress - 0.60) / 0.30;
    page2.style.transform = `rotateY(${-180 * p}deg)`;
    shadow2Front.style.background = `linear-gradient(to right, rgba(0,0,0,${0.1 + p * 0.4}) 0%, rgba(0,0,0,0) ${20 + p * 30}%)`;
    shadow2Back.style.background = `linear-gradient(to left, rgba(0,0,0,${0.5 - p * 0.4}) 0%, rgba(0,0,0,0) ${50 - p * 30}%)`;
  } else {
    page2.style.transform = "rotateY(-180deg)";
    shadow2Back.style.background = "linear-gradient(to left, rgba(0,0,0,0.1) 0%, rgba(0,0,0,0) 20%)";
  }

  frameId = requestAnimationFrame(renderScrollScene);
}

onMounted(() => {
  document.documentElement.classList.add(homeActiveClass);
  document.body.classList.add(homeActiveClass);
  document.getElementById("app")?.classList.add(homeActiveClass);
  formulaCycleStart = performance.now();
  formulaFrameId = requestAnimationFrame(renderFormulaCanvas);
  frameId = requestAnimationFrame(renderScrollScene);
});

onBeforeUnmount(() => {
  document.documentElement.classList.remove(homeActiveClass);
  document.body.classList.remove(homeActiveClass);
  document.getElementById("app")?.classList.remove(homeActiveClass);
  if (frameId) cancelAnimationFrame(frameId);
  if (formulaFrameId) cancelAnimationFrame(formulaFrameId);
});
</script>

<style scoped>
:global(html.product-home-active),
:global(body.product-home-active),
:global(#app.product-home-active) {
  min-height: 100%;
  background: #121614 !important;
  overscroll-behavior-y: none;
}

:global(body.product-home-active) {
  overflow-x: hidden;
}

/* ====== 全局 & 字体变量 ====== */
.product-home {
  --ca-font-chalk: "Hannotate SC", "HanziPen SC", "Wawati SC", "STXingkai",
    "华文行楷", "PingFang SC", sans-serif;
  --ca-font-serif: "Songti SC", "STSong", "SimSun", "宋体", serif;
  --ca-font-sans: -apple-system, BlinkMacSystemFont, "PingFang SC",
    "Microsoft YaHei", "Helvetica Neue", sans-serif;
  --ca-font-mono: "SFMono-Regular", Consolas, "Liberation Mono", Menlo,
    monospace;
  --shared-title-left: max(24px, calc((100vw - 1040px) / 2));
  --shared-title-top: clamp(190px, calc(50vh - 190px), 290px);
  --home-logo-left: max(24px, calc((100vw - 1280px) / 2 + 24px));
  --home-logo-top: 16px;
  --logo-to-title-x: calc(var(--shared-title-left) - var(--home-logo-left));
  --logo-to-title-y: calc(var(--shared-title-top) - var(--home-logo-top));

  min-height: 100vh;
  overflow-x: hidden;
  background: #121614;
  color: #f4f4f0;
  font-family: var(--ca-font-sans);
  cursor: default;
}

/* ====== 黑板质感 ====== */
.board-texture,
.board-smudge {
  position: fixed;
  inset: 0;
  pointer-events: none;
}
.board-texture {
  z-index: 0;
  background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noiseFilter"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="3" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noiseFilter)" opacity="0.04"/%3E%3C/svg%3E');
}
.board-smudge {
  z-index: 1;
  background: radial-gradient(
      circle at 20% 30%,
      rgba(244, 244, 240, 0.03) 0%,
      transparent 40%
    ),
    radial-gradient(
      circle at 80% 70%,
      rgba(244, 244, 240, 0.02) 0%,
      transparent 35%
    );
}

/* ====== 导航 ====== */
.product-nav {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 50;
  padding: 16px 0;
  border-bottom: 1px solid rgba(244, 244, 240, 0.05);
  background: rgba(18, 22, 20, 0.8);
  backdrop-filter: blur(16px);
}
.product-nav-inner {
  max-width: 1280px;
  margin: 0 auto;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.product-logo {
  color: #f4f4f0;
  font-family: var(--ca-font-chalk);
  font-size: 20px;
  font-weight: 500;
  letter-spacing: 0;
  line-height: .9;
}
.product-logo span {
  color: #00e5ff;
}
.product-nav-links {
  display: flex;
  gap: 40px;
  color: #8c948f;
  font-size: 14px;
}
.product-nav a {
  color: inherit;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  transition: color 0.2s;
}
.product-nav a:hover {
  color: #f4f4f0;
}
.product-nav-actions {
  display: flex;
  align-items: center;
  gap: 20px;
}
.login-link {
  color: #8c948f;
  font-size: 13px;
}
.login-link:hover {
  color: #f4f4f0;
}
.register-link {
  min-height: 44px !important;
  display: inline-flex;
  align-items: center;
  background: #f4f4f0;
  color: #121614 !important;
  padding: 0 20px;
  font-size: 13px;
  font-weight: 700;
  transition: background-color 300ms, color 300ms;
}
.register-link:hover {
  background: #00e5ff;
}

/* ====== 滚动轨道 ====== */
.scroll-track {
  position: relative;
  z-index: 2;
  height: 800vh;
  background: #121614;
}
.home-stage {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 100svh;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  perspective: 1800px;
  background: #121614;
}

/* ====== 场景 1：黑板 ====== */
.scene-blackboard {
  position: absolute;
  inset: 0;
  z-index: 10;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding-top: 40px;
  transform-origin: center;
  background: #121614;
  /* 已删去导致 3D 渲染黑屏的 will-change */
}
.formula-writing-canvas {
  position: absolute;
  inset: 0;
  z-index: 1;
  width: 100%;
  height: 100%;
  opacity: .62;
  pointer-events: none;
}
.formula-corner {
  position: absolute;
  z-index: 2;
  opacity: 0.14;
  pointer-events: none;
}
.formula-corner.left {
  top: 128px;
  left: clamp(40px, 8vw, 128px);
}
.formula-corner.right {
  top: 160px;
  right: clamp(40px, 8vw, 128px);
}
.chalk-svg {
  stroke: #f4f4f0;
  stroke-width: 1.5;
  fill: none;
}
.formula-text {
  stroke: none;
  fill: #f4f4f0;
  font-family: var(--ca-font-serif);
  font-size: 18px;
  letter-spacing: 2px;
  opacity: 0;
  animation: fade-in 2s forwards 1.5s;
}
.draw-path {
  stroke-dasharray: 2000;
  stroke-dashoffset: 2000;
  animation: draw 4s cubic-bezier(0.4, 0, 0.2, 1) forwards;
}
.delay-1 {
  animation-delay: 0.5s;
}
.delay-2 {
  animation-delay: 0.8s;
}
.delay-3 {
  animation-delay: 2s;
}
.classic-quote {
  position: absolute;
  bottom: 128px;
  left: clamp(40px, 7vw, 96px);
  opacity: 0;
  color: #f4f4f0;
  font-family: var(--ca-font-chalk);
  font-size: 30px;
  line-height: 1.8;
  letter-spacing: 0.3em;
  writing-mode: vertical-rl;
  text-shadow: 0 0 2px rgba(244, 244, 240, 0.7),
    1px 1px 1px rgba(244, 244, 240, 0.4);
  animation: fade-in 3s forwards 1s;
  pointer-events: none;
}

/* ====== 英雄区 ====== */
.hero-center {
  position: relative;
  z-index: 20;
  max-width: 1024px;
  text-align: center;
  padding: 0 24px;
}
.chalk-kicker {
  margin: 0 0 48px;
  color: #f4f4f0;
  font-family: var(--ca-font-chalk);
  font-size: clamp(30px, 4vw, 40px);
  letter-spacing: 0.12em;
  text-shadow: 0 0 2px rgba(244, 244, 240, 0.7),
    1px 1px 1px rgba(244, 244, 240, 0.4);
  transform: translateX(-40px) rotate(-2deg);
  white-space: nowrap; /* 修复：防止前缀文字在小屏换行 */
}
.ai-scanner-container {
  position: relative;
  display: inline-block;
  margin-bottom: 64px;
  color: #f4f4f0;
  font-family: var(--ca-font-chalk);
  font-size: clamp(48px, 8.4vw, 104px);
  line-height: 1.08;
  letter-spacing: 0.05em;
  text-shadow: 0 0 2px rgba(244, 244, 240, 0.7),
    1px 1px 1px rgba(244, 244, 240, 0.4);
  transform: rotate(1deg);
  white-space: nowrap; /* 修复重点：阻止因为手写体较宽导致的“今天，黑板...”自动换行折断撑爆屏幕 */
}
.ai-reveal-layer {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  clip-path: polygon(0 0, 0 0, 0 100%, 0 100%);
  color: #00e5ff;
  font-family: var(--ca-font-sans);
  font-weight: 900;
  letter-spacing: 0.2em;
  text-shadow: 0 0 15px rgba(0, 229, 255, 0.8);
  white-space: nowrap;
  pointer-events: none;
  transition: clip-path 0.1s ease-out;
}
.hero-copy {
  max-width: 680px;
  margin: 0 auto 64px;
  color: #9ca3af;
  font-family: var(--ca-font-serif);
  font-size: 17px;
  font-weight: 300;
  line-height: 2;
  letter-spacing: 0.1em;
  opacity: 0;
  animation: fade-in 2s forwards 2s;
}
.hero-copy strong {
  color: #f4f4f0;
  font-weight: 700;
}
.hero-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 48px;
  opacity: 0;
  animation: fade-in 2s forwards 2.5s;
}
.hand-drawn-link,
.teacher-console-link {
  position: relative;
  min-height: 44px;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: #f4f4f0;
  font-family: var(--ca-font-serif);
  font-size: 19px;
  font-weight: 700;
  letter-spacing: 0.1em;
}
.hand-drawn-link svg:last-child {
  position: absolute;
  inset: -16px -28px;
  z-index: -1;
  width: calc(100% + 56px);
  height: calc(100% + 32px);
  fill: none;
  stroke: currentColor;
  stroke-width: 2;
  opacity: 0.6;
}
.hand-drawn-link:hover,
.teacher-console-link:hover {
  color: #00e5ff;
}
.teacher-console-link {
  color: #8c948f;
  font-size: 17px;
}
.scroll-hint {
  margin-top: 96px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 24px;
  color: #8c948f;
  font-size: 12px;
  letter-spacing: 0.5em;
  opacity: 0;
  animation: fade-in 2s forwards 3s;
}
.scroll-hint i {
  width: 1px;
  height: 64px;
  background: linear-gradient(to bottom, #8c948f, transparent);
}

/* ====== 场景 2：图书展示 ====== */
.scene-book {
  position: absolute;
  inset: 0;
  z-index: 30;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  pointer-events: none;
  transform: translateY(128px);
  perspective: 1800px;
  padding: 92px 24px 48px;
  box-sizing: border-box;
  background: #121614;
  /* 已删去导致 3D 渲染黑屏的 will-change */
}
.book {
  --book-paper: #fcfaf2;
  --book-ink: #2c2c2c;
  --book-muted: #4a4a4a;
  --book-accent: #a63d2d;

  isolation: isolate;
  position: relative;
  width: min(1100px, calc(100vw - 56px));
  height: min(720px, calc(100svh - 168px));
  min-height: 520px;
  border-radius: 4px 8px 8px 4px;
  background: var(--book-paper);
  box-shadow: 0 30px 60px -12px rgba(0, 0, 0, 0.7),
    0 18px 36px -18px rgba(0, 0, 0, 0.5), 0 5px 0 -1px #e5e0d5,
    0 5px 0 0 #d1ccc0, 0 10px 0 -2px #e5e0d5,
    0 10px 0 -1px #d1ccc0, 0 15px 20px rgba(0, 0, 0, 0.3);
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
  animation: book-float 6s ease-in-out infinite;
}
.book::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  border-radius: inherit;
  background: linear-gradient(
    90deg,
    rgba(0, 0, 0, 0) 0 49.2%,
    rgba(0, 0, 0, 0.08) 49.2% 49.8%,
    rgba(255, 255, 255, 0.35) 49.8% 50.2%,
    rgba(0, 0, 0, 0.08) 50.2% 50.8%,
    rgba(0, 0, 0, 0) 50.8% 100%
  );
  pointer-events: none;
}
.book-spine {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 50%;
  z-index: 10;
  width: 60px;
  pointer-events: none;
  transform: translateX(-50%) translateZ(4px);
  background: linear-gradient(
    to right,
    rgba(0, 0, 0, 0.12) 0%,
    rgba(0, 0, 0, 0.05) 15%,
    rgba(255, 255, 255, 0.4) 50%,
    rgba(0, 0, 0, 0.05) 85%,
    rgba(0, 0, 0, 0.12) 100%
  );
}
.paper-texture {
  position: absolute;
  inset: 0;
  z-index: 12;
  pointer-events: none;
  background-image: url('data:image/svg+xml;utf8,%3Csvg viewBox="0 0 200 200" xmlns="http://www.w3.org/2000/svg"%3E%3Cfilter id="noise"%3E%3CfeTurbulence type="fractalNoise" baseFrequency="1.5" numOctaves="2" stitchTiles="stitch"/%3E%3C/filter%3E%3Crect width="100%25" height="100%25" filter="url(%23noise)" opacity="0.03"/%3E%3C/svg%3E');
}
.book-base-left,
.book-base-right,
.book-page {
  position: absolute;
  top: 0;
  height: 100%;
}
.book-base-left,
.book-base-right {
  z-index: 1;
  width: 50%;
  overflow: hidden;
  background: var(--book-paper);
  color: var(--book-ink);
}
.book-base-left {
  left: 0;
  border-radius: 4px 0 0 4px;
  border-right: 1px solid rgba(0, 0, 0, 0.05);
  box-shadow: inset -28px 0 48px rgba(0, 0, 0, 0.07);
}
.book-base-right {
  right: 0;
  border-radius: 0 4px 4px 0;
  box-shadow: inset 28px 0 48px rgba(0, 0, 0, 0.07);
}

.book-final-left {
  position: absolute;
  inset: 0;
  padding: 80px 70px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  font-family: var(--ca-font-serif);
  color: var(--book-ink);
}
.book-icon-circle {
  width: 96px;
  height: 96px;
  display: grid;
  place-items: center;
  border: 2px solid rgba(0, 0, 0, 0.1);
  border-radius: 50%;
  margin-bottom: 48px;
  color: var(--book-ink);
  opacity: 0.42;
}
.book-icon-circle svg {
  width: 42px;
  height: 42px;
}
.book-final-left h2 {
  margin: 0 0 16px;
  color: #1a1a1a;
  font-size: 30px;
  font-weight: 700;
  letter-spacing: 0.18em;
}
.book-final-left p {
  margin: 0;
  color: #9a9a9a;
  font-family: var(--ca-font-sans);
  font-size: 12px;
  letter-spacing: 0.22em;
  text-transform: uppercase;
}

.book-final-right {
  position: absolute;
  inset: 0;
  padding: 80px 70px;
  display: flex;
  flex-direction: column;
  justify-content: center;
  font-family: var(--ca-font-serif);
  color: var(--book-ink);
}
.book-final-right .page-label {
  position: absolute;
  top: 40px;
  right: 40px;
  color: #999;
  font-family: var(--ca-font-mono);
  font-size: 12px;
}
.book-final-right h2 {
  margin: 0 0 32px;
  color: #1a1a1a;
  font-size: 42px;
  font-weight: 900;
  line-height: 1.2;
}
.book-final-right > p {
  margin: 0 0 48px;
  color: var(--book-muted);
  font-family: var(--ca-font-serif);
  font-size: 17px;
  line-height: 1.8;
  text-align: justify;
}
.book-final-right footer {
  margin-top: auto;
  border-top: 1px solid rgba(166, 61, 45, 0.18);
  padding-top: 24px;
}
.book-final-right footer p {
  margin: 0 0 16px;
  color: #777;
  font-family: var(--ca-font-sans);
  font-size: 11px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
}
.bounce-arrow {
  color: var(--book-ink);
  animation: bounce-down 1.4s infinite;
}

/* 翻页 */
.book-page {
  left: 50%;
  width: 50%;
  z-index: 3;
  border-radius: 0 8px 8px 0;
  transform-origin: left center;
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
  will-change: transform;
}
.book-page.page-two {
  z-index: 2;
}
.book-page.page-one {
  z-index: 4;
}
.page-front,
.page-back {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: var(--book-paper);
  color: var(--book-ink);
  padding: 80px 70px;
  backface-visibility: hidden;
  -webkit-backface-visibility: hidden;
  transform-style: preserve-3d;
  -webkit-transform-style: preserve-3d;
}
.page-front {
  transform: rotateY(0deg) translateZ(1px);
}
.page-back {
  transform: rotateY(180deg) translateZ(1px);
  border-radius: 4px 0 0 4px;
}
.page-no {
  position: absolute;
  bottom: 40px;
  color: #999;
  font-family: var(--ca-font-serif);
  font-size: 14px;
  font-style: italic;
}
.page-no.right {
  right: 40px;
}
.page-no.left {
  left: 40px;
}
.page-footer-number {
  position: absolute;
  bottom: 40px;
  color: #999;
  font-family: var(--ca-font-serif);
  font-size: 14px;
  font-style: italic;
}
.page-footer-number.left {
  left: 40px;
}
.page-shadow-front,
.page-shadow-back {
  position: absolute;
  inset: 0;
  z-index: 50;
  pointer-events: none;
}

.chapter-label {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  color: var(--book-accent);
  font-family: var(--ca-font-serif);
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.3em;
  text-transform: uppercase;
}
.chapter-label::after {
  content: "";
  flex: 1;
  height: 1px;
  background: rgba(166, 61, 45, 0.2);
}
.book-page h3 {
  margin: 0 0 40px;
  color: #1a1a1a;
  font-family: var(--ca-font-serif);
  font-size: clamp(34px, 3.1vw, 48px);
  font-weight: 900;
  line-height: 1.2;
}
.book-copy {
  margin: 0;
  color: var(--book-muted);
  font-family: var(--ca-font-serif);
  font-size: 18px;
  letter-spacing: 0.02em;
  line-height: 1.8;
  text-align: justify;
}
.wrong-paper {
  position: relative;
  margin-top: auto;
  border-left: 4px solid var(--book-accent);
  border-radius: 2px;
  background: #ffffff;
  padding: 30px;
  box-shadow: 2px 5px 15px rgba(0, 0, 0, 0.05);
  transform: rotate(-1deg);
}
.wrong-text {
  margin: 0;
  color: #666;
  font-family: var(--ca-font-serif);
  font-size: 18px;
  font-style: italic;
}
.wrong-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  margin-top: 24px;
  border-top: 1px dashed #e5e7eb;
  padding-top: 14px;
}
.wrong-footer span {
  color: #c8c8c8;
  font-family: var(--ca-font-sans);
  font-size: 10px;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
.wrong-x {
  color: #7f1d1d;
  font-family: var(--ca-font-sans);
  font-size: 24px;
  font-weight: 900;
  line-height: 1;
  opacity: 0.6;
}

.turn-hint {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  opacity: 0.3;
  color: var(--book-ink);
}
.turn-hint strong {
  font-family: var(--ca-font-serif);
  font-size: 20px;
  margin-top: 16px;
}

.living-book-title {
  margin-top: 0;
  border-left: 4px solid #00e5ff;
  padding-left: 18px;
}
.paper-note {
  position: relative;
  margin: auto 0 24px;
  border: 1px solid #e5e7eb;
  border-radius: 2px;
  background: #ffffff;
  box-shadow: 2px 5px 15px rgba(0, 0, 0, 0.05);
  padding: 30px;
  font-family: var(--ca-font-serif);
  font-size: 17px;
  color: var(--book-ink);
  line-height: 1.8;
  text-align: justify;
}
.formula-span {
  display: inline-block;
  margin: 8px 0;
  padding: 0 8px;
  border: 1px solid rgba(166, 61, 45, 0.1);
  background: #fcfaf2;
  font-family: var(--ca-font-mono);
  font-size: 18px;
}
.ai-sticker {
  position: absolute;
  bottom: -28px;
  left: -20px;
  width: calc(100% + 40px);
  border-radius: 4px;
  background: #0a1118;
  color: white;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1),
    0 8px 10px -6px rgba(0, 0, 0, 0.1);
  padding: 20px;
  transform: rotate(-1deg);
}
.ai-sticker div {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  color: #00e5ff;
  font-size: 12px;
  font-weight: 800;
}
.ai-sticker p {
  margin: 0;
  font-family: var(--ca-font-sans);
  font-size: 14px;
  font-weight: 300;
  line-height: 1.625;
}

.dark-page {
  background: var(--book-paper);
  color: var(--book-ink);
}
.data-network {
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.data-network h3 {
  color: #1a1a1a;
  font-family: var(--ca-font-serif);
  font-size: 34px;
  font-weight: 900;
  margin-bottom: 24px;
}
.data-network p {
  margin: 0 0 32px;
  color: var(--book-muted);
  font-family: var(--ca-font-serif);
  font-size: 17px;
  line-height: 1.8;
}
.radar-demo {
  position: relative;
  width: 100%;
  height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid rgba(166, 61, 45, 0.12);
  border-radius: 2px;
  background: #ffffff;
}
.radar-demo svg {
  width: 96px;
  height: 96px;
  opacity: 0.7;
  stroke: #00e5ff;
  fill: rgba(0, 229, 255, 0.2);
}
.radar-demo polygon:nth-child(2) {
  fill: none;
}
.radar-demo > span {
  position: absolute;
  right: 8px;
  bottom: 8px;
  color: #00e5ff;
  font-family: var(--ca-font-mono);
  font-size: 10px;
}

/* ====== 多端教室 ====== */
.roles-section {
  position: relative;
  z-index: 10;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: #181c1a;
  padding: 128px 24px;
}
.section-inner {
  max-width: 1280px;
  margin: 0 auto;
}
.roles-section header {
  margin-bottom: 96px;
  text-align: center;
}
.roles-section h2 {
  margin: 0 0 24px;
  color: #f4f4f0;
  font-family: var(--ca-font-serif);
  font-size: clamp(36px, 5vw, 48px);
  font-weight: 900;
}
.roles-section header p {
  margin: 0;
  color: #8c948f;
  font-size: 15px;
  letter-spacing: 0.1em;
}
.role-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 32px;
}
.role-card {
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 2px;
  background: #121614;
  padding: 40px;
  transition: border-color 500ms;
}
.role-card.student:hover {
  border-color: rgba(0, 229, 255, 0.5);
}
.role-card.teacher:hover {
  border-color: rgba(255, 87, 34, 0.5);
}
.role-card.admin:hover {
  border-color: rgba(217, 160, 91, 0.5);
}
.role-icon {
  width: 48px;
  height: 48px;
  display: grid;
  place-items: center;
  margin-bottom: 32px;
}
.role-card.student .role-icon {
  background: rgba(0, 229, 255, 0.1);
  color: #00e5ff;
}
.role-card.teacher .role-icon {
  background: rgba(255, 87, 34, 0.1);
  color: #ff5722;
}
.role-card.admin .role-icon {
  background: rgba(217, 160, 91, 0.1);
  color: #d9a05b;
}
.role-card h3 {
  margin: 0 0 24px;
  color: #f4f4f0;
  font-family: var(--ca-font-serif);
  font-size: 20px;
  font-weight: 700;
}
.role-card ul {
  display: grid;
  gap: 16px;
  margin: 0;
  padding: 0;
  color: #9ca3af;
  font-family: var(--ca-font-sans);
  font-size: 14px;
  line-height: 1.6;
  list-style: none;
}
.role-card li {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}
.role-card.student li svg {
  color: #00e5ff;
}
.role-card.teacher li svg {
  color: #ff5722;
}
.role-card.admin li svg {
  color: #d9a05b;
}

/* ====== 页脚 ====== */
.product-footer {
  position: relative;
  z-index: 10;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
  background: #121614;
  padding: 128px 24px;
  text-align: center;
}
.product-footer h2 {
  margin: 0 0 48px;
  color: #f4f4f0;
  font-family: var(--ca-font-serif);
  font-size: clamp(36px, 7vw, 80px);
  font-weight: 900;
  letter-spacing: -0.025em;
}
.product-footer > p {
  max-width: 680px;
  margin: 0 auto 64px;
  color: #8c948f;
  font-size: 16px;
  line-height: 1.625;
}
.product-footer > div {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 24px;
}
.trial-link,
.docs-link {
  min-height: 52px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 48px;
  border-radius: 2px;
  font-size: 15px;
  font-weight: 700;
  transition: all 300ms;
}
.trial-link {
  background: #f4f4f0;
  color: #121614;
}
.trial-link:hover {
  background: #00e5ff;
  box-shadow: 0 0 30px rgba(0, 229, 255, 0.4);
}
.docs-link {
  border: 1px solid #8c948f;
  color: #f4f4f0;
}
.docs-link:hover {
  border-color: #f4f4f0;
}

/* ====== 动画 ====== */
@keyframes draw {
  to {
    stroke-dashoffset: 0;
  }
}
@keyframes fade-in {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
@keyframes bounce-down {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(8px);
  }
}
@keyframes book-float {
  0%,
  100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

/* ====== /auth 转场：公式收向左侧，左上标题下落承接登录页 ====== */
.product-home.route-home-auth-leave-active,
.product-home.route-home-auth-leave-active .scroll-track,
.product-home.route-home-auth-leave-active .home-stage,
.product-home.route-home-auth-leave-active .scene-blackboard {
  background: transparent;
}
.product-home.route-home-auth-leave-active .formula-corner.left {
  animation: home-leave-corner-left 940ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .formula-corner.right {
  animation: home-leave-corner-right 940ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .classic-quote {
  animation: home-leave-quote 720ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .hero-center {
  animation: home-leave-hero 760ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .formula-writing-canvas {
  animation: home-leave-canvas 760ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .product-nav {
  animation: home-leave-nav-surface 620ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .product-nav-links,
.product-home.route-home-auth-leave-active .product-nav-actions {
  animation: home-leave-nav-items 520ms cubic-bezier(.55, .06, .68, .19) forwards;
}
.product-home.route-home-auth-leave-active .product-logo {
  transform-origin: left center;
  animation: home-logo-to-auth-title 940ms cubic-bezier(.22, .61, .36, 1) forwards;
}
.product-home.route-home-auth-leave-active .product-logo span {
  animation: home-logo-dot-out 220ms ease-out forwards;
}
.product-home.route-auth-home-enter-active .formula-corner.left {
  animation: home-enter-corner-left 760ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .formula-corner.right {
  animation: home-enter-corner-right 760ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .classic-quote {
  animation: home-enter-quote 760ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .hero-center {
  animation: home-enter-hero 760ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .hero-copy,
.product-home.route-auth-home-enter-active .hero-actions,
.product-home.route-auth-home-enter-active .scroll-hint {
  opacity: 1;
  animation: none;
}
.product-home.route-auth-home-enter-active .formula-writing-canvas {
  animation: home-enter-canvas 760ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .product-nav {
  animation: home-enter-nav-surface 620ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .product-nav-links,
.product-home.route-auth-home-enter-active .product-nav-actions {
  animation: home-enter-nav-items 620ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .product-logo {
  transform-origin: left center;
  animation: home-auth-title-to-logo 940ms cubic-bezier(.22, .61, .36, 1) both;
}
.product-home.route-auth-home-enter-active .product-logo span {
  animation: home-logo-dot-in 220ms ease-out 720ms both;
}

@keyframes home-leave-corner-left {
  0% { transform: translate(0, 0) rotate(0); opacity: .14; }
  60% { opacity: .12; }
  100% { transform: translate(calc(-100% - 12vw), 72px) rotate(-16deg); opacity: 0; }
}
@keyframes home-enter-corner-left {
  from { transform: translate(calc(-100% - 12vw), 72px) rotate(-16deg); opacity: 0; }
  to { transform: translate(0, 0) rotate(0); opacity: .14; }
}
@keyframes home-leave-corner-right {
  0% { transform: translate(0, 0) rotate(0); opacity: .14; }
  60% { opacity: .12; }
  100% { transform: translate(calc(-100vw - 100%), 48px) rotate(14deg); opacity: 0; }
}
@keyframes home-enter-corner-right {
  from { transform: translate(calc(-100vw - 100%), 48px) rotate(14deg); opacity: 0; }
  to { transform: translate(0, 0) rotate(0); opacity: .14; }
}
@keyframes home-leave-quote {
  to { transform: translateX(-110px); opacity: 0; }
}
@keyframes home-enter-quote {
  from { transform: translateX(-110px); opacity: 0; }
  to { transform: translateX(0); opacity: 1; }
}
@keyframes home-leave-hero {
  to { transform: translateY(-22px) scale(.94); opacity: 0; }
}
@keyframes home-enter-hero {
  from { transform: translateY(-22px) scale(.94); opacity: 0; }
  to { transform: translateY(0) scale(1); opacity: 1; }
}
@keyframes home-leave-canvas {
  to { transform: translateX(-28vw) scale(.94); opacity: .34; }
}
@keyframes home-enter-canvas {
  from { transform: translateX(-28vw) scale(.94); opacity: .34; }
  to { transform: translateX(0) scale(1); opacity: .62; }
}
@keyframes home-leave-nav-surface {
  to { border-bottom-color: transparent; background: rgba(18, 22, 20, 0); backdrop-filter: blur(0); }
}
@keyframes home-enter-nav-surface {
  from { border-bottom-color: transparent; background: rgba(18, 22, 20, 0); backdrop-filter: blur(0); }
  to { border-bottom-color: rgba(244, 244, 240, 0.05); background: rgba(18, 22, 20, 0.8); backdrop-filter: blur(16px); }
}
@keyframes home-leave-nav-items {
  to { opacity: 0; transform: translateY(-12px); }
}
@keyframes home-enter-nav-items {
  from { opacity: 0; transform: translateY(-12px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes home-logo-to-auth-title {
  0% { transform: translate(0, 0); font-size: 20px; opacity: 1; }
  78% { transform: translate(var(--logo-to-title-x), var(--logo-to-title-y)); font-size: clamp(64px, 10vw, 128px); opacity: 1; }
  100% { transform: translate(var(--logo-to-title-x), var(--logo-to-title-y)); font-size: clamp(64px, 10vw, 128px); opacity: 1; }
}
@keyframes home-auth-title-to-logo {
  0% { transform: translate(var(--logo-to-title-x), var(--logo-to-title-y)); font-size: clamp(64px, 10vw, 128px); opacity: 0; }
  84% { transform: translate(var(--logo-to-title-x), var(--logo-to-title-y)); font-size: clamp(64px, 10vw, 128px); opacity: 0; }
  100% { transform: translate(0, 0); font-size: 20px; opacity: 1; }
}
@keyframes home-logo-dot-out {
  to { opacity: 0; }
}
@keyframes home-logo-dot-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* ====== 响应式 ====== */
@media (min-width: 640px) {
  .hero-actions {
    flex-direction: row;
    gap: 48px;
  }
  .product-footer > div {
    flex-direction: row;
  }
}
@media (max-width: 900px) {
  .product-nav-links {
    display: none;
  }
  .product-nav-actions {
    gap: 10px;
  }
  .register-link {
    padding: 0 14px;
  }
  .formula-corner,
  .classic-quote {
    display: none;
  }
  .chalk-kicker {
    transform: none;
  }
  .role-grid {
    grid-template-columns: 1fr;
  }
  .book {
    width: min(920px, calc(100vw - 32px));
    height: min(640px, calc(100svh - 148px));
    min-height: 460px;
  }
  .book-spine {
    width: 48px;
  }
  .book-final-left,
  .book-final-right,
  .page-front,
  .page-back {
    padding: 48px 34px;
  }
  .book-icon-circle {
    width: 72px;
    height: 72px;
    margin-bottom: 28px;
  }
  .book-icon-circle svg {
    width: 32px;
    height: 32px;
  }
  .book-final-left h2,
  .book-final-right h2 {
    font-size: 24px;
  }
  .book-final-left p {
    font-size: 10px;
    letter-spacing: 0.14em;
  }
  .book-page h3 {
    margin-bottom: 24px;
    font-size: 26px;
  }
  .book-copy,
  .paper-note,
  .data-network p {
    font-size: 15px;
    line-height: 1.65;
  }
  .wrong-paper,
  .paper-note {
    padding: 22px;
  }
  .ai-sticker {
    position: static;
    width: 100%;
    margin-top: 18px;
    transform: none;
  }
}
@media (max-width: 640px) {
  .product-nav-inner {
    padding: 0 16px;
  }
  .login-link {
    display: none !important;
  }
  .hero-center {
    padding-top: 40px;
  }
  .ai-scanner-container {
    max-width: 100%;
    font-size: clamp(34px, 12vw, 56px);
  }
  .ai-reveal-layer {
    white-space: normal;
    letter-spacing: 0.08em;
  }
  .hero-copy {
    letter-spacing: 0.06em;
  }
  .scroll-hint {
    display: none;
  }
  .scene-book {
    padding: 82px 10px 36px;
  }
  .book {
    width: calc(100vw - 20px);
    height: min(68vh, 520px);
    min-height: 390px;
  }
  .book-spine {
    width: 34px;
  }
  .book-final-left,
  .book-final-right,
  .page-front,
  .page-back {
    padding: 28px 14px 38px;
  }
  .book-icon-circle {
    width: 48px;
    height: 48px;
    margin-bottom: 16px;
  }
  .book-icon-circle svg {
    width: 22px;
    height: 22px;
  }
  .book-final-left h2 {
    margin-bottom: 10px;
    font-size: 18px;
    letter-spacing: 0.08em;
  }
  .book-final-right h2,
  .data-network h3 {
    font-size: 20px;
  }
  .book-final-left p {
    font-size: 8px;
    letter-spacing: 0.08em;
  }
  .chapter-label {
    gap: 6px;
    margin-bottom: 14px;
    font-size: 8px;
    letter-spacing: 0.14em;
  }
  .book-page h3 {
    margin-bottom: 18px;
    font-size: 20px;
  }
  .paper-note,
  .book-copy,
  .data-network p {
    font-size: 12px;
    line-height: 1.55;
  }
  .wrong-paper,
  .paper-note {
    padding: 14px;
  }
  .wrong-text {
    font-size: 12px;
  }
  .wrong-footer {
    margin-top: 12px;
    padding-top: 10px;
  }
  .wrong-footer span {
    max-width: 80px;
    font-size: 8px;
  }
  .book-final-right > p,
  .ai-sticker p {
    font-size: 12px;
    line-height: 1.5;
  }
  .page-no,
  .page-footer-number {
    bottom: 16px;
    font-size: 10px;
  }
  .page-no.right {
    right: 16px;
  }
  .page-no.left,
  .page-footer-number.left {
    left: 16px;
  }
}
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
  .scroll-hint {
    display: none;
  }
}
</style>
