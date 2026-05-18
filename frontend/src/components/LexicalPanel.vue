<template>
  <!--
    `inline` mode (used by the translator's result panel) renders the
    matches with a small leading muted label instead of an uppercase
    section heading, and forces the provider selector into the abbrev-
    popup style so it competes less for attention with the page's main
    translation provider <select>.  The `compact` flag still controls
    other density tweaks for the wordbook details overlay.
  -->
  <div ref="containerRef">
    <!-- Header: label + provider selector -->
    <div
      v-if="!inline"
      class="flex items-center mb-3"
    >
      <h3 class="text-xs font-semibold uppercase tracking-widest text-gray-500">Lexical matches</h3>
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

    <!--
      State messages: skipped in `inline` mode so the translator's bottom
      row stays discreet — we'd rather render nothing than shout "No matches
      found." or "Loading…" alongside the main translation result.
      Branches form a single v-if/v-else-if chain so the chips render as
      the natural "happy path" terminator below.
    -->
    <p
      v-if="!inline && providersLoaded && visibleProviders.length === 0 && state === 'loading'"
      class="text-sm text-gray-500 italic"
    >No providers available.</p>

    <p
      v-else-if="!inline && fetchBlocked && state === 'loading'"
      class="text-sm text-gray-500 italic"
    >Provider unavailable.</p>

    <p
      v-else-if="!inline && state === 'loading'"
      class="text-sm text-gray-500"
    >Loading…</p>

    <div
      v-else-if="!inline && state === 'error'"
      class="text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2"
    >{{ errorMsg }}</div>

    <p
      v-else-if="!inline && state === 'done' && !matches.length"
      class="text-sm text-gray-500 italic"
    >No matches found.</p>

    <!-- Results: clickable chips in target-lang frequency order -->
    <div
      v-else-if="state === 'done' && matches.length"
      class="flex flex-wrap gap-1"
      :class="inline ? 'mt-1' : ''"
    >
      <span
        v-for="m in matches" :key="m"
        :class="[
          'rounded-lg cursor-pointer hover:bg-primary-500/20 hover:text-primary-300 transition-colors',
          inline
            ? 'text-[11px] bg-surface-800/70 px-1.5 py-0.5 text-gray-400'
            : 'text-xs bg-surface-800 px-1.5 py-0.5 text-gray-300',
        ]"
        @click="onMatchClick(m)"
      >{{ m }}</span>
    </div>
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
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { lexicalApi } from '@/api/lexical'
import { useTranslatorStore } from '@/stores/translator'
import { useSettingsStore } from '@/stores/settings'
import { extractErrorMessage } from '@/utils/error'
import { useTextSelectionButton } from '@/composables/useTextSelectionButton'
import type { ProviderItem } from '@/types'

const props = withDefaults(defineProps<{
  word: string
  sourceLang: string
  targetLang: string
  compact?: boolean
  // Translator-side embed: drop the section heading and the inline
  // provider trigger entirely; the parent page renders its own "Lexical"
  // label + popup and just feeds us the chosen provider code (or null to
  // mean "none — don't fetch"). Implies a smaller chip font.
  inline?: boolean
  // Saved matches from history to restore state without a re-fetch.
  // undefined = never fetched (auto-fetch); array (possibly empty) = already fetched.
  initialData?: string[]
  // Provider code last used for this entry; re-validated against the available list.
  initialProviderCode?: string | null
}>(), { compact: false, inline: false, initialData: undefined, initialProviderCode: undefined })

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
  // Inline mode: the translator view owns the provider selector and
  // pushes the chosen code in via `initialProviderCode`. Skip our own
  // provider-list fetch entirely so we don't make a redundant request
  // for a list we never display.
  if (props.inline) {
    providersLoaded.value = true
    return
  }
  providersLoaded.value = false
  try {
    const raw = await lexicalApi.providers(props.sourceLang, props.targetLang)
    providers.value = [...raw].sort((a, b) => a.position - b.position)
    providersLoaded.value = true
  } catch {
    // Non-critical; keep the existing list if the request fails
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

/** True when we have a provider selection but can't/shouldn't fetch. */
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
  fetchMatches()
}

let _providersReady = false
let _userSelectedProvider = false

