import { createRouter, createMemoryHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

// The route name the user was on before opening Settings. Used by SettingsView
// to return to the correct view on dismiss, since createMemoryHistory does not
// reliably expose history.state.back.
export let previousSettingsRoute: string | null = null

const router = createRouter({
  history: createMemoryHistory(),
  routes: [
    { path: '/', redirect: '/translator' },
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/translator',
      name: 'translator',
      component: () => import('@/views/TranslatorView.vue'),
    },
    {
      path: '/wordbook',
      name: 'wordbook',
      component: () => import('@/views/WordbookView.vue'),
    },
    {
      path: '/settings',
      name: 'settings',
      component: () => import('@/views/SettingsView.vue'),
    },
  ],
})

router.beforeEach((to, from) => {
  if (to.name === 'settings' && from.name != null && from.name !== 'settings') {
    previousSettingsRoute = from.name as string
  }
  const authStore = useAuthStore()
  if (!to.meta.public && !authStore.isLoggedIn) {
    return { name: 'login' }
  }
  if (to.name === 'login' && authStore.isLoggedIn) {
    return { name: 'translator' }
  }
})

export default router
