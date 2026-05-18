<template>
  <div ref="containerRef">
    <!-- Header: label + (provider selector & translations toggle).
         Hidden in inline mode — TranslatorView renders the header. -->
    <div v-if="!inline" class="flex items-center mb-3">
      <h3 class="text-xs font-semibold uppercase tracking-widest text-gray-500">Context examples</h3>
      <!-- Right cluster: provider selector + show/hide-translations toggle.
           Wrapping both in one `ml-auto` flex container keeps them tightly
           grouped and avoids per-branch ml-auto bookkeeping when either is
           conditionally absent. -->
      <div class="ml-auto flex items-center gap-2">
        <!-- Translator (non-compact) only: show/hide-translations icon button.
             Visually mirrors the wordbook view's global show/hide-translations
             control so the affordance is consistent across the two views.
             Compact mode (wordbook entry details panel) keeps the original
             text-label toggle rendered below the header instead. Only shown
             once results are in and at least one example carries a target
             (monolingual providers → nothing to toggle). -->
        <button
          v-if="!compact && showToggle && state === 'done' && examples.some(e => !!e.target)"
          class="p-1 transition-colors rounded-lg border border-surface-700"
          :class="anyVisible() ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
          :title="anyVisible() ? 'Hide translations' : 'Show translations'"
          @click="toggleAllVisible"
        >
          <svg v-if="anyVisible()" viewBox="0 0 16 16" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8s-2.5 4.5-6.5 4.5S1.5 8 1.5 8z"/>
            <circle cx="8" cy="8" r="2"/>
          </svg>
          <svg v-else viewBox="0 0 16 16" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 2l12 12M6.5 6.6a2 2 0 0 0 2.9 2.9M3.3 5.2C2.2 6.3 1.5 8 1.5 8s2.5 4.5 6.5 4.5c1 0 1.9-.3 2.7-.7M13.1 10.4c.9-1 1.4-2.4 1.4-2.4s-2.5-4.5-6.5-4.5c-.5 0-1 .1-1.4.2"/>
          </svg>
        </button>
        <!-- Compact: abbrev clickable → popup (wordbook details) -->
        <template v-if="compact && providers.length > 0 && (visibleProviders.length > 0 || historicalProviderCode)">
          <div class="relative" ref="popupAnchorRef">
            <button
              class="text-xs font-mono text-gray-500 hover:text-gray-300 transition-colors px-1"
              :title="currentProviderName ?? 'Select provider'"
              @click.stop="showPopup = !showPopup"
            >{{ currentProviderLabel }}</button>
            <div
              v-if="showPopup"
              ref="popupRef"
              class="absolute top-full right-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col"
              @click.stop
            >
              <!-- Provider removed from registry (not in list at all) -->
              <button
                v-if="historicalProviderCode && !providers.some(p => p.code === historicalProviderCode)"
                disabled
                title="Provider no longer available"
                class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-gray-600 cursor-not-allowed"
              >🛇 {{ historicalProviderDisplayAbbrev ?? historicalProviderCode }}</button>
              <button
                v-for="p in visibleProviders"
                :key="p.code"
                :disabled="!p.enabled || !p.available"
                :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
                class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors"
                :class="p.code === selectedProviderCode && (!p.enabled || !p.available)
                  ? 'text-gray-400 cursor-not-allowed'
                  : (!p.enabled || !p.available)
                    ? 'text-gray-600 cursor-not-allowed'
                    : p.code === selectedProviderCode
                      ? 'text-primary-400 bg-primary-500/10'
                      : 'text-gray-300 hover:bg-surface-800'"
                @click="selectProvider(p.code)"
              >{{ !p.enabled ? `🛇 ${p.name}` : (!p.available ? `⚠ ${p.name}` : p.name) }}</button>
            </div>
          </div>
        </template>
        <!-- Non-compact: select with full names (translator page) -->
        <select
          v-else-if="!compact && providers.length > 0 && (visibleProviders.length > 0 || historicalProviderCode)"
          v-model="providerSelectValue"
          class="bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500/50 transition-colors"
        >
          <!-- Provider removed from registry (not in list at all) -->
          <option
            v-if="historicalProviderCode && !providers.some(p => p.code === historicalProviderCode)"
            :value="historicalProviderCode"
            disabled
            title="Provider no longer available"
          >🛇 {{ historicalProviderDisplayName }}</option>
          <option
            v-for="p in visibleProviders"
            :key="p.code"
            :value="p.code"
            :disabled="!p.enabled || !p.available"
            :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
          >{{ !p.enabled ? `🛇 ${p.name}` : (!p.available ? `⚠ ${p.name}` : p.name) }}</option>
        </select>
      </div>
    </div>

    <!-- In inline mode the provider selector is external; hide these messages when
         the parent has no usable provider (inlineBlocked). -->
    <template v-if="!inlineBlocked">

    <!-- No visible providers (non-inline mode only) -->
    <p v-if="!inline && providersLoaded && visibleProviders.length === 0 && state === 'loading'" class="text-sm text-gray-500 italic">No providers available.</p>

    <!-- Provider blocked (non-inline mode only) -->
    <p v-else-if="!inline && fetchBlocked && state === 'loading'" class="text-sm text-gray-500 italic">Provider unavailable.</p>

    <!-- Loading -->
    <p v-else-if="state === 'loading'" class="text-sm text-gray-500">Loading…</p>

    <!-- Error -->
    <div v-else-if="state === 'error'" class="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">
      {{ errorMsg }}
    </div>

    <!-- No results -->
    <p v-else-if="state === 'done' && !examples.length" class="text-sm text-gray-500 italic">
      No examples found.
    </p>

    <!-- Results -->
    <template v-else-if="state === 'done' && examples.length">
      <!-- Compact (wordbook entry details): text-label toggle. -->
      <div v-if="compact && showToggle && examples.some(e => !!e.target)" class="flex justify-end mb-2">
        <button
          class="text-xs text-gray-500 hover:text-primary-400 transition-colors"
          @click="toggleAllVisible"
        >
          {{ anyVisible() ? 'Hide translations' : 'Show translations' }}
        </button>
      </div>

      <div v-for="(ex, i) in examples" :key="i" class="mb-3">
        <!-- Source sentence + audio -->
        <div class="flex items-center gap-1">
          <p class="text-sm flex-1 leading-snug">
            <span
              :class="(showToggle && !!ex.target) ? 'cursor-pointer hover:text-primary-400' : 'cursor-default'"
              class="text-gray-200 transition-colors"
              @click="showToggle && !!ex.target && toggleExample(i)"
            >{{ ex.source }}</span>
          </p>
          <AudioButton :text="ex.source" :lang="sourceLang" size="sm" class="shrink-0" />
        </div>

        <!-- Translation (hidden by default; omitted for monolingual providers with no target) -->
        <div v-if="ex.target && (allVisible || revealed.has(i))" class="mt-0.5 flex items-center gap-1">
          <p class="text-sm text-gray-500 leading-snug flex-1">{{ ex.target }}</p>
          <AudioButton v-if="targetLang" :text="ex.target" :lang="targetLang" size="sm" class="shrink-0" />
        </div>
      </div>
    </template>

    </template><!-- /!inlineBlocked -->
  </div>

  <Teleport to="body">
    <button
      v-if="buttonVisible"
      :style="{ left: buttonLeft + 'px', top: buttonTop + 'px' }"
      class="fixed z-50 flex items-center justify-center p-1.5 bg-surface-900 border border-surface-700 rounded-lg text-primary-400 hover:text-primary-300 hover:bg-surface-800 shadow-lg transition-colors"
      @pointerdown.prevent
      @click="onSelectionTranslate"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0 0 14.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
      </svg>
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { dictionaryApi } from '@/api/dictionary'
import AudioButton from './AudioButton.vue'
import { extractErrorMessage } from '@/utils/error'
import { useTranslatorStore } from '@/stores/translator'
import { useSettingsStore } from '@/stores/settings'
import { useTextSelectionButton } from '@/composables/useTextSelectionButton'
import type { ContextExample, ProviderItem } from '@/types'

