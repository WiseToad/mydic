<template>
  <div class="max-w-2xl mx-auto w-full flex-1 min-h-0 flex flex-col pb-3">
    <!-- Fixed header: back/close button + title + tab strip (non-scrollable) -->
    <div class="flex-none pt-8 pb-6 space-y-6">
      <div class="flex items-start gap-3">
        <button
          type="button"
          class="shrink-0 mt-1 inline-flex items-center justify-center w-8 h-8 rounded-lg text-gray-400 hover:text-gray-100 hover:bg-surface-800 transition-colors"
          :title="canGoBack ? 'Back' : 'Close'"
          :aria-label="canGoBack ? 'Back' : 'Close'"
          @click="goBack"
        >
          <svg v-if="canGoBack" xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M15.41 7.41 14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
          </svg>
          <svg v-else xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
            <path d="M19 6.41 17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
        <div>
          <h1 class="text-xl font-semibold text-gray-100">Preferences</h1>
          <p class="text-sm text-gray-500 mt-1">Drag items to reorder priority</p>
        </div>
      </div>
      <div class="flex items-center border-b border-surface-700">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          :class="[
            'px-3 py-1.5 text-sm font-medium transition-colors border-b-2 -mb-px',
            activeTab === tab.id
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-300',
          ]"
          @click="activeTab = tab.id"
        >{{ tab.label }}</button>
      </div>
    </div>

    <!-- Scrollable tab content -->
    <div class="flex-1 min-h-0 overflow-y-auto space-y-6" style="scrollbar-gutter: stable">
      <!-- Languages tab -->
      <template v-if="activeTab === 'languages'">
        <section class="card p-5 space-y-3">
          <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Languages</h2>
          <div v-if="!langStore.isLoaded" class="text-gray-500 text-sm">Loading…</div>
          <LangList v-else :items="langStore.languages" @toggle="handleLangToggle" @reorder="handleLangReorder" />
        </section>
      </template>

      <!-- Providers tab: translation + definition + context + lexical -->
      <template v-else-if="activeTab === 'providers'">
        <div v-if="!store.loaded && !store.error" class="text-gray-500 text-sm">Loading…</div>
        <div v-else-if="!store.loaded && store.error" class="text-sm text-red-400">{{ store.error }}</div>
        <template v-else>
          <section class="card p-5 space-y-3">
            <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Translation</h2>
            <ProviderList capability="translation" :items="store.translation" @toggle="handleToggle" @reorder="handleReorder" />
          </section>
          <section class="card p-5 space-y-3">
            <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Lexical</h2>
            <ProviderList capability="lexical" :items="store.lexical" @toggle="handleToggle" @reorder="handleReorder" />
          </section>
          <section class="card p-5 space-y-3">
            <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Definition</h2>
            <ProviderList capability="definition" :items="store.definition" @toggle="handleToggle" @reorder="handleReorder" />
          </section>
          <section class="card p-5 space-y-3">
            <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Context Examples</h2>
            <ProviderList capability="context" :items="store.context" @toggle="handleToggle" @reorder="handleReorder" />
          </section>
          <p v-if="store.error" class="text-sm text-red-400">{{ store.error }}</p>
        </template>
      </template>

      <!-- TTS tab -->
      <template v-else>
        <div v-if="!store.loaded && !store.error" class="text-gray-500 text-sm">Loading…</div>
        <div v-else-if="!store.loaded && store.error" class="text-sm text-red-400">{{ store.error }}</div>
        <section v-else class="card p-5 space-y-3">
          <h2 class="text-sm font-semibold text-gray-300 uppercase tracking-wide">Text-to-speech</h2>
          <p class="text-xs text-gray-500">Each provider expands to its voices. Voices show the languages they can pronounce.<br>
            Click language to hear the sample.</p>
          <TtsList
            :items="store.tts"
            @toggle="handleTtsToggle"
            @reorder="handleTtsReorder"
            @voice-toggle="handleVoiceToggle"
            @voice-reorder="handleVoiceReorder"
          />
          <p v-if="store.error" class="text-sm text-red-400">{{ store.error }}</p>
        </section>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, defineComponent, h, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore, type Capability } from '@/stores/settings'