watch(providers, (newProviders) => {
  // Inline mode is fully driven by the parent; skip the in-component
  // selection / fallback machinery and rely on the dedicated watcher
  // below that just mirrors `initialProviderCode` into local state.
  if (props.inline) return
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

  // The saved code is honoured only if it is still physically present in the
  // provider list. A code that's gone from the registry (provider removed,
  // not applicable to this lang pair, or disabled by an admin) behaves
  // identically to having no preserved code: pick the first usable provider.
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
        matches.value = props.initialData
      } else if (providerValid) {
        fetchMatches()  // valid provider, no cached data
      }
      // else: provider blocked — state stays 'loading', fetchBlocked shows the message.
    } else {
      // No preserved provider, or preserved code is not in the registry:
      // pick the first enabled+available; fall back to first enabled (even if
      // unavailable). Disabled providers are never selected here — if no
      // enabled provider exists at all the selector is hidden and the
      // "No providers available." message is shown instead.
      const first = newProviders.find(p => p.enabled && p.available)
                    ?? newProviders.find(p => p.enabled)
                    ?? null
      selectedProviderCode.value = first?.code ?? null
      historicalProviderCode.value = null
      fetchMatches()
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
      if (wasHistorical || state.value === 'loading') fetchMatches()
    } else if (state.value !== 'loading') {
      // Provider became disabled/unavailable: clear content so the blocked message shows.
      state.value = 'loading'
      matches.value = []
      errorMsg.value = ''
    }
  } else {
    // No preserved provider, or preserved code is not in the registry:
    // re-validate the current selection and pick the first usable when it's stale.
    historicalProviderCode.value = null
    const sp = newProviders.find(p => p.code === selectedProviderCode.value)
    if (!sp || !sp.enabled || !sp.available) {
      const first = newProviders.find(p => p.enabled && p.available)
                    ?? newProviders.find(p => p.enabled)
                    ?? null
      selectedProviderCode.value = first?.code ?? null
      if (first?.enabled && first?.available) {
        fetchMatches()
      } else {
        // No valid or enabled provider — reset state so the blocked message shows.
        state.value = 'loading'
        matches.value = []
        errorMsg.value = ''
      }
    } else if (state.value === 'loading') {
      fetchMatches()
    }
  }
}, { immediate: true })

const emit = defineEmits<{
  (e: 'fetched', matches: string[]): void
  (e: 'providerChanged', code: string | null): void
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
const matches = ref<string[]>([])
const errorMsg = ref('')
// Note: initialData is intentionally NOT applied here. Content is only
// restored inside the providers watcher once the saved provider is confirmed
// valid, preventing a flicker when the provider has since been disabled.

// Monotonically increasing request id used to discard stale fetches when
// props (word / sourceLang / targetLang / provider) change while a request
// is in-flight.
let _fetchSeq = 0

async function fetchMatches() {
  // Increment first so any in-flight request is invalidated even when this
  // call bails out below (e.g. providers not yet loaded).
  const seq = ++_fetchSeq
  if (!props.word) return
  state.value = 'loading'
  matches.value = []
  errorMsg.value = ''
  const usedCode = selectedProviderCode.value
  if (!usedCode) return
  if (!props.inline) {
    // Non-inline (wordbook) mode: validate against the loaded provider
    // list. Inline mode trusts whatever the translator view passed in
    // since it has already applied its own "first usable" fallback.
    if (!providersLoaded.value) return
    if (historicalProviderCode.value) return
    const sp = selectedProvider.value
    if (!sp || !sp.enabled || !sp.available) return
  }
  try {
    const result = await lexicalApi.matches(
      props.word,
      props.sourceLang,
      props.targetLang,
      usedCode,
    )
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    matches.value = result
    state.value = 'done'
    emit('providerChanged', usedCode)
  } catch (e: unknown) {
    if (seq !== _fetchSeq) return  // a newer fetch superseded this one
    errorMsg.value = extractErrorMessage(e, 'Fetch error, please try later')
    state.value = 'error'
  } finally {
    if (seq === _fetchSeq) emit('fetched', matches.value)
  }
}

watch(() => [props.word, props.sourceLang, props.targetLang], () => {
  matches.value = []
  errorMsg.value = ''
  fetchMatches()
})

// Inline mode: react to provider-code changes pushed by the translator
// view. `null` is an explicit "none" selection — clear matches and skip
// the fetch so the chips disappear entirely; a string code triggers a
// normal fetch (or restores cached data when available).
//
// Registered AFTER `state` / `matches` / `errorMsg` / `fetchMatches` are
// in scope: with `immediate: true` the callback runs synchronously
// during setup, so anything it touches must already be declared, or it
// throws a TDZ ReferenceError that Vue silently swallows (this used to
// leave the inline panel stuck "loading" on history navigation and
// fresh translations — the watcher only worked once the user toggled
// providers in the popup, where the callback re-runs after setup).
if (props.inline) {
  watch(() => props.initialProviderCode, (code) => {
    historicalProviderCode.value = null
    selectedProviderCode.value = code ?? null
    if (selectedProviderCode.value === null) {
      state.value = 'done'
      matches.value = []
      errorMsg.value = ''
      return
    }
    if (props.initialData !== undefined) {
      state.value = 'done'
      matches.value = props.initialData
      return
    }
    fetchMatches()
  }, { immediate: true })
}

/** Open the translator with the clicked match as input, reversing direction
 *  so the target-lang match is translated back into source-lang. */
function onMatchClick(match: string) {
  translatorStore.translateWord(match, props.targetLang, props.sourceLang)
  router.push('/translator')
}
</script>
