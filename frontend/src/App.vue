<template>
  <div class="min-h-screen flex flex-col">
    <!-- Navigation -->
    <header v-if="authStore.isLoggedIn" class="sticky top-0 z-40 bg-surface-900/80 backdrop-blur-md border-b border-surface-700 px-6 py-3 flex items-center gap-6">
      <span class="font-bold text-primary-400 text-lg tracking-tight">MyDic</span>
      <nav class="flex gap-4 flex-1">
        <RouterLink
          to="/translator"
          class="text-sm font-medium text-gray-400 hover:text-gray-100 transition-colors"
          active-class="!text-primary-400 border-b-2 border-primary-400 pb-0.5"
        >
          Translator
        </RouterLink>
        <RouterLink
          to="/wordbook"
          class="text-sm font-medium text-gray-400 hover:text-gray-100 transition-colors"
          active-class="!text-primary-400 border-b-2 border-primary-400 pb-0.5"
        >
          Wordbook
        </RouterLink>
      </nav>
      <!-- Username with sign-out dropdown -->
      <div class="relative" ref="menuRef">
        <button
          class="flex items-center gap-1.5 text-sm font-medium text-gray-400 hover:text-gray-100 transition-colors"
          @click="menuOpen = !menuOpen"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 12c2.7 0 4.8-2.1 4.8-4.8S14.7 2.4 12 2.4 7.2 4.5 7.2 7.2 9.3 12 12 12zm0 2.4c-3.2 0-9.6 1.6-9.6 4.8v2.4h19.2v-2.4c0-3.2-6.4-4.8-9.6-4.8z"/>
          </svg>
          {{ authStore.user?.username ?? 'Account' }}
          <svg :class="['w-3 h-3 transition-transform', menuOpen ? 'rotate-180' : '']" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor">
            <path d="M7 10l5 5 5-5H7z"/>
          </svg>
        </button>

        <div
          v-if="menuOpen"
          class="absolute right-0 mt-1 w-36 bg-surface-800 border border-surface-700 rounded-xl shadow-2xl py-1 z-50"
        >
          <RouterLink
            to="/settings"
            class="block w-full text-left px-4 py-2 text-sm text-gray-300 hover:bg-surface-700 transition-colors"
            @click="menuOpen = false"
          >
            Settings
          </RouterLink>
          <button
            class="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors"
            @click="authStore.logout"
          >
            Sign out
          </button>
        </div>
      </div>
    </header>

    <main class="flex-1 px-4 py-8">
      <!-- KeepAlive preserves component state (translation, open panels, etc.)
           when the user switches between Translator and Wordbook tabs.
           LoginView is deliberately excluded — form state should reset. -->
      <RouterView v-slot="{ Component }">
        <KeepAlive :include="['TranslatorView', 'WordbookView']">
          <component :is="Component" />
        </KeepAlive>
      </RouterView>
    </main>

    <!-- Global toast notifications (slides in from bottom-right) -->
    <ToastContainer />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useSettingsStore } from '@/stores/settings'
import { useLanguageSettingsStore } from '@/stores/languageSettings'
import { useTranslatorStore } from '@/stores/translator'
import { useWordbookStore } from '@/stores/wordbook'
import { useWordbookGroupsStore } from '@/stores/wordbookGroups'
import { useWordbookUiStore } from '@/stores/wordbookUi'
import ToastContainer from '@/components/ToastContainer.vue'

const authStore = useAuthStore()
const settingsStore = useSettingsStore()
const languageSettingsStore = useLanguageSettingsStore()
const translatorStore = useTranslatorStore()
const wordbookStore = useWordbookStore()
const wordbookGroupsStore = useWordbookGroupsStore()
const wordbookUiStore = useWordbookUiStore()
const menuOpen = ref(false)
const menuRef = ref<HTMLElement | null>(null)

/** userId captured at page-load time, before any authentication changes.
 *  Used to detect whether stores were already seeded for the resuming user. */
const _initialUserId = (() => {
  const raw = localStorage.getItem('mydicUserId')
  if (!raw) return null
  const n = Number(raw)
  return isNaN(n) ? null : n
})()

// Close dropdown when clicking outside
function onClickOutside(e: MouseEvent) {
  if (menuRef.value && !menuRef.value.contains(e.target as Node)) {
    menuOpen.value = false
  }
}

// Re-initialise all stores when a (different) user logs in.
// When the same user's session resumes on page load, stores already read the
// correct namespaced keys at startup via mydicUserId — skip reinit in that case.
watch(() => authStore.user?.id, (newId, oldId) => {
  if (newId == null) return
  if (oldId === undefined && newId === _initialUserId) return
  settingsStore.reinitialize(newId)
  translatorStore.reinitialize(newId)
  wordbookUiStore.reinitialize(newId)
  languageSettingsStore.reset()
  wordbookStore.reset()
  wordbookGroupsStore.reset()
  settingsStore.load()
  languageSettingsStore.load()
})

onMounted(() => {
  authStore.fetchAppConfig()
  if (authStore.isLoggedIn) {
    authStore.fetchMe()
    settingsStore.load()
    languageSettingsStore.load()
  }
  document.addEventListener('click', onClickOutside)
})
onUnmounted(() => document.removeEventListener('click', onClickOutside))
</script>