import { useLanguageSettingsStore, type LangPref } from '@/stores/languageSettings'
import { useToastStore } from '@/stores/toast'
import { playTts, stopTts } from '@/api/tts'
import { ttsSampleFor, ensureTtsSamplesLoaded } from '@/utils/ttsSamples'
import { extractErrorMessage } from '@/utils/error'
import type { ProviderItem, TtsVoiceItem } from '@/types'
import { useAuthStore } from '@/stores/auth'

const store = useSettingsStore()
const langStore = useLanguageSettingsStore()
const router = useRouter()
const toast = useToastStore()

// ─── TTS sample playback state ────────────────────────────────────────────────
// Tracks which (provider, voice, lang) is currently being generated/played so
// TtsList can show a spinner during generation and a stop button during playback.
interface SampleState {
  providerCode: string
  voiceId: string
  lang: string
  phase: 'generating' | 'playing'
}
const activeSample = ref<SampleState | null>(null)

// ---------------------------------------------------------------------------
// Tab state
// ---------------------------------------------------------------------------
//
// Three tabs split the formerly-single column into logical groups so the
// page is no longer overscrolling vertically. The active tab is persisted
// in localStorage so reload returns the user to the same group.
type SettingsTab = 'languages' | 'providers' | 'tts'
const tabs: { id: SettingsTab; label: string }[] = [
  { id: 'languages', label: 'Languages' },
  { id: 'providers', label: 'Providers' },
  { id: 'tts', label: 'TTS' },
]
const _userId = useAuthStore().user?.id
const SETTINGS_VIEW_KEY = _userId != null ? `mydicSettingsView${_userId}` : 'mydicSettingsView'
function _loadActiveTab(): SettingsTab {
  try {
    const raw = localStorage.getItem(SETTINGS_VIEW_KEY)
    if (raw) {
      const node = JSON.parse(raw)
      if (node.activeTab === 'languages' || node.activeTab === 'providers' || node.activeTab === 'tts') return node.activeTab
    }
  } catch { /* ignore */ }
  return 'languages'
}
const activeTab = ref<SettingsTab>(_loadActiveTab())
watch(activeTab, (v) => {
  try {
    let node: Record<string, unknown> = {}
    try { node = JSON.parse(localStorage.getItem(SETTINGS_VIEW_KEY) ?? '{}') } catch { /* */ }
    node.activeTab = v
    localStorage.setItem(SETTINGS_VIEW_KEY, JSON.stringify(node))
  } catch { /* quota */ }
})

// Tracks which sample is in-flight independently of the reactive
// `activeSample` so the click-to-stop guard works within the spinner delay
// window and so the delay timer can be cancelled when audio starts early.
interface SampleKey { providerCode: string; voiceId: string; lang: string }
let _sampleInFlight: SampleKey | null = null
let _sampleSpinnerTimer: ReturnType<typeof setTimeout> | null = null
function _cancelSampleSpinnerTimer() {
  if (_sampleSpinnerTimer !== null) { clearTimeout(_sampleSpinnerTimer); _sampleSpinnerTimer = null }
}

/**
 * Play a short sample sentence in *lang* through the given (provider, voice).
 * The spinner is shown only after a short delay so cached/fast responses
 * skip it entirely; clicking a currently-active sample stops it.
 */
