<template>
  <RouterView v-slot="{ Component, route }">
    <Transition :name="transitionName" :mode="transitionMode">
      <component
        :is="Component"
        v-if="ready"
        :key="String(route.meta.shellKey || route.path)"
        :user="session.user"
        @authed="onAuthed"
        @logout="logout"
        @notice="session.pushToast"
      />
    </Transition>
  </RouterView>
  <ToastHost :items="session.toasts" @close="session.closeToast" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import ToastHost from "./components/ToastHost.vue";
import { useSessionStore } from "./stores/session";
import type { User } from "./types";

const router = useRouter();
const session = useSessionStore();
const ready = computed(() => session.initialized);
const transitionName = ref("route-none");
const transitionMode = computed(() => (transitionName.value === "route-page" ? "out-in" : undefined));

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
onMounted(() => session.bootstrap());
</script>
