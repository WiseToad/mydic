import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { languagesApi } from '@/api/languages'
import type { LanguageItem } from '@/types'
import { extractErrorMessage } from '@/utils/error'
import { useToastStore } from '@/stores/toast'

// Re-exported for component consumers (SettingsView LangList prop type)
export type LangPref = LanguageItem

export const useLanguageSettingsStore = defineStore('languageSettings', () => {
  const languages = ref<LanguageItem[]>([])
  const isLoaded = ref(false)
  const isSaving = ref(false)

  /** All enabled languages in saved order – drives the translator selectors. */
  const enabledLangs = computed(() =>
    [...languages.value].sort((a, b) => a.position - b.position).filter(l => l.enabled)
  )

  async function load() {
    if (isLoaded.value) return
    try {
      languages.value = await languagesApi.getLanguages()
      isLoaded.value = true
    } catch (e: unknown) {
      useToastStore().error(extractErrorMessage(e, 'Failed to load language preferences'))
    }
  }

  async function _save() {
    isSaving.value = true
    try {
      languages.value = await languagesApi.saveLanguages(languages.value)
    } catch (e: unknown) {
      useToastStore().error(extractErrorMessage(e, 'Failed to save language preferences'))
    } finally {
      isSaving.value = false
    }
  }

  function toggleEnabled(index: number) {
    const list = [...languages.value]
    list[index] = { ...list[index], enabled: !list[index].enabled }
    languages.value = list
    _save()
  }

  function reorder(from: number, to: number) {
    const list = [...languages.value]
    const [item] = list.splice(from, 1)
    list.splice(to, 0, item)
    list.forEach((l, i) => { l.position = i })
    languages.value = list
    _save()
  }

  function reset() {
    languages.value = []
    isLoaded.value = false
  }

  return { languages, isLoaded, isSaving, enabledLangs, load, toggleEnabled, reorder, reset }
})