async function playVoiceSample(
  provider: ProviderItem,
  voice: TtsVoiceItem,
  lang: string,
) {
  // If clicking the in-flight sample — stop it.
  if (
    _sampleInFlight?.providerCode === provider.code &&
    _sampleInFlight?.voiceId === voice.id &&
    _sampleInFlight?.lang === lang
  ) {
    stopTts()
    _cancelSampleSpinnerTimer()
    _sampleInFlight = null
    activeSample.value = null
    return
  }
  // Stop any other ongoing playback and arm the new request.
  stopTts()
  _cancelSampleSpinnerTimer()
  _sampleInFlight = { providerCode: provider.code, voiceId: voice.id, lang }
  activeSample.value = null
  // Delay spinner to avoid flicker for fast / cached responses.
  _sampleSpinnerTimer = setTimeout(() => {
    _sampleSpinnerTimer = null
    if (
      _sampleInFlight?.providerCode === provider.code &&
      _sampleInFlight?.voiceId === voice.id &&
      _sampleInFlight?.lang === lang
    ) {
      activeSample.value = { providerCode: provider.code, voiceId: voice.id, lang, phase: 'generating' }
    }
  }, 150)
  try {
    await playTts(
      ttsSampleFor(lang), lang,
      { speed: 'NORMAL', provider: provider.code, voice: voice.id },
      () => {
        // Audio has started — cancel pending spinner and switch to stop-button.
        _cancelSampleSpinnerTimer()
        if (
          _sampleInFlight?.providerCode === provider.code &&
          _sampleInFlight?.voiceId === voice.id &&
          _sampleInFlight?.lang === lang
        ) {
          activeSample.value = { providerCode: provider.code, voiceId: voice.id, lang, phase: 'playing' }
        }
      },
    )
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Could not play sample'))
  } finally {
    _cancelSampleSpinnerTimer()
    if (
      _sampleInFlight?.providerCode === provider.code &&
      _sampleInFlight?.voiceId === voice.id &&
      _sampleInFlight?.lang === lang
    ) {
      _sampleInFlight = null
      activeSample.value = null
    }
  }
}

// Track whether there is a previous in-app route to return to. Captured once
// at mount so the button label stays stable while on the settings page.
const canGoBack = ref(
  typeof window !== 'undefined' && window.history.state?.back != null,
)

function goBack() {
  if (canGoBack.value) {
    router.back()
  } else {
    router.push({ name: 'translator' })
  }
}

onMounted(() => {
  store.load()
  langStore.load()
  ensureTtsSamplesLoaded()
})

function handleToggle(cap: Capability, index: number) {
  store.toggleEnabled(cap, index)
  store.save()
}

function handleReorder(cap: Capability, from: number, to: number) {
  store.reorder(cap, from, to)
  store.save()
}

function handleTtsToggle(index: number) {
  store.toggleEnabled('tts', index)
  store.save()
}

function handleTtsReorder(from: number, to: number) {
  store.reorder('tts', from, to)
  store.save()
}

function handleVoiceToggle(providerIndex: number, voiceIndex: number) {
  store.toggleVoiceEnabled(providerIndex, voiceIndex)
  store.save()
}

function handleVoiceReorder(providerIndex: number, from: number, to: number) {
  store.reorderVoice(providerIndex, from, to)
  store.save()
}

function handleLangToggle(index: number) {
  langStore.toggleEnabled(index)
}

function handleLangReorder(from: number, to: number) {
  langStore.reorder(from, to)
}

// ---------------------------------------------------------------------------
// Inline sub-components to avoid separate files for simple lists
// ---------------------------------------------------------------------------
const LangList = defineComponent({
  name: 'LangList',
  props: {
    items: { type: Array as () => LangPref[], required: true },
  },
  emits: ['toggle', 'reorder'],
  setup(props, { emit }) {
    const draggedIndex = ref<number | null>(null)
    const dragOverIndex = ref<number | null>(null)
    const dragSourceEl = ref<HTMLElement | null>(null)

    function onDragStart(event: DragEvent, index: number) {
      draggedIndex.value = index
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
      dragSourceEl.value = event.currentTarget as HTMLElement
      dragSourceEl.value.style.opacity = '0.4'
    }

    function onDragOver(event: DragEvent, index: number) {
      event.preventDefault()
      if (draggedIndex.value === null) return
      dragOverIndex.value = index
    }

    function onDragLeave() { dragOverIndex.value = null }

    function onDrop(event: DragEvent, targetIndex: number) {
      event.preventDefault()
      const from = draggedIndex.value
      if (from === null || from === targetIndex) { cleanupDrag(); return }
      emit('reorder', from, targetIndex)
      cleanupDrag()
    }

    function cleanupDrag() {
      if (dragSourceEl.value) { dragSourceEl.value.style.opacity = ''; dragSourceEl.value = null }
      draggedIndex.value = null
      dragOverIndex.value = null
    }

    return () =>
      h('ul', { class: 'space-y-1' },
        props.items.map((item, index) =>
          h('li', {
            key: item.code,
            draggable: true,
            class: [
              'flex items-center gap-2 px-3 py-2 rounded-lg border cursor-default transition-colors',
              !item.enabled
                ? 'border-surface-700 opacity-50'
                : 'border-surface-700 bg-surface-800/50',
              dragOverIndex.value === index && draggedIndex.value !== index
                ? 'border-primary-500/50 ring-2 ring-primary-500/50'
                : '',
            ],
            onDragstart: (e: DragEvent) => onDragStart(e, index),
            onDragover: (e: DragEvent) => onDragOver(e, index),
            onDragleave: () => onDragLeave(),
            onDrop: (e: DragEvent) => onDrop(e, index),
            onDragend: () => cleanupDrag(),
          }, [
            h('input', {
              type: 'checkbox',
              checked: item.enabled,
              class: 'w-3.5 h-3.5 rounded accent-primary-500 cursor-pointer shrink-0',
              onChange: () => emit('toggle', index),
            }),
            h('span', { class: 'flex-1 text-sm text-gray-200' }, [
              item.name,
              ' ',
              h('span', { class: 'text-gray-500' }, `(${item.code})`),
            ]),
          ])
        )
      )
  },
})

