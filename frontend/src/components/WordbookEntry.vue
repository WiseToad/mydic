<template>
  <!--
    Outer wrapper = grid item. No padding/border so its natural height equals the card's
    border-box height. Grid stretches all wrappers in a row to equal height.
    z-20 when expanded so the overlay floats above cards in subsequent rows.
  -->
  <div ref="entryRootRef" class="relative" :class="expandedInfo ? 'z-20' : ''">

    <!--
      Card: h-full fills the grid-stretched wrapper. Dynamic bottom-radius:
      square when overlay is attached, rounded otherwise.
      highlight: brief flash triggered by side-panel clicks / cross-view jumps.
      When the details panel is open, `wordbook-flash` is also applied there
      so the whole card perimeter flashes as a single unit.
    -->
    <div
      ref="cardRef"
      class="group/provider h-full p-3 border border-surface-700"
      :class="[
        cardBgClass,
        expandedInfo && !editing ? 'rounded-t-2xl' : 'rounded-2xl',
        isDragTarget ? 'ring-2 ring-primary-500/50' : '',
      ]"
      @animationend.self="onFlashEnd"
    >
      <!-- Edit mode: unified form (replaces entire card content) -->
      <template v-if="editing">
        <div class="space-y-1.5">
          <!-- Row 1: original word -->
          <div class="flex items-center gap-2">
            <div class="relative flex-1">
              <input v-model="editSource" class="input w-full py-1 pr-9" placeholder="Original" />
              <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs font-mono text-gray-500 pointer-events-none select-none">{{ entry.source_lang }}</span>
            </div>
            <div class="flex items-center gap-1 shrink-0">
              <button
                title="Save"
                :disabled="!editSource.trim() || !editTarget.trim()"
                class="inline-flex items-center justify-center w-7 h-7 rounded-full text-gray-500 hover:text-emerald-400 hover:bg-emerald-500/10 disabled:opacity-40 transition-colors"
                @click="saveEdit"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
              </button>
              <button
                title="Cancel"
                class="inline-flex items-center justify-center w-7 h-7 rounded-full text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-colors"
                @click="cancelEdit"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
              </button>
            </div>
          </div>
          <!-- Row 2: translation -->
          <div class="flex items-center gap-2">
            <div class="relative flex-1">
              <input v-model="editTarget" class="input w-full py-1 pr-9" placeholder="Translation" @input="onEditTargetInput" />
              <span class="absolute right-2.5 top-1/2 -translate-y-1/2 text-xs font-mono text-gray-500 pointer-events-none select-none">{{ entry.target_lang }}</span>
            </div>
            <div class="flex items-center justify-end gap-1 shrink-0">
              <!-- Provider picker -->
              <div class="relative">
                <button
                  title="Change provider"
                  :disabled="usableEditProviders.length === 0"
                  class="inline-flex items-center justify-center w-7 h-7 rounded-full text-gray-500 hover:text-primary-400 hover:bg-primary-500/10 disabled:opacity-40 transition-colors"
                  @click.stop="showProviderPopup = !showProviderPopup"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M7 10l5 5 5-5z"/></svg>
                </button>
                <div
                  v-if="showProviderPopup"
                  ref="providerPopupRef"