const props = withDefaults(defineProps<{
  text: string
  sourceLang: string
  targetLang: string
  compact?: boolean
  showAllByDefault?: boolean
  showToggle?: boolean
  // When true: TranslatorView owns the provider selector.  The panel hides its
  // own header and trusts the validated code fed via initialProviderCode directly
  // (same pattern as LexicalPanel inline mode).
  inline?: boolean
  // Pass saved examples from history to restore state on back/forward.
  // undefined = never fetched (auto-fetch); array (possibly empty) = already fetched.
  initialExamples?: ContextExample[]
  // Provider code last used for this entry; re-validated against the available list.
  initialProviderCode?: string | null
}>(), { compact: false, showAllByDefault: false, showToggle: true, inline: false, initialExamples: undefined, initialProviderCode: undefined })

const settingsStore = useSettingsStore()

// All providers (enabled + excluded) sorted by position.
const providers = ref<ProviderItem[]>([])
const providersLoaded = ref(false)

// Set when initialProviderCode is not found in the providers list at all.
const historicalProviderCode = ref<string | null>(null)

const historicalProviderDisplayName = computed<string | null>(() => {
  const code = historicalProviderCode.value
  if (!code) return null
  return providers.value.find(p => p.code === code)?.name ?? code
})
const historicalProviderDisplayAbbrev = computed<string | null>(() => {
  const code = historicalProviderCode.value
  if (!code) return null
  return providers.value.find(p => p.code === code)?.abbrev ?? null
})

