<template>
  <div ref="containerRef">
    <!-- Header: label + provider selector — hidden in inline mode (TranslatorView renders it). -->
    <div v-if="!inline" class="flex items-center mb-3">
      <h3 class="text-xs font-semibold uppercase tracking-widest text-gray-500">Definition</h3>
      <!-- Compact: abbrev clickable → popup (wordbook details) -->
      <template v-if="compact && providers.length > 0 && (visibleProviders.length > 0 || historicalProviderCode)">
        <div class="ml-auto relative" ref="popupAnchorRef">
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
        class="ml-auto bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500/50 transition-colors"
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

    <!-- Not found -->
    <p v-else-if="state === 'done' && !definition" class="text-sm text-gray-500 italic">No definition found.</p>

    <!-- Result -->
    <template v-else-if="state === 'done' && definition">
      <p v-if="definition.phonetics.length" class="text-xs text-gray-500 mb-2">
        {{ definition.phonetics.join('  ') }}
      </p>

      <div v-for="meaning in definition.meanings" :key="meaning.part_of_speech" class="mb-3">
        <span class="text-xs font-semibold uppercase tracking-widest text-primary-400">
          {{ meaning.part_of_speech }}
        </span>

        <ol class="list-decimal list-inside space-y-1 mt-1 ml-1">
          <li v-for="(def, i) in meaning.definitions" :key="i" class="text-sm text-gray-300 leading-snug">
            {{ def.definition }}
            <span v-if="def.example" class="block text-xs text-gray-500 ml-4 mt-0.5 italic">
              &ldquo;{{ def.example }}&rdquo;
            </span>
            <span v-if="def.synonyms.length" class="block ml-4 mt-0.5">
              <span
                v-for="syn in def.synonyms" :key="syn"
                class="inline-block mr-1 mb-0.5 text-xs text-primary-400 cursor-pointer hover:underline"
                @click="onWordClick(syn)"
              >{{ syn }}</span>
            </span>
          </li>
        </ol>

        <div v-if="meaning.synonyms.length" class="flex flex-wrap gap-1 mt-1.5 ml-1">
          <span
            v-for="syn in meaning.synonyms" :key="syn"
            class="text-xs bg-surface-800 rounded-lg px-1.5 py-0.5 text-gray-400 cursor-pointer hover:bg-primary-500/20 hover:text-primary-300 transition-colors"
            @click="onWordClick(syn)"
          >{{ syn }}</span>
        </div>
      </div>
    </template>

    </template><!-- /!inlineBlocked -->
  </div>

  <Teleport to="body">
    <button
      v-if="buttonVisible"
      :style="{ left: buttonLeft + 'px', top: buttonTop + 'px', transform: buttonTransform || undefined }"
      data-floating-translate-button
      class="fixed z-50 flex items-center justify-center p-1.5 bg-surface-900 border border-surface-700 rounded-lg text-primary-400 hover:text-primary-300 hover:bg-surface-800 shadow-lg transition-colors"
      @pointerdown.prevent
      @pointerup.stop="onSelectionTranslate"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0 0 14.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
      </svg>
    </button>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { definitionApi } from '@/api/definition'
import { useTranslatorStore } from '@/stores/translator'
import { useSettingsStore } from '@/stores/settings'
import { extractErrorMessage } from '@/utils/error'
import { useTextSelectionButton } from '@/composables/useTextSelectionButton'
import type { Definition, ProviderItem } from '@/types'

const props = withDefaults(defineProps<{
  word: string
  lang: string
  compact?: boolean
  // When true: TranslatorView owns the provider selector.  The panel hides its
  // own header and trusts the validated code fed via initialProviderCode directly
  // (same pattern as LexicalPanel inline mode).
  inline?: boolean
  // Pass saved definition from history entry to restore state on back/forward.
  // undefined = never fetched (auto-fetch); null = fetched, not found; object = fetched OK.
  initialData?: Definition | null
  // Provider code used when this entry was last fetched; restored and re-validated against
  // the available list.  Falls back to the first preferred provider when absent or invalid.
  initialProviderCode?: string | null
}>(), { compact: false, inline: false, initialData: undefined, initialProviderCode: undefined })

const settingsStore = useSettingsStore()

// All providers (enabled + excluded) sorted by position.
const providers = ref<ProviderItem[]>([])
const providersLoaded = ref(false)

// Set when initialProviderCode is not found in the providers list at all
// (provider removed from registry). Shows 🛇 label without a live entry to click.
const historicalProviderCode = ref<string | null>(null)

// Look up metadata from providers list; falls back to code for removed providers.
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
    const raw = await definitionApi.providers(props.lang)
    providers.value = [...raw].sort((a, b) => a.position - b.position)
    providersLoaded.value = true
  } catch {
    // Non-critical; keep the existing list if the request fails.
    // Must mark as loaded so fetch() is not blocked indefinitely — the
    // empty providers list will show "No providers available." instead.
    providersLoaded.value = true
  }
}

watch(() => props.lang, loadProviders, { immediate: true })
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

/** True when we have a provider selection but can't/shouldn't fetch. */
const fetchBlocked = computed(() => {
  if (!providersLoaded.value) return false
  if (historicalProviderCode.value) return true
  if (!selectedProviderCode.value) return true
  const sp = selectedProvider.value
  return !sp || !sp.enabled || !sp.available
})

