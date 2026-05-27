<template>
  <Transition name="fade">
    <div
      v-if="modelValue"
      class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
      @click.self="close"
    >
      <Transition name="scale">
        <div
          v-if="modelValue"
          class="bg-surface-800 border border-surface-700 rounded-2xl shadow-2xl max-w-xs w-full p-6"
        >
          <h3 class="text-lg font-semibold text-gray-100 mb-4">About MyDic</h3>

          <dl class="space-y-2 mb-6">
            <div class="flex justify-between text-sm">
              <dt class="text-gray-400">Version</dt>
              <dd class="text-gray-200 font-mono">{{ version }}</dd>
            </div>
          </dl>

          <div
            v-if="updateAvailable"
            class="mb-4 p-3 bg-primary-950 border border-primary-700 rounded-xl text-sm"
          >
            <p class="text-primary-300 mb-3">
              A new version is available ({{ serverVersion }}).
            </p>
            <button
              class="w-full px-4 py-2 rounded-lg text-sm font-medium bg-primary-600 hover:bg-primary-500 text-white transition-colors"
              @click="reload"
            >
              Reload to update
            </button>
          </div>

          <div class="flex justify-end">
            <button
              class="px-4 py-2 rounded-lg text-sm font-medium text-gray-400 hover:text-gray-100 hover:bg-surface-700 transition-colors"
              @click="close"
            >
              Close
            </button>
          </div>
        </div>
      </Transition>
    </div>
  </Transition>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { version } from 'virtual:app-version'
import { fetchServerVersion } from '@/api/version'

const props = defineProps<{ modelValue: boolean }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: boolean): void }>()

const serverVersion = ref<string | null>(null)
const updateAvailable = ref(false)

watch(
  () => props.modelValue,
  async (open) => {
    if (!open) return
    try {
      const sv = await fetchServerVersion()
      serverVersion.value = sv
      updateAvailable.value = sv !== version
    } catch {
      // silently ignore — version check is best-effort
    }
  },
)

function close() {
  emit('update:modelValue', false)
}

function reload() {
  window.location.reload()
}
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.scale-enter-active,
.scale-leave-active {
  transition: all 0.2s ease;
}
.scale-enter-from,
.scale-leave-to {
  opacity: 0;
  transform: scale(0.95);
}
</style>
