<template>
  <div class="flex min-h-[70vh] items-center justify-center">
    <div class="w-full max-w-sm card p-8 shadow-2xl">
      <div class="text-center mb-8">
        <span class="text-2xl font-bold text-primary-400 tracking-tight">MyDic</span>
        <p class="text-xs text-gray-500 mt-1">Your personal language companion</p>
      </div>

      <!-- Tab switcher (hidden when registration is disabled) -->
      <div v-if="authStore.registrationEnabled" class="flex rounded-xl bg-surface-800 p-1 mb-6">
        <button
          v-for="tab in ['login', 'register']" :key="tab"
          :class="['flex-1 py-1.5 text-sm font-medium rounded-lg transition-all capitalize',
            mode === tab
              ? 'bg-primary-600 text-white shadow'
              : 'text-gray-400 hover:text-gray-200']"
          @click="mode = tab as 'login' | 'register'"
        >
          {{ tab }}
        </button>
      </div>

      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Username</label>
          <input v-model="username" type="text" autocomplete="username" required class="input" />
        </div>
        <div>
          <label class="block text-xs font-medium text-gray-400 uppercase tracking-wide mb-1.5">Password</label>
          <input v-model="password" type="password" autocomplete="current-password" required class="input" />
        </div>

        <p v-if="error" class="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{{ error }}</p>

        <button type="submit" :disabled="isLoading" class="btn-primary w-full py-2.5">
          {{ isLoading ? '…' : mode === 'login' ? 'Sign in' : 'Create account' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

// If registration gets disabled after initial render, snap back to login mode
watch(() => authStore.registrationEnabled, (enabled) => {
  if (!enabled) mode.value = 'login'
})

const mode = ref<'login' | 'register'>('login')
const username = ref('')
const password = ref('')
const isLoading = ref(false)
const error = ref('')

async function submit() {
  error.value = ''
  isLoading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(username.value, password.value)
    } else {
      await authStore.register(username.value, password.value)
    }
    router.push('/translator')
  } catch (e: unknown) {
    const msg = (e as { response?: { data?: { detail?: string } } }).response?.data?.detail
    error.value = msg ?? 'Something went wrong'
  } finally {
    isLoading.value = false
  }
}
</script>