async function loadProviders() {
  // Inline mode: TranslatorView owns the provider list; skip our own fetch.
  if (props.inline) { providersLoaded.value = true; return }
  providersLoaded.value = false
  try {
    const raw = await dictionaryApi.contextProviders(props.sourceLang, props.targetLang)
    providers.value = [...raw].sort((a, b) => a.position - b.position)
    providersLoaded.value = true
  } catch {
    // Non-critical; keep the existing list if the request fails.
    // Must mark as loaded so fetchExamples() is not blocked indefinitely.
    providersLoaded.value = true
  }
}

watch(() => [props.sourceLang, props.targetLang], loadProviders, { immediate: true })
watch(() => settingsStore.saveCount, loadProviders)

const selectedProviderCode = ref<string | null>(null)

// Providers rendered in the selector: all enabled ones (available or not) +
// the disabled/unavailable one that was saved as "used before" for this entry.
const visibleProviders = computed(() =>
  providers.value.filter(p => p.enabled || p.code === selectedProviderCode.value)
)

const selectedProvider = computed(() =>
  providers.value.find(p => p.code === selectedProviderCode.value) ?? null
)

const currentProviderName = computed(() => selectedProvider.value?.name ?? null)

/** True when we have a selection but can't/shouldn't fetch. */
const fetchBlocked = computed(() => {
  if (!providersLoaded.value) return false
  if (historicalProviderCode.value) return true
  if (!selectedProviderCode.value) return true
  const sp = selectedProvider.value
  return !sp || !sp.enabled || !sp.available
})

const currentProviderLabel = computed(() => {
  if (historicalProviderCode.value) {
    return `🛇 ${historicalProviderDisplayAbbrev.value ?? historicalProviderCode.value}`
  }
  const p = selectedProvider.value
  if (!p) return '…'
  if (!p.enabled) return `🛇 ${p.abbrev || p.code}`
  if (!p.available) return `⚠ ${p.abbrev || p.code}`
  return p.abbrev || p.code
})

// For the non-compact <select>
const providerSelectValue = computed({
  get: () => historicalProviderCode.value ?? selectedProviderCode.value ?? '',
  set: (v: string) => { selectProvider(v || null) },
})

// Compact popup state
const showPopup = ref(false)
const popupRef = ref<HTMLElement | null>(null)

function closePopup() { showPopup.value = false }
watch(showPopup, (open) => {
  if (open) document.addEventListener('click', closePopup)
  else document.removeEventListener('click', closePopup)
})
onBeforeUnmount(() => document.removeEventListener('click', closePopup))

function selectProvider(code: string | null) {
  showPopup.value = false
  if (code === selectedProviderCode.value && !historicalProviderCode.value) return
  _userSelectedProvider = true
  historicalProviderCode.value = null
  selectedProviderCode.value = code
  fetchExamples()
}

// True when inline mode is active and the parent passes null (no usable provider).
const inlineBlocked = ref(false)

let _providersReady = false
let _userSelectedProvider = false