class="absolute top-full right-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col"
                  @click.stop
                >
                  <button
                    v-for="p in visibleEditProviders"
                    :key="p.code"
                    :data-code="p.code"
                    :disabled="!p.enabled || !p.available"
                    :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors"
                    :class="p.code === editProviderCode && (!p.enabled || !p.available)
                      ? 'text-gray-400 cursor-not-allowed'
                      : (!p.enabled || !p.available)
                        ? 'text-gray-600 cursor-not-allowed'
                        : p.code === editProviderCode
                          ? 'text-primary-400 bg-primary-500/10'
                          : 'text-gray-300 hover:bg-surface-800'"
                    @click="selectEditProvider(p)"
                  >{{ !p.enabled ? `🛇 ${p.name}` : (!p.available ? `⚠ ${p.name}` : p.name) }}</button>
                </div>
              </div>
              <button
                title="Re-translate"
                :disabled="!editSource.trim() || retranslating || selectedProviderUnusable"
                class="inline-flex items-center justify-center w-7 h-7 rounded-full text-gray-500 hover:text-primary-400 hover:bg-primary-500/10 disabled:opacity-40 transition-colors"
                @click="retranslateEdit"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
                </svg>
              </button>
            </div>
          </div>
          <!-- Row 3: notes -->
          <textarea
            v-model="editNotes"
            rows="2"
            class="input resize-none py-1 w-full"
            placeholder="Notes (optional)"
          />
        </div>
      </template>

      <!-- View mode -->
      <template v-else>
        <!-- Primary toolbar: source text + [audio / hint-toggle / edit / delete] -->
        <div class="flex items-start gap-2">
          <div class="flex-1 min-w-0">
            <p class="font-medium text-gray-100">
              <span
                class="cursor-pointer hover:text-primary-400 transition-colors"
                @click="hintVisible = !hintVisible"
              >{{ entry.source_text }}</span>
            </p>
          </div>

          <div class="flex items-center gap-1 shrink-0">
            <AudioButton :text="entry.source_text" :lang="entry.source_lang" size="sm" title="Pronounce source" />

            <template v-if="!isCompact">
              <div class="relative" ref="actionsContainerRef">
                <button
                  title="More actions"
                  class="inline-flex items-center justify-center w-7 h-7 rounded-full text-gray-500 hover:text-gray-300 hover:bg-surface-700 transition-colors"
                  @click.stop="showActionsMenu = !showActionsMenu"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M12 8c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm0 2c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm0 6c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2z"/>
                  </svg>
                </button>
                <!--
                  Placement flips to `bottom-full mb-1` (i.e. above the
                  trigger) when the entry sits close enough to the bottom
                  edge of the viewport that the natural top-full popup
                  would overflow.  See `actionsMenuPlacement` in script.
                -->
                <div
                  v-if="showActionsMenu"
                  class="absolute right-0 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[140px]"
                  :class="actionsMenuPlacement === 'above' ? 'bottom-full mb-1' : 'top-full mt-1'"
                  @click.stop
                >
                  <button
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-gray-300 hover:bg-surface-800 transition-colors flex items-center gap-2"
                    @click="handleEdit"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zm17.71-10.46c.39-.39.39-1.02 0-1.41l-2.34-2.34a.9959.9959 0 0 0-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                    Edit
                  </button>
                  <!--
                    Color submenu trigger: clicking opens an adjacent popup with
                    labeled color swatches. The submenu is rendered just below
                    so it shares the actions container scope and is not closed
                    by the outside-click handler.
                  -->
                  <button
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-gray-300 hover:bg-surface-800 transition-colors flex items-center gap-2"
                    :class="showColorSubmenu ? 'bg-surface-800' : ''"
                    @click="toggleColorSubmenu"
                  >
                    <svg class="w-3.5 h-3.5" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.3">
                      <circle cx="6"  cy="6"  r="3.2"/>
                      <circle cx="10" cy="6"  r="3.2"/>
                      <circle cx="8"  cy="10" r="3.2"/>
                    </svg>
                    Color
                    <span class="ml-auto text-gray-500">›</span>
                  </button>
                  <!--
                    Color submenu: floats to the right of the actions menu by
                    default; falls back to the left when the actions popup is
                    too close to the viewport's right edge to fit the submenu
                    (typical case: rightmost grid card with the side panel
                    closed). Lives inside the actions popup so the same
                    outside-click container check keeps both popups open while
                    the user navigates between them.
                  -->
                  <div
                    v-if="showColorSubmenu"
                    class="absolute top-0 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[120px]"
                    :class="submenuPlacement === 'left' ? 'right-full mr-1' : 'left-full ml-1'"
                  >
                    <button
                      v-for="c in colorOptions"
                      :key="c"
                      class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors flex items-center gap-2"
                      :class="entry.color === c
                        ? 'text-primary-400 bg-primary-500/10'
                        : 'text-gray-300 hover:bg-surface-800'"
                      @click="handleSetColor(c)"
                    >
                      <span class="inline-flex w-3 h-3 rounded-full" :class="swatchBg(c)" />
                      {{ colorLabel(c) }}
                    </button>
                    <button
                      class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors flex items-center gap-2"
                      :class="!entry.color
                        ? 'text-primary-400 bg-primary-500/10'
                        : 'text-gray-300 hover:bg-surface-800'"
                      @click="handleSetColor(null)"
                    >
                      <span class="inline-flex w-3 h-3 rounded-full border border-surface-600" />
                      No color
                    </button>
                  </div>
                  <button
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-gray-300 hover:bg-surface-800 transition-colors flex items-center gap-2"
                    @click="handleOpenInTranslator"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0 0 14.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
                    </svg>
                    Open in Translator
                  </button>
                  <button
                    v-if="isInGroup"
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-gray-300 hover:bg-surface-800 transition-colors flex items-center gap-2"
                    @click="handleRemoveFromGroup"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                    Remove from group
                  </button>
                  <button
                    class="text-left px-3 py-1.5 text-xs whitespace-nowrap text-red-400 hover:bg-red-500/10 transition-colors flex items-center gap-2"
                    @click="handleDelete"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
                      <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                    </svg>
                    Delete
                  </button>
                </div>
              </div>
            </template>
          </div>
        </div>

        <!-- Secondary row: lang pair OR translation swap in place; buttons always on right -->
        <div class="flex items-start gap-2 min-w-0">
          <p v-if="!hintVisible" class="text-xs text-gray-500 flex-1 min-w-0">
            {{ entry.source_lang }} → {{ entry.target_lang }}
            <span v-if="entry.provider_abbrev" class="ml-1 text-gray-600 opacity-0 group-hover/provider:opacity-100 transition-opacity">· {{ entry.provider_abbrev }}</span>
          </p>
          <p v-else class="flex-1 min-w-0 text-gray-400 text-sm self-center">{{ entry.target_text }}</p>
          <div class="flex items-center gap-1 shrink-0">
            <AudioButton
              v-if="hintVisible"
              :text="entry.target_text"
              :lang="entry.target_lang"
              size="sm"
              title="Pronounce translation"
            />
            <template v-if="!isCompact">
              <button
                :title="expandedInfo ? 'Hide details' : 'Details'"
                :class="[
                  'inline-flex items-center justify-center w-7 h-7 rounded-full transition-colors',
                  expandedInfo
                    ? 'text-primary-400 bg-primary-500/10'
                    : 'text-gray-500 hover:text-primary-400 hover:bg-primary-500/10'
                ]"
                @click="toggleExpandedInfo"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
                </svg>
              </button>
            </template>
          </div>
        </div>

        <!-- Notes display -->
        <p v-if="entry.notes" class="mt-1 text-xs text-gray-500 italic">{{ entry.notes }}</p>

        <!--
          Group badge: shown only in the "All" view (no group filter active),
          so a click here unambiguously means "switch to this group's filter".
          The trailing × button keeps its existing meaning (ungroup the entry).
        -->
        <div v-if="groupName" class="mt-1 flex items-center gap-2 group/badge">
          <button
            type="button"
            class="flex items-center gap-1 flex-1 min-w-0 text-left transition-colors hover:text-primary-400"
            :title="`Filter by group: ${groupName}`"
            @click.stop="handleFilterByGroup"
          >
            <span class="w-1.5 h-1.5 rounded-full bg-primary-500/50 shrink-0" />
            <span class="text-xs text-gray-600 truncate leading-tight group-hover/badge:text-primary-400/70">{{ groupName }}</span>
          </button>
          <button
            class="opacity-0 group-hover/badge:opacity-100 inline-flex items-center justify-center w-5 h-5 rounded-full shrink-0 text-gray-500 hover:text-red-400 hover:bg-red-500/10 transition-opacity -mr-1"
            @click.stop="$emit('ungroup', entry.id)"
            title="Remove from group"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3" viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>

      </template>
    </div>

    <!--
      Lifted overlay: absolute, anchored to the outer wrapper.
      top: 100% = bottom of the grid cell (wrapper stretches to row height),
      so this always starts exactly at the grid row's lower edge — overlapping
      the next row without displacing anything in the current row.
      left/right: 0 aligns with the card's outer border edges.
      No top border — the card's bottom border acts as the visual divider.
    -->
    <div
      v-if="expandedInfo && !editing"
      ref="overlayRef"
      :data-entry-id="entry.id"
      class="absolute left-0 right-0 top-full bg-surface-800 border-l border-r border-b border-surface-700 rounded-b-2xl p-3"
      :class="[
        isDragTarget ? 'ring-2 ring-primary-500/50' : '',
      ]"
      @animationend.self="onFlashEnd"
      :style="{ overflowAnchor: 'none' }"
    >
      <div class="flex items-center border-b border-surface-700 mb-3">
        <button
          @click="activeTab = 'definition'"
          :class="[
            'px-3 py-1.5 text-xs font-medium transition-colors border-b-2 -mb-px',
            activeTab === 'definition'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          ]"
        >Definition</button>
        <button
          @click="activeTab = 'context'"
          :class="[
            'px-3 py-1.5 text-xs font-medium transition-colors border-b-2 -mb-px',
            activeTab === 'context'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          ]"
        >Context</button>
        <button
          @click="activeTab = 'lexical'"
          :class="[
            'px-3 py-1.5 text-xs font-medium transition-colors border-b-2 -mb-px',
            activeTab === 'lexical'
              ? 'border-primary-500 text-primary-400'
              : 'border-transparent text-gray-500 hover:text-gray-300'
          ]"
        >Lexical</button>
        <button
          title="Close details"
          class="ml-auto inline-flex items-center justify-center w-6 h-6 rounded-full text-gray-500 hover:text-gray-300 hover:bg-surface-700 transition-colors"
          @click="toggleExpandedInfo"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>
      <DefinitionPanel
        v-if="activeTab === 'definition'"
        :word="entry.source_text"
        :lang="entry.source_lang"
        :compact="true"
      :initial-provider-code="savedDefProvider"
        @provider-changed="onDefProviderChanged"
      />
      <ContextExamples
        v-else-if="activeTab === 'context'"
        :text="entry.source_text"
        :source-lang="entry.source_lang"
        :target-lang="entry.target_lang"
        :compact="true"
        :initial-provider-code="savedCtxProvider"
        @provider-changed="onCtxProviderChanged"
      />
      <LexicalPanel
        v-else
        :word="entry.source_text"
        :source-lang="entry.source_lang"
        :target-lang="entry.target_lang"
        :compact="true"
        :initial-provider-code="savedLexProvider"
        @provider-changed="onLexProviderChanged"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onBeforeUnmount, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import AudioButton from './AudioButton.vue'
