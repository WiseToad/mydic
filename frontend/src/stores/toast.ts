import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastType = 'error' | 'success' | 'info' | 'warn'

export interface Toast {
  id: number
  message: string
  type: ToastType
  action?: () => void
  actionLabel?: string
}

let _nextId = 0

export const useToastStore = defineStore('toast', () => {
  const toasts = ref<Toast[]>([])

  function show(
    message: string,
    type: ToastType = 'error',
    duration = 5000,
    action?: () => void,
    actionLabel?: string,
  ) {
    const id = ++_nextId
    toasts.value.push({ id, message, type, action, actionLabel })
    setTimeout(() => dismiss(id), duration)
  }

  function error(message: string) {
    show(message, 'error')
  }

  function success(message: string) {
    show(message, 'success', 3000)
  }

  function warn(message: string) {
    show(message, 'warn', 5000)
  }

  function undo(message: string, action: () => void) {
    show(message, 'success', 5000, action, 'Undo')
  }

  function dismiss(id: number) {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  return { toasts, show, error, success, warn, undo, dismiss }
})
