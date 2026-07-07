<template>
  <PageLoader v-if="!ready" />
  <template v-else>
    <RouterView v-slot="{ Component, route }">
      <Transition :name="transitionName" :mode="transitionMode">
        <!-- 鉴权路由必须等 session.user 就绪再挂载：token 失效时 store 会先把 user 置空再异步跳登录页，
             这个空窗期若仍渲染角色视图会命中 user.nickname 之类的空指针崩溃 -->
        <component
          v-if="!route.meta.requiresAuth || session.user"
          :is="Component"
          :key="String(route.meta.shellKey || route.path)"
          :user="session.user"
          @authed="onAuthed"
          @logout="logout"
          @notice="session.pushToast"
        />
        <PageLoader v-else />
      </Transition>
    </RouterView>
    <ToastHost :items="session.toasts" @close="session.closeToast" />
  </template>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import PageLoader from "./components/PageLoader.vue";
import ToastHost from "./components/ToastHost.vue";
import { useSessionStore } from "./stores/session";
import { applyAppTheme, readStoredTheme, subscribeAppTheme, type AppTheme } from "./theme";
import type { User } from "./types";

const router = useRouter();
const session = useSessionStore();
const ready = computed(() => session.initialized);
const transitionName = ref("route-none");
const transitionMode = computed(() => (transitionName.value === "route-page" ? "out-in" : undefined));
const appTheme = ref<AppTheme>(readStoredTheme());
let unsubscribeTheme: (() => void) | null = null;

applyAppTheme(appTheme.value);

router.beforeEach((to, from) => {
  if (!from.matched.length) transitionName.value = "route-none";
  else if (from.path === "/" && to.path === "/auth") transitionName.value = "route-home-auth";
  else if (from.path === "/auth" && to.path === "/") transitionName.value = "route-auth-home";
  else transitionName.value = "route-page";
  return true;
});

async function onAuthed(user: User) {
  session.setUser(user);
}
async function logout() {
  session.logout();
  await router.replace("/auth");
}

onMounted(() => {
  applyAppTheme(appTheme.value);
  unsubscribeTheme = subscribeAppTheme((theme) => {
    appTheme.value = theme;
    applyAppTheme(theme);
  });
  session.bootstrap();
});

onBeforeUnmount(() => {
  unsubscribeTheme?.();
});
</script>