import DefinitionPanel from './DefinitionPanel.vue'
import ContextExamples from './ContextExamples.vue'
import LexicalPanel from './LexicalPanel.vue'
import { useTranslatorStore } from '@/stores/translator'
import { useWordbookUiStore } from '@/stores/wordbookUi'
import { useSettingsStore } from '@/stores/settings'
import { translateApi } from '@/api/translate'
import {
  ENTRY_COLORS,
  ENTRY_COLOR_CARD_BG,
  ENTRY_COLOR_LABEL,
  ENTRY_COLOR_SWATCH_BG,
  isEntryColor,
  type EntryColor,
} from '@/utils/entryColors'
import type { ProviderItem, WordbookEntry } from '@/types'

const props = defineProps<{ entry: WordbookEntry; groupName?: string; isDragTarget?: boolean }>()
const emit = defineEmits<{
  (e: 'delete', id: number): void
  (e: 'update', id: number, data: { source_text?: string; target_text?: string; notes?: string; provider_code?: string | null; color?: string | null }): void
  (e: 'ungroup', id: number): void
  (e: 'filter-group', groupId: number): void
}>()

const router = useRouter()
const translatorStore = useTranslatorStore()
const uiStore = useWordbookUiStore()
const settingsStore = useSettingsStore()

// ── Per-entry lexical provider persistence ────────────────────────────
const savedDefProvider = computed(() => uiStore.getProvider(props.entry.id, 'def'))
const savedCtxProvider = computed(() => uiStore.getProvider(props.entry.id, 'ctx'))
const savedLexProvider = computed(() => uiStore.getProvider(props.entry.id, 'lex'))