const ProviderList = defineComponent({
  name: 'ProviderList',
  props: {
    capability: { type: String as () => Capability, required: true },
    items: { type: Array as () => ProviderItem[], required: true },
  },
  emits: ['toggle', 'reorder'],
  setup(props, { emit }) {
    const draggedIndex = ref<number | null>(null)
    const dragOverIndex = ref<number | null>(null)
    const dragSourceEl = ref<HTMLElement | null>(null)

    function onDragStart(event: DragEvent, index: number) {
      draggedIndex.value = index
      if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
      dragSourceEl.value = event.currentTarget as HTMLElement
      dragSourceEl.value.style.opacity = '0.4'
    }

    function onDragOver(event: DragEvent, index: number) {
      event.preventDefault()
      if (draggedIndex.value === null) return
      dragOverIndex.value = index
    }

    function onDragLeave() {
      dragOverIndex.value = null
    }

    function onDrop(event: DragEvent, targetIndex: number) {
      event.preventDefault()
      const from = draggedIndex.value
      if (from === null || from === targetIndex) { cleanupDrag(); return }
      emit('reorder', props.capability, from, targetIndex)
      cleanupDrag()
    }

    function cleanupDrag() {
      if (dragSourceEl.value) {
        dragSourceEl.value.style.opacity = ''
        dragSourceEl.value = null
      }
      draggedIndex.value = null
      dragOverIndex.value = null
    }

    return () =>
      props.items.length === 0
        ? h('p', { class: 'text-sm text-gray-500 italic' }, 'No providers available.')
        : h('ul', { class: 'space-y-1' },
        props.items.map((item, index) =>
          h('li', {
            key: String(item.code),
            draggable: true,
            class: [
'flex items-center gap-2 px-3 py-2 rounded-lg border cursor-default transition-colors',
              !item.enabled
                ? 'border-surface-700 opacity-50'
                : 'border-surface-700 bg-surface-800/50',
              dragOverIndex.value === index && draggedIndex.value !== index
                ? 'border-primary-500/50 ring-2 ring-primary-500/50'
                : '',
            ],
            onDragstart: (e: DragEvent) => onDragStart(e, index),
            onDragover: (e: DragEvent) => onDragOver(e, index),
            onDragleave: () => onDragLeave(),
            onDrop: (e: DragEvent) => onDrop(e, index),
            onDragend: () => cleanupDrag(),
          }, [
            // Checkbox (checked = included / active)
            h('input', {
              type: 'checkbox',
              checked: item.enabled,
              class: 'w-3.5 h-3.5 rounded accent-primary-500 cursor-pointer shrink-0',
              onChange: () => emit('toggle', props.capability, index),
            }),

            // Provider name
            h('span', {
              class: [
                'flex-1 text-sm text-gray-200',
                !item.available ? 'opacity-50' : '',
              ],
            }, item.name ?? '—'),

            // Unavailability indicator
            !item.available
              ? h('span', {
                  title: item.unavailable_reason ?? 'Not available',
                  class: 'flex items-center justify-center text-amber-500 cursor-help shrink-0',
                },
                h('svg', {
                  xmlns: 'http://www.w3.org/2000/svg',
                  class: 'w-3.5 h-3.5',
                  viewBox: '0 0 24 24',
                  fill: 'currentColor',
                }, h('path', {
                  d: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z',
                }))
              )
              : null,
          ])
        )
      )
  },
})