watch(providers, (newProviders) => {
  if (props.inline) return  // provider management is external in inline mode
  const hasPreserved = props.initialProviderCode != null && !_userSelectedProvider

  if (newProviders.length === 0) {
    if (!_providersReady) {
      selectedProviderCode.value = props.initialProviderCode ?? null
    }
    if (providersLoaded.value) {
      // Loaded list is empty (no providers for this lang pair, or all excluded):
      // nothing to select. Historical mode is reserved for in-list-but-unusable
      // codes only — a code that isn't in the list at all is treated as if no
      // code was preserved.
      selectedProviderCode.value = null
      historicalProviderCode.value = null
    }
    return
  }

  // The saved code is honoured if it is still physically present in the
  // provider list. A code that's gone from the registry (provider removed or
  // not applicable to this lang pair) is shown as a ghost — blocking fetch
  // but preserving the entry's saved selection visually, mirroring translation/lex.
  const existing = hasPreserved
    ? newProviders.find(p => p.code === props.initialProviderCode)
    : undefined

  if (!_providersReady) {
    _providersReady = true
    if (existing) {
      selectedProviderCode.value = existing.code
      historicalProviderCode.value = null
      const providerValid = !!(existing.enabled && existing.available)
      if (providerValid && props.initialExamples !== undefined) {
        // Valid provider + cached data: restore content immediately, no fetch needed.
        state.value = 'done'
        examples.value = props.initialExamples
        allVisible.value = props.showAllByDefault
      } else if (providerValid) {
        fetchExamples()  // valid provider, no cached data
      }
      // else: provider blocked — state stays 'loading', fetchBlocked shows the message.
    } else if (hasPreserved) {
      // Saved code is not in the provider registry (removed or not applicable
      // to this lang pair): ghost it so the entry's saved selection is visible.
      historicalProviderCode.value = props.initialProviderCode!
      selectedProviderCode.value = null
      // fetchBlocked is true → "Provider unavailable." is shown, no fetch.
    } else {
      // No preserved code: pick the first enabled+available; fall back to
      // first enabled (even if unavailable). Disabled providers are never
      // selected here — if no enabled provider exists at all the selector is
      // hidden and "No providers available." is shown instead.
      const first = newProviders.find(p => p.enabled && p.available)
                    ?? newProviders.find(p => p.enabled)
                    ?? null
      selectedProviderCode.value = first?.code ?? null
      historicalProviderCode.value = null
      fetchExamples()
    }
    return
  }

  // Subsequent reload (settings saved or lang changed).
  if (existing) {
    const wasHistorical = !!historicalProviderCode.value
    selectedProviderCode.value = existing.code
    historicalProviderCode.value = null
    if (existing.enabled && existing.available) {
      // Provider is (or became) valid: fetch if it was previously blocked or not yet loaded.
      if (wasHistorical || state.value === 'loading') fetchExamples()
    } else if (state.value !== 'loading') {
      // Provider became disabled/unavailable: clear content so the blocked message shows.
      state.value = 'loading'
      examples.value = []
      errorMsg.value = ''
    }
  } else if (hasPreserved) {
    // Saved code still not in registry: maintain/restore ghost.
    historicalProviderCode.value = props.initialProviderCode!
    selectedProviderCode.value = null
  } else {
    // No preserved code: re-validate the current selection and pick the first
    // usable when it's stale.
    historicalProviderCode.value = null
    const sp = newProviders.find(p => p.code === selectedProviderCode.value)
    if (!sp || !sp.enabled || !sp.available) {
      const first = newProviders.find(p => p.enabled && p.available)
                    ?? newProviders.find(p => p.enabled)
                    ?? null
      selectedProviderCode.value = first?.code ?? null
      if (first?.enabled && first?.available) {
        fetchExamples()
      } else {
        // No valid or enabled provider — reset state so the blocked message shows.
        state.value = 'loading'
        examples.value = []
        errorMsg.value = ''
      }
    } else if (state.value === 'loading') {
      fetchExamples()
    }
  }
}, { immediate: true })

const emit = defineEmits<{
  (e: 'fetched', examples: ContextExample[]): void
  (e: 'providerChanged', code: string | null): void
  (e: 'toggleAll', value: boolean): void
}>()

const router = useRouter()
const translatorStore = useTranslatorStore()
const containerRef = ref<HTMLElement | null>(null)
const { selectedText, buttonVisible, buttonLeft, buttonTop, dismiss } = useTextSelectionButton(containerRef)