function onDefProviderChanged(code: string | null) {
  uiStore.setProvider(props.entry.id, 'def', code)
}
function onCtxProviderChanged(code: string | null) {
  uiStore.setProvider(props.entry.id, 'ctx', code)
}
function onLexProviderChanged(code: string | null) {
  uiStore.setProvider(props.entry.id, 'lex', code)
}

const activeTab = computed({
  get: () => (uiStore.getState(props.entry.id).detailsTab ?? 'definition') as 'definition' | 'context' | 'lexical',
  set: (v: 'definition' | 'context' | 'lexical') => uiStore.setState(props.entry.id, { detailsTab: v }),
})

const hintVisible = computed({
  get: () => uiStore.getReactive(props.entry.id, 'hintVisible'),
  set: (v) => uiStore.setState(props.entry.id, { hintVisible: v }),
})


const expandedInfo = computed(
  () => uiStore.activeCardId === props.entry.id && uiStore.activeCardMode === 'details',
)

const editing = computed(
  () => uiStore.activeCardId === props.entry.id && uiStore.activeCardMode === 'editing',
)

const cardRef = ref<HTMLElement | null>(null)
const overlayRef = ref<HTMLElement | null>(null)

// Restart the flash animation on whichever card elements exist. Uses a
// synchronous reflow (void el.offsetWidth) instead of an async rAF so
// rapid successive clicks trigger an immediate re-highlight with no gap.
watch(
  () => uiStore.highlightId === props.entry.id ? uiStore.highlightSeq : 0,
  (token) => {
    if (!token) return
    for (const el of [cardRef.value, overlayRef.value]) {
      if (!el) continue
      el.classList.remove('wordbook-flash')
      void el.offsetWidth
      el.classList.add('wordbook-flash')
    }
  },
)

