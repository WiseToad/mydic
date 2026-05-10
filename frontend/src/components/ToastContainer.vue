<template>
  <Teleport to="body">
    <div class="fixed bottom-4 right-4 z-50 flex flex-col gap-2 w-80 pointer-events-none">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toastStore.toasts"
          :key="toast.id"
          :class="[
            'flex items-start gap-3 rounded-xl px-4 py-3 shadow-2xl text-sm pointer-events-auto cursor-pointer select-none border',
            toast.type === 'error'   ? 'bg-red-950 border-red-800 text-red-200' :
            toast.type === 'success' ? 'bg-emerald-950 border-emerald-800 text-emerald-200' :
                                       'bg-surface-800 border-surface-600 text-gray-200',
          ]"
          @click="toastStore.dismiss(toast.id)"
        >
          <!-- Icon -->
          <svg v-if="toast.type === 'error'" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
          </svg>
          <svg v-else-if="toast.type === 'success'" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 mt-0.5 shrink-0" viewBox="0 0 24 24" fill="currentColor">
            <path d="M9 16.2L4.8 12l-1.4 1.4L9 19 21 7l-1.4-1.4L9 16.2z"/>
          </svg>

          <span class="flex-1 leading-snug">{{ toast.message }}</span>

          <!-- Dismiss -->
          <span class="opacity-40 hover:opacity-100 text-lg leading-none mt-0.5">×</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { useToastStore } from '@/stores/toast'

const toastStore = useToastStore()
</script>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.25s ease;
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(2rem);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(2rem);
}
</style>