// ---------------------------------------------------------------------------
// TTS provider list with nested per-provider voice list. Providers can be
// expanded/collapsed; each voice row shows its supported languages and can
// be enabled/disabled and reordered independently within its provider.
// ---------------------------------------------------------------------------
const TtsList = defineComponent({
  name: 'TtsList',
  props: {
    items: { type: Array as () => ProviderItem[], required: true },
  },
  emits: ['toggle', 'reorder', 'voice-toggle', 'voice-reorder'],
  setup(props, { emit }) {
    const expanded = ref<Set<string>>(new Set())

    // Provider drag state
    const dragProvider = ref<number | null>(null)
    const dragOverProvider = ref<number | null>(null)
    const dragProviderEl = ref<HTMLElement | null>(null)

    // Voice drag state (provider-scoped)
    const dragVoice = ref<{ providerIndex: number; voiceIndex: number } | null>(null)
    const dragOverVoice = ref<{ providerIndex: number; voiceIndex: number } | null>(null)
    const dragVoiceEl = ref<HTMLElement | null>(null)

    function isExpanded(code: string): boolean { return expanded.value.has(code) }

    function toggleExpanded(code: string) {
      const next = new Set(expanded.value)
      next.has(code) ? next.delete(code) : next.add(code)
      expanded.value = next
    }

    function onProviderDragStart(e: DragEvent, index: number) {
      dragProvider.value = index
      if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
      dragProviderEl.value = e.currentTarget as HTMLElement
      dragProviderEl.value.style.opacity = '0.4'
    }

    function onProviderDragOver(e: DragEvent, index: number) {
      e.preventDefault()
      if (dragProvider.value === null) return
      dragOverProvider.value = index
    }

    function onProviderDrop(e: DragEvent, targetIndex: number) {
      e.preventDefault()
      const from = dragProvider.value
      if (from === null || from === targetIndex) { cleanupProviderDrag(); return }
      emit('reorder', from, targetIndex)
      cleanupProviderDrag()
    }

    function cleanupProviderDrag() {
      if (dragProviderEl.value) { dragProviderEl.value.style.opacity = ''; dragProviderEl.value = null }
      dragProvider.value = null
      dragOverProvider.value = null
    }

    function onVoiceDragStart(e: DragEvent, providerIndex: number, voiceIndex: number) {
      e.stopPropagation()
      dragVoice.value = { providerIndex, voiceIndex }
      if (e.dataTransfer) e.dataTransfer.effectAllowed = 'move'
      dragVoiceEl.value = e.currentTarget as HTMLElement
      dragVoiceEl.value.style.opacity = '0.4'
    }

    function onVoiceDragOver(e: DragEvent, providerIndex: number, voiceIndex: number) {
      e.preventDefault()
      e.stopPropagation()
      if (dragVoice.value === null || dragVoice.value.providerIndex !== providerIndex) return
      dragOverVoice.value = { providerIndex, voiceIndex }
    }

    function onVoiceDrop(e: DragEvent, providerIndex: number, voiceIndex: number) {
      e.preventDefault()
      e.stopPropagation()
      const drag = dragVoice.value
      if (!drag || drag.providerIndex !== providerIndex || drag.voiceIndex === voiceIndex) {
        cleanupVoiceDrag()
        return
      }
      emit('voice-reorder', providerIndex, drag.voiceIndex, voiceIndex)
      cleanupVoiceDrag()
    }

    function cleanupVoiceDrag() {
      if (dragVoiceEl.value) { dragVoiceEl.value.style.opacity = ''; dragVoiceEl.value = null }
      dragVoice.value = null
      dragOverVoice.value = null
    }

    function renderVoice(
      provider: ProviderItem,
      providerIndex: number,
      voice: TtsVoiceItem,
      voiceIndex: number,
    ) {
      const isOver =
        dragOverVoice.value?.providerIndex === providerIndex &&
        dragOverVoice.value?.voiceIndex === voiceIndex &&
        !(dragVoice.value?.providerIndex === providerIndex && dragVoice.value?.voiceIndex === voiceIndex)
      return h('li', {
        key: voice.id,
        draggable: true,
        class: [
          'flex items-center gap-2 px-3 py-1.5 rounded-md border cursor-default transition-colors',
          !voice.enabled
            ? 'border-surface-700/60 opacity-50'
            : 'border-surface-700/60 bg-surface-800/30',
          isOver ? 'border-primary-500/50 ring-2 ring-primary-500/50' : '',
        ],
        onDragstart: (e: DragEvent) => onVoiceDragStart(e, providerIndex, voiceIndex),
        onDragover: (e: DragEvent) => onVoiceDragOver(e, providerIndex, voiceIndex),
        onDragleave: (e: DragEvent) => { e.stopPropagation(); dragOverVoice.value = null },
        onDrop: (e: DragEvent) => onVoiceDrop(e, providerIndex, voiceIndex),
        onDragend: () => cleanupVoiceDrag(),
      }, [
        h('input', {
          type: 'checkbox',
          checked: voice.enabled,
          class: 'w-3.5 h-3.5 rounded accent-primary-500 cursor-pointer shrink-0',
          onChange: () => emit('voice-toggle', providerIndex, voiceIndex),
        }),
        h('span', { class: 'flex-1 text-sm text-gray-200 truncate' }, voice.name || voice.id),
        voice.languages.length > 0
          ? renderVoiceLangs(provider, voice)
          : null,
      ])
    }

    /**
     * Render the per-voice language list as a clickable button row.  Clicking
     * a code plays a short sample of *voice* in that lang via the parent
     * provider; the row is non-draggable (pointerdown.stop) so the click
     * doesn't accidentally start a drag of the surrounding list item.
     *
     * When playback is obviously impossible — the provider is reported as
     * unavailable by the backend (e.g. binary missing, optional dep not
     * installed) — the abbrev is rendered in a disabled state: dimmed,
     * not-allowed cursor, no hover-to-primary transition, and the tooltip
     * surfaces the provider's ``unavailable_reason`` instead of the play
     * hint.  User-disabled provider/voice flags are intentionally NOT
     * treated as blocked here because the backend honours an explicit
     * (provider, voice) override regardless of those preferences.
     */
    function renderVoiceLangs(provider: ProviderItem, voice: TtsVoiceItem) {
      const blocked = !provider.available
      const blockedReason = provider.unavailable_reason ?? 'Not available'
      const buttons = voice.languages.map(lang => {
        const sample = activeSample.value
        const isActive =
          sample?.providerCode === provider.code &&
          sample?.voiceId === voice.id &&
          sample?.lang === lang
        const phase = isActive ? sample!.phase : null
        let btnClass: string
        let btnTitle: string
        let icon: ReturnType<typeof h> | null = null
        if (blocked) {
          btnClass = 'relative inline-flex items-center justify-center w-7 text-sm text-gray-600 cursor-not-allowed'
          btnTitle = `Cannot play sample in ${lang}: ${blockedReason}`
        } else if (phase === 'generating') {
          icon = h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            class: 'animate-spin w-3.5 h-3.5',
            viewBox: '0 0 24 24',
            fill: 'none',
          }, [
            h('circle', { class: 'opacity-25', cx: '12', cy: '12', r: '10', stroke: 'currentColor', 'stroke-width': '4' }),
            h('path', { class: 'opacity-75', fill: 'currentColor', d: 'M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z' }),
          ])
          btnClass = 'relative inline-flex items-center justify-center w-7 text-sm text-gray-400 cursor-pointer'
          btnTitle = `Generating sample in ${lang}… (click to cancel)`
        } else if (phase === 'playing') {
          icon = h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            class: 'w-3.5 h-3.5',
            viewBox: '0 0 24 24',
            fill: 'currentColor',
          }, h('path', { d: 'M6 6h12v12H6z' }))
          btnClass = 'relative inline-flex items-center justify-center w-7 text-sm text-red-400 hover:text-red-300 cursor-pointer'
          btnTitle = `Stop sample in ${lang}`
        } else {
          btnClass = 'relative inline-flex items-center justify-center w-7 text-sm text-gray-400 hover:text-primary-400 transition-colors cursor-pointer'
          btnTitle = `Play sample in ${lang}`
        }
        // The lang text is always rendered (to hold the natural text width of the
        // button), but made invisible when an icon is overlaid.  The icon is
        // absolutely centred so it never affects the button's layout box.
        return h('button', {
          type: 'button',
          disabled: blocked,
          class: btnClass,
          title: btnTitle,
          onPointerdown: (e: PointerEvent) => e.stopPropagation(),
          onMousedown: (e: MouseEvent) => e.stopPropagation(),
          onClick: (e: MouseEvent) => {
            e.stopPropagation()
            if (blocked) return
            void playVoiceSample(provider, voice, lang)
          },
        }, [
          h('span', { class: icon ? 'invisible' : '' }, lang),
          icon ? h('span', { class: 'absolute inset-0 flex items-center justify-center' }, icon) : null,
        ])
      })
      return h('span', { class: 'flex items-center gap-1 shrink-0' }, buttons)
    }

    function renderProvider(provider: ProviderItem, providerIndex: number) {
      const isOpen = isExpanded(provider.code)
      const voices = provider.voices ?? []
      const enabledVoiceCount = voices.filter(v => v.enabled).length
      const overProvider =
        dragOverProvider.value === providerIndex && dragProvider.value !== providerIndex
      const header = h('div', {
        draggable: true,
        class: [
          'flex items-center gap-2 px-3 py-2 rounded-lg border cursor-default transition-colors',
          !provider.enabled ? 'border-surface-700 opacity-50' : 'border-surface-700 bg-surface-800/50',
          overProvider ? 'border-primary-500/50 ring-2 ring-primary-500/50' : '',
        ],
        onDragstart: (e: DragEvent) => onProviderDragStart(e, providerIndex),
        onDragover: (e: DragEvent) => onProviderDragOver(e, providerIndex),
        onDragleave: () => { dragOverProvider.value = null },
        onDrop: (e: DragEvent) => onProviderDrop(e, providerIndex),
        onDragend: () => cleanupProviderDrag(),
      }, [
        h('input', {
          type: 'checkbox',
          checked: provider.enabled,
          class: 'w-3.5 h-3.5 rounded accent-primary-500 cursor-pointer shrink-0',
          onChange: () => emit('toggle', providerIndex),
        }),
        h('button', {
          type: 'button',
          class: 'flex-1 flex items-center gap-2 text-left text-sm text-gray-200 min-w-0',
          onClick: () => toggleExpanded(provider.code),
        }, [
          h('svg', {
            xmlns: 'http://www.w3.org/2000/svg',
            class: ['w-3 h-3 text-gray-500 transition-transform shrink-0', isOpen ? 'rotate-90' : ''],
            viewBox: '0 0 24 24',
            fill: 'currentColor',
          }, h('path', { d: 'M8.59 16.59 13.17 12 8.59 7.41 10 6l6 6-6 6z' })),
          h('span', { class: ['truncate', !provider.available ? 'opacity-50' : ''] }, provider.name ?? provider.code),
          voices.length > 0
            ? h('span', { class: 'text-xs text-gray-500 shrink-0' }, `${enabledVoiceCount} / ${voices.length} voice${voices.length === 1 ? '' : 's'}`)
            : null,
        ]),
        !provider.available
          ? h('span', {
              title: provider.unavailable_reason ?? 'Not available',
              class: 'flex items-center justify-center text-amber-500 cursor-help shrink-0',
            },
            h('svg', {
              xmlns: 'http://www.w3.org/2000/svg',
              class: 'w-3.5 h-3.5',
              viewBox: '0 0 24 24',
              fill: 'currentColor',
            }, h('path', { d: 'M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z' })))
          : null,
      ])
      const body = isOpen && voices.length > 0
        ? h('ul', { class: 'mt-1 ml-6 space-y-1' },
            voices.map((voice, voiceIndex) => renderVoice(provider, providerIndex, voice, voiceIndex)))
        : null
      return h('li', { key: provider.code, class: 'space-y-1' }, [header, body])
    }

    return () =>
      props.items.length === 0
        ? h('p', { class: 'text-sm text-gray-500 italic' }, 'No providers available.')
        : h('ul', { class: 'space-y-1' }, props.items.map((p, i) => renderProvider(p, i)))
  },
})
</script>