// Called when the flash animation ends naturally. Removes the class and
// signals the store to clear highlightId so the sidebar indicator turns off.
function onFlashEnd(event: AnimationEvent) {
  const el = event.currentTarget as HTMLElement
  el.classList.remove('wordbook-flash')
  if (uiStore.highlightId === props.entry.id) uiStore.clearHighlight()
}

const isCompact = computed(
  () => uiStore.density === 'compact' && !editing.value && !expandedInfo.value,
)

const isInGroup = computed(() => props.entry.group != null)

// ── Color tag ─────────────────────────────────────────────────────────
const colorOptions = ENTRY_COLORS
const swatchBg = (c: EntryColor) => ENTRY_COLOR_SWATCH_BG[c]
const colorLabel = (c: EntryColor) => ENTRY_COLOR_LABEL[c]

const cardBgClass = computed(() =>
  isEntryColor(props.entry.color) ? ENTRY_COLOR_CARD_BG[props.entry.color] : 'bg-surface-900',
)

const editSource = ref('')
const editTarget = ref('')
const editNotes = ref('')
const editProviderCode = ref<string | null>(null)
const editProviders = ref<ProviderItem[]>([])
const retranslating = ref(false)
const showProviderPopup = ref(false)

const showActionsMenu = computed({
  get: () => uiStore.activeMenuId === props.entry.id,
  set: (v: boolean) => { uiStore.activeMenuId = v ? props.entry.id : null },
})

const usableEditProviders = computed(() => editProviders.value.filter(p => p.enabled && p.available))

// Providers rendered in the popup: enabled ones + the entry's saved provider
// even if it is now disabled/unavailable (shown as non-selectable "used before").
const visibleEditProviders = computed(() =>
  editProviders.value.filter(p => p.enabled || p.code === editProviderCode.value)
)