function onSelectionTranslate() {
  const text = selectedText.value
  dismiss()
  translatorStore.translateWord(text, 'auto')
  router.push('/translator')
}

type State = 'loading' | 'done' | 'error'
const state = ref<State>('loading')
const examples = ref<ContextExample[]>([])
const allVisible = ref(props.showAllByDefault)
const revealed = reactive(new Set<number>())
const anyVisible = () => allVisible.value || revealed.size > 0
const errorMsg = ref('')
// Note: initialExamples is intentionally NOT applied here. Content is only
// restored inside the providers watcher once the saved provider is confirmed
// valid, preventing a flicker when the provider has since been disabled.

function toggleAllVisible() {
  if (anyVisible()) {
    allVisible.value = false
    revealed.clear()
  } else {
    allVisible.value = true
  }
  // Emit so callers that own a global "show translations" flag (e.g. the
  // translator view) can persist the new state across history navigation.
  emit('toggleAll', allVisible.value)
}

const hasTargets = computed(() => examples.value.some(e => !!e.target))

defineExpose({ toggleAllVisible, anyVisible, state, hasTargets })

function toggleExample(i: number) {
  const visible = allVisible.value || revealed.has(i)
  if (visible) {
    if (allVisible.value) {
      allVisible.value = false
      examples.value.forEach((_, j) => { if (j !== i) revealed.add(j) })
    } else {
      revealed.delete(i)
    }
  } else {
    revealed.add(i)
  }
}

// Monotonically increasing request id used to discard stale fetches when
// props (text / sourceLang / targetLang / provider) change while a request
// is in-flight.  Without this, a slow Reverso fetch issued for an old target
// language can resolve after a newer one and overwrite the displayed
// examples (or pollute the saved cache for the wrong history entry).
let _fetchSeq = 0

async function fetchExamples() {
  // Increment first so any in-flight request is invalidated even when this
  // call bails out below (e.g. providers not yet loaded).
  const seq = ++_fetchSeq
  if (!props.text) return
  state.value = 'loading'
  examples.value = []
  allVisible.value = props.showAllByDefault
  revealed.clear()
  errorMsg.value = ''
  // In inline mode providersLoaded is always true (set immediately in loadProviders).
  // In non-inline mode, bail and let the providers watcher retry when they arrive.
  if (!providersLoaded.value) return
  const usedCode = selectedProviderCode.value
  if (!usedCode) return
  if (!props.inline) {
    // Non-inline (wordbook): validate code against the loaded provider list.
    if (historicalProviderCode.value) return
    const sp = selectedProvider.value
    if (!sp || !sp.enabled || !sp.available) return
  }
  try {
    const result = await dictionaryApi.contextExamples(
      props.text,
      props.sourceLang,
      props.targetLang,
      usedCode,
    )
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    examples.value = result
    state.value = 'done'
    emit('providerChanged', usedCode)
  } catch (e: unknown) {
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    errorMsg.value = extractErrorMessage(e, 'Fetch error, please try later')
    state.value = 'error'
  } finally {
    if (seq === _fetchSeq) emit('fetched', examples.value)
  }
}

watch(() => [props.text, props.sourceLang, props.targetLang], () => {
  examples.value = []
  allVisible.value = props.showAllByDefault
  revealed.clear()
  errorMsg.value = ''
  fetchExamples()
})

// Inline mode: react to provider-code changes pushed by TranslatorView.
// Registered AFTER state/examples/fetchExamples are declared.
if (props.inline) {
  let _initialized = false
  watch(() => props.initialProviderCode, (code) => {
    inlineBlocked.value = !code
    selectedProviderCode.value = code ?? null
    examples.value = []
    allVisible.value = props.showAllByDefault
    revealed.clear()
    state.value = 'loading'
    errorMsg.value = ''
    if (!code) return
    // On initial mount: restore cached examples if available.
    // On subsequent provider changes: always fetch fresh (_initialized guards this).
    if (!_initialized && props.initialExamples !== undefined) {
      _initialized = true
      state.value = 'done'
      examples.value = props.initialExamples
      allVisible.value = props.showAllByDefault
      emit('fetched', examples.value)
      return
    }
    _initialized = true
    fetchExamples()
  }, { immediate: true })
}
</script>
