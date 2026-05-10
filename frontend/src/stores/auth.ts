import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api/auth'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem('mydicToken'))
  const user = ref<User | null>(null)
  const registrationEnabled = ref(true)

  const isLoggedIn = computed(() => token.value !== null)

  async function login(username: string, password: string) {
    const data = await authApi.login(username, password)
    token.value = data.access_token
    localStorage.setItem('mydicToken', data.access_token)
    const me = await authApi.me()
    localStorage.setItem('mydicUserId', String(me.id))
    user.value = me
  }

  async function register(username: string, password: string) {
    await authApi.register(username, password)
    await login(username, password)
  }

  async function fetchAppConfig() {
    try {
      const cfg = await authApi.getAppConfig()
      registrationEnabled.value = cfg.registration_enabled
    } catch {
      // keep the default (true) on network error
    }
  }

  async function fetchMe() {
    if (token.value) {
      try {
        const me = await authApi.me()
        localStorage.setItem('mydicUserId', String(me.id))
        user.value = me
      } catch {
        logout()
      }
    }
  }

  function logout() {
    token.value = null
    user.value = null
    localStorage.removeItem('mydicToken')
    localStorage.removeItem('mydicUserId')
    // Router is not available as a dependency here; redirect via window
    window.location.href = '/login'
  }

  return { token, user, isLoggedIn, registrationEnabled, login, register, fetchAppConfig, fetchMe, logout }
})