/**
 * True when a specific provider is selected and it is disabled or unavailable.
 * While providers haven't loaded yet (list empty) we treat any saved code as
 * still usable so the button stays enabled during the async fetch.
 */
const selectedProviderUnusable = computed(() => {
  if (!editProviderCode.value || editProviders.value.length === 0) return false
  const found = editProviders.value.find(p => p.code === editProviderCode.value)
  if (!found) return false  // unknown code — let the server decide
  return !found.enabled || !found.available
})
const providerPopupRef = ref<HTMLElement | null>(null)
const actionsContainerRef = ref<HTMLElement | null>(null)
// Color submenu inside the actions popup. Local to this card.
const showColorSubmenu = ref(false)
// Which side the color submenu opens on. Recomputed each time the user opens
// it so a window resize / side-panel toggle between openings is reflected.
const submenuPlacement = ref<'left' | 'right'>('right')
// Approximate width of the rendered submenu plus its 4px gap. Used to decide
// whether the right side has enough room before the submenu would clip the
// viewport. Tuned to fit the longest label ("No color") at the current font.
const SUBMENU_RIGHT_RESERVE_PX = 148

function toggleColorSubmenu() {
  if (!showColorSubmenu.value) {
    const rect = actionsContainerRef.value?.getBoundingClientRect()
    submenuPlacement.value =
      rect && rect.right + SUBMENU_RIGHT_RESERVE_PX <= window.innerWidth
        ? 'right'
        : 'left'
  }
  showColorSubmenu.value = !showColorSubmenu.value
}

// Vertical placement of the actions popup. Flipped to 'above' when the
// entry's trigger button is near the bottom of the viewport so the menu
// items aren't pushed off-screen.
const actionsMenuPlacement = ref<'below' | 'above'>('below')
// Approximate height in pixels of the fully-expanded actions popup
// (Edit → Color → Open in Translator → [Remove from group] → Delete + py).
// Sized to the worst case (in-group entry shows all 5 rows). When less
// than this fits below the trigger, the popup flips above.
const ACTIONS_MENU_RESERVE_PX = 200

function recomputeActionsMenuPlacement() {
  const rect = actionsContainerRef.value?.getBoundingClientRect()
  if (!rect) {
    actionsMenuPlacement.value = 'below'
    return
  }
  const spaceBelow = window.innerHeight - rect.bottom
  const spaceAbove = rect.top
  if (spaceBelow < ACTIONS_MENU_RESERVE_PX && spaceAbove > spaceBelow) {
    actionsMenuPlacement.value = 'above'
  } else {
    actionsMenuPlacement.value = 'below'
  }
}

function closeProviderPopup() { showProviderPopup.value = false }

/**
 * Closes the actions menu (and its color submenu) when a click lands
 * anywhere outside the trigger+popup container.  Registered with
 * `capture: true` so it fires before child handlers — this lets us close
 * the menu even when the click target uses `@click.stop` (e.g. the
 * AudioButton or the color-filter button in the top bar).  Clicks inside
 * the container leave the menu open so the trigger button can still
 * toggle and the popup items can still receive their click.
 */
function onActionsOutsideClick(e: MouseEvent) {
  const target = e.target as Node | null
  if (!target) return
  if (actionsContainerRef.value?.contains(target)) return
  showActionsMenu.value = false
}

watch(showProviderPopup, async (open) => {
  if (open) {
    document.addEventListener('click', closeProviderPopup)
    await nextTick()
    if (editProviderCode.value !== null) {
      const btn = providerPopupRef.value?.querySelector(
        `[data-code="${editProviderCode.value}"]`,
      ) as HTMLElement | null
      btn?.focus()
    } else {
      // Blur anything the browser may have auto-focused inside the popup
      const active = document.activeElement
      if (active && providerPopupRef.value?.contains(active)) {
        ;(active as HTMLElement).blur()
      }
    }
  } else {
    document.removeEventListener('click', closeProviderPopup)
  }
})

