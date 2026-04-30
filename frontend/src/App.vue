<template>
  <RouterView v-slot="{ Component }">
    <component
      :is="Component"
      v-if="ready"
      :user="session.user"
      @authed="onAuthed"
      @logout="logout"
      @notice="session.pushToast"
    />
  </RouterView>
  <ToastHost :items="session.toasts" @close="session.closeToast" />
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import ToastHost from "./components/ToastHost.vue";
import { defaultRouteForRole } from "./router";
import { useSessionStore } from "./stores/session";
import type { User } from "./types";

const router = useRouter();
const session = useSessionStore();
const ready = computed(() => session.initialized);

async function onAuthed(user: User) {
  session.setUser(user);
  await router.replace(defaultRouteForRole(user.role));
}
async function logout() {
  session.logout();
  await router.replace("/auth");
}
onMounted(() => session.bootstrap());
</script>