/** Abbreviated label shown on the compact trigger button. */
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
  fetch()
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
      // Loaded list is empty (no providers for this lang, or all excluded):
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
  // not applicable to this lang) is shown as a ghost — blocking fetch but
  // preserving the entry's saved selection visually, mirroring translation/lex.
  const existing = hasPreserved
    ? newProviders.find(p => p.code === props.initialProviderCode)
    : undefined

  if (!_providersReady) {
    _providersReady = true
    if (existing) {
      selectedProviderCode.value = existing.code
      historicalProviderCode.value = null
      const providerValid = !!(existing.enabled && existing.available)
      if (providerValid && props.initialData !== undefined) {
        // Valid provider + cached data: restore content immediately, no fetch needed.
        state.value = 'done'
        definition.value = props.initialData
      } else if (providerValid) {
        fetch()  // valid provider, no cached data
      }
      // else: provider blocked — state stays 'loading', fetchBlocked shows the message.
    } else if (hasPreserved) {
      // Saved code is not in the provider registry (removed or not applicable
      // to this lang): ghost it so the entry's saved selection is visible.
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
      fetch()
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
      if (wasHistorical || state.value === 'loading') fetch()
    } else if (state.value !== 'loading') {
      // Provider became disabled/unavailable: clear content so the blocked message shows.
      state.value = 'loading'
      definition.value = null
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
        fetch()
      } else {
        // No valid or enabled provider — reset state so the blocked message shows.
        state.value = 'loading'
        definition.value = null
        errorMsg.value = ''
      }
    } else if (state.value === 'loading') {
      fetch()  // provider was previously blocked; retry
    }
  }
}, { immediate: true })

const emit = defineEmits<{
  (e: 'fetched', data: Definition | null): void
  (e: 'providerChanged', code: string | null): void
}>()
const translatorStore = useTranslatorStore()
const router = useRouter()

const containerRef = ref<HTMLElement | null>(null)
const { selectedText, buttonVisible, buttonLeft, buttonTop, buttonTransform, dismiss } = useTextSelectionButton(containerRef)

function onSelectionTranslate() {
  const text = selectedText.value
  dismiss()
  translatorStore.translateWord(text, 'auto')
  router.push('/translator')
}

type State = 'loading' | 'done' | 'error'
const state = ref<State>('loading')
const definition = ref<Definition | null>(null)
const errorMsg = ref('')
// Note: initialData is intentionally NOT applied here. Content is only
// restored inside the providers watcher once the saved provider is confirmed
// valid, preventing a flicker when the provider has since been disabled.

// Monotonically increasing request id used to discard stale fetches when
// props (word / lang / provider) change while a request is in-flight.
let _fetchSeq = 0

async function fetch() {
  // Increment first so any in-flight request is invalidated even when this
  // call bails out below (e.g. providers not yet loaded).
  const seq = ++_fetchSeq
  if (!props.word) return
  state.value = 'loading'
  definition.value = null
  errorMsg.value = ''
  // In inline mode providersLoaded is always true (set immediately in loadProviders).
  // In non-inline mode, bail and let the providers watcher retry when they arrive.
  if (!providersLoaded.value) return
  const usedCode = selectedProviderCode.value
  if (!usedCode) return
  if (!props.inline) {
    // Non-inline (wordbook): validate code against the loaded provider list.
    if (historicalProviderCode.value) return  // not in registry
    const sp = selectedProvider.value
    if (!sp || !sp.enabled || !sp.available) return  // excluded or unavailable
  }
  try {
    const result = await definitionApi.get(props.word, props.lang, usedCode)
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    definition.value = result
    state.value = 'done'
    emit('fetched', definition.value)
    emit('providerChanged', usedCode)
  } catch (e: unknown) {
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    errorMsg.value = extractErrorMessage(e, 'Fetch error, please try again later')
    state.value = 'error'
  }
}

watch(() => [props.word, props.lang], () => {
  definition.value = null
  errorMsg.value = ''
  fetch()
})

// Inline mode: react to provider-code changes pushed by TranslatorView.
// Registered AFTER state/definition/fetch are declared (immediate watcher runs
// synchronously during setup — anything it touches must already exist).
if (props.inline) {
  let _initialized = false
  watch(() => props.initialProviderCode, (code) => {
    inlineBlocked.value = !code
    selectedProviderCode.value = code ?? null
    definition.value = null
    state.value = 'loading'
    errorMsg.value = ''
    if (!code) return
    // On initial mount: restore cached data if available (avoids a redundant
    // fetch when history-navigating to an entry that was already fetched).
    // On subsequent provider changes (user picks a different provider from the
    // view's dropdown): always fetch fresh — _initialized guards this path.
    if (!_initialized && props.initialData !== undefined) {
      _initialized = true
      state.value = 'done'
      definition.value = props.initialData
      emit('fetched', definition.value)
      return
    }
    _initialized = true
    fetch()
  }, { immediate: true })
}

function onWordClick(word: string) {
  // Skip if the user drag-selected text (non-collapsed selection = floating
  // translate button is appearing; don't also navigate as a side-effect).
  if (!(window.getSelection()?.isCollapsed ?? true)) return
  translatorStore.translateWord(word)
  router.push('/translator')
}
</script>