watch(showActionsMenu, (open) => {
  if (open) {
    // Recompute placement at the moment the popup opens so a recent scroll
    // or window resize is reflected.
    recomputeActionsMenuPlacement()
    document.addEventListener('click', onActionsOutsideClick, true)
  } else {
    document.removeEventListener('click', onActionsOutsideClick, true)
    // Always collapse the color submenu when the parent menu closes.
    showColorSubmenu.value = false
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('click', closeProviderPopup)
  document.removeEventListener('click', onActionsOutsideClick, true)
  stopDetailsResizeObserver()
})

watch(() => settingsStore.saveCount, async (count) => {
  if (count === 0 || !editing.value) return
  try {
    editProviders.value = (await translateApi.getProviders(props.entry.source_lang, props.entry.target_lang))
      .sort((a, b) => a.position - b.position)
  } catch {
    // non-critical
  }
})

function toggleExpandedInfo() {
  uiStore.toggleDetails(props.entry.id)
}

// Padding below the viewport's top edge that the entry's top must keep
// when the page auto-scrolls on details-panel open. Matches the spec's
// "some margin below that screen edge" requirement (#6).
const WORDBOOK_DETAILS_TOP_MARGIN_PX = 12
const entryRootRef = ref<HTMLElement | null>(null)

/**
 * After the details overlay opens, scroll the page so more of the
 * panel becomes visible. Bounded so that the entry's top never crosses
 * above `top + WORDBOOK_DETAILS_TOP_MARGIN_PX` — in other words, we
 * never scroll "too far" and tuck the entry's source text out of view.
 *
 * The page itself is already long enough to scroll into (the wordbook
 * grid + its surrounding chrome), so we only need to drive
 * `window.scrollBy`; no body-padding tricks required.
 */
function ensureDetailsVisible() {
  if (!expandedInfo.value) return
  const wrapper = entryRootRef.value
  if (!wrapper) return
  const wrapperRect = wrapper.getBoundingClientRect()
  const overlay = wrapper.querySelector(
    `[data-entry-id="${props.entry.id}"]`,
  ) as HTMLElement | null
  if (!overlay) return
  const overlayRect = overlay.getBoundingClientRect()
  const overlayBottom = overlayRect.bottom
  const viewportHeight = window.innerHeight
  if (overlayBottom <= viewportHeight) return  // already fully visible
  const overflow = overlayBottom - viewportHeight
  // How much we can scroll without pushing the entry's top above the
  // sticky header + top-margin band. Negative values clamp to 0 (no scroll possible).
  const stickyHeader = document.querySelector('header') as HTMLElement | null
  const stickyHeaderHeight = stickyHeader?.getBoundingClientRect().height ?? 0
  const headroom = Math.max(0, wrapperRect.top - stickyHeaderHeight - WORDBOOK_DETAILS_TOP_MARGIN_PX)
  const delta = Math.min(overflow, headroom)
  if (delta <= 0) return
  window.scrollBy({ top: delta, behavior: 'smooth' })
}

// The DefinitionPanel / ContextExamples / LexicalPanel children fetch
// asynchronously, so the overlay's height after the first paint reflects
// only their loading skeleton. Observe the overlay for a brief window
// after open so the auto-scroll catches up once content arrives.  The
// observer is torn down well before the user is likely to switch tabs,
// so a later tab change doesn't yank the page around again.
const DETAILS_RESIZE_OBSERVE_MS = 1500
let detailsResizeObserver: ResizeObserver | null = null
let detailsResizeTimer: ReturnType<typeof setTimeout> | null = null

function stopDetailsResizeObserver() {
  detailsResizeObserver?.disconnect()
  detailsResizeObserver = null
  if (detailsResizeTimer !== null) {
    clearTimeout(detailsResizeTimer)
    detailsResizeTimer = null
  }
}

/**
 * Scroll the page so the open details overlay is visible (bounded by the
 * top-margin), then watch the overlay for async height changes for a short
 * window so newly-arrived content (lazy fetches in the active tab) is also
 * accounted for. Used both when the overlay first opens and when the user
 * switches tabs inside it.
 */
async function startDetailsAutoScroll() {
  await nextTick()
  await new Promise<void>((r) => requestAnimationFrame(() => r()))
  ensureDetailsVisible()
  const overlay = entryRootRef.value?.querySelector(
    `[data-entry-id="${props.entry.id}"]`,
  ) as HTMLElement | null
  if (overlay && typeof ResizeObserver !== 'undefined') {
    stopDetailsResizeObserver()
    detailsResizeObserver = new ResizeObserver(() => ensureDetailsVisible())
    detailsResizeObserver.observe(overlay)
    detailsResizeTimer = setTimeout(stopDetailsResizeObserver, DETAILS_RESIZE_OBSERVE_MS)
  }
}

watch(expandedInfo, (open) => {
  if (!open) {
    stopDetailsResizeObserver()
    return
  }
  startDetailsAutoScroll()
})

// Switching tabs inside an open details panel can grow the overlay
// (def/ctx/lex have different content heights and async fetches), so
// re-run the same scroll-into-view logic to keep more of the panel
// visible without tucking the entry's source text out of view.
watch(activeTab, () => {
  if (!expandedInfo.value) return
  startDetailsAutoScroll()
})

async function startEdit() {
  editSource.value = props.entry.source_text
  editTarget.value = props.entry.target_text
  editNotes.value = props.entry.notes ?? ''
  editProviderCode.value = props.entry.provider_code ?? null
  editProviders.value = []
  showProviderPopup.value = false
  uiStore.openEditing(props.entry.id)
  try {
    editProviders.value = (await translateApi.getProviders(props.entry.source_lang, props.entry.target_lang))
      .sort((a, b) => a.position - b.position)
  } catch {
    // non-critical — popup list won't populate
  }
}

function selectEditProvider(p: ProviderItem) {
  if (!p.enabled || !p.available) return
  editProviderCode.value = p.code
  showProviderPopup.value = false
  retranslateEdit()
}

function onEditTargetInput() {
  editProviderCode.value = null
}

function cancelEdit() {
  showProviderPopup.value = false
  uiStore.closeActive()
}

async function retranslateEdit() {
  if (!editSource.value.trim() || retranslating.value) return
  const code = editProviderCode.value
  if (!code) return  // can't translate without an explicit provider
  retranslating.value = true
  try {
    const res = await translateApi.translate(
      editSource.value.trim(),
      props.entry.source_lang,
      props.entry.target_lang,
      code,
    )
    editTarget.value = res.translated_text
  } finally {
    retranslating.value = false
  }
}

function openInTranslator() {
  translatorStore.translateWord(
    props.entry.source_text,
    props.entry.source_lang,
    props.entry.target_lang,
  )
  router.push('/translator')
}

function saveEdit() {
  emit('update', props.entry.id, {
    source_text: editSource.value,
    target_text: editTarget.value,
    notes: editNotes.value,
    provider_code: editProviderCode.value,
  })
  uiStore.closeActive()
}

function handleEdit() {
  showActionsMenu.value = false
  startEdit()
}

function handleOpenInTranslator() {
  showActionsMenu.value = false
  openInTranslator()
}

function handleDelete() {
  showActionsMenu.value = false
  emit('delete', props.entry.id)
}

function handleRemoveFromGroup() {
  showActionsMenu.value = false
  emit('ungroup', props.entry.id)
}

function handleSetColor(color: EntryColor | null) {
  showActionsMenu.value = false
  // Avoid pointless backend round-trip if the user picks the active color again
  if ((props.entry.color ?? null) === color) return
  emit('update', props.entry.id, { color })
}

/**
 * Activate the wordbook view's group filter for the entry's own group.
 * Only invoked while the badge is visible — i.e. the All view is active
 * — so this is always a meaningful state transition (no group is currently
 * selected, the entry obviously belongs to one). The actual store mutation
 * lives in `WordbookView.vue` to keep this component free of view-level
 * concerns.
 */
function handleFilterByGroup() {
  const groupId = props.entry.group?.id
  if (groupId == null) return
  emit('filter-group', groupId)
}
</script>
