<template>
  <!--
    The negative top margin in `with-controls` mode reclaims the empty
    space above the title that is normally reserved for the absolutely
    positioned `X entries` badge above the right controls. In this mode
    the controls (and the badge) move down to row 2, so the slot above
    the title is no longer needed.
  -->
  <div
    class="space-y-3"
    :class="headerLayout === 'with-controls' ? '-mt-6' : ''"
  >
    <!-- Header row: title + tab bar + right controls -->
    <!--
      Layout switches between three modes via JS measurement (see
      `checkGroupsFit` in script):
        - inline:        [title] [groups (flex-1)] [controls]
        - with-controls: row 1 [title (w-full)] /
                         row 2 [groups (flex-1)] [controls]
        - standalone:    row 1 [title] [controls (ml-auto)] /
                         row 2 [groups (basis-full)]
      The `w-full` on the title in `with-controls` mode is what forces the
      flex-wrap break: a 100%-wide item leaves no room for its siblings,
      so groups + controls wrap together to the next row.
    -->
    <div ref="headerRowEl" class="flex items-center gap-3 flex-wrap">

      <h1
        ref="titleEl"
        class="text-xl font-bold text-gray-100"
        :class="headerLayout === 'with-controls' ? 'w-full' : 'shrink-0'"
      >Wordbook</h1>

      <!-- Word group tabs -->
      <div
        ref="groupsEl"
        class="flex items-center gap-1 flex-wrap"
        :class="headerLayout === 'standalone' ? 'order-1 basis-full' : 'flex-1 min-w-0'"
      >
        <!-- Each group tab -->
        <div
          v-for="tab in groupsStore.tabs"
          :key="tab.id"
          :data-tab-id="tab.id"
          class="relative flex items-center gap-0 rounded-full border transition-colors select-none"
          :class="[
            uiStore.activeGroupId === tab.id
              ? 'border-primary-500/50 bg-primary-500/10'
              : 'border-surface-700',
            draggedTabId === tab.id
              ? 'opacity-40 cursor-grabbing'
              : longPressReadyTabId === tab.id
                ? 'cursor-text'
                : 'cursor-default',
            dragOverTabId === tab.id ? 'ring-2 ring-primary-500/50' : '',
          ]"
          style="touch-action: none"
          @pointerdown="onTabPointerDown($event, tab.id)"
          @pointermove="onTabPointerMove"
          @pointerup="onTabPointerUp"
          @pointercancel="onTabPointerCancel"
        >
          <!-- Name or inline edit input -->
          <template v-if="editingTabId !== tab.id">
            <span
              class="px-3 py-1 text-xs transition-colors rounded-l-full"
              :class="uiStore.activeGroupId === tab.id ? 'text-primary-300' : 'text-gray-400'"
            >{{ tab.name }}</span>
            <button
              data-delete-tab
              class="pr-2 pl-1 py-1 text-gray-600 hover:text-red-400 transition-colors rounded-r-full text-xs leading-none"
              title="Delete group"
            >×</button>
          </template>
          <template v-else>
            <!-- Sizer: keeps the pill width as the user types (matches view-mode content) -->
            <span class="px-3 py-1 text-xs invisible pointer-events-none" aria-hidden="true">{{ tabEditName }}</span>
            <span class="pr-2 pl-1 py-1 text-xs invisible pointer-events-none" aria-hidden="true">×</span>
            <input
              v-focus-select
              type="text"
              v-model="tabEditName"
              :maxlength="GROUP_NAME_MAX_LEN"
              class="absolute inset-0 px-3 py-1 text-xs bg-transparent text-gray-200 outline-none rounded-full"
              @blur="saveTabEdit(tab.id)"
              @keydown.enter.prevent="saveTabEdit(tab.id)"
              @keydown.escape.prevent="cancelTabEdit"
              @pointerdown.stop
            />
          </template>
        </div>

        <!-- Add group button -->
        <button
          class="px-2.5 py-1 text-xs text-gray-600 hover:text-gray-300 border border-dashed border-surface-700 hover:border-surface-500 rounded-full transition-colors"
          @click="addNewTab"
          title="Add word group"
        >+ group</button>
      </div>

      <!-- Right controls: translation toggle + lang filter + count + density -->
      <div
        ref="controlsEl"
        class="flex items-center gap-2 shrink-0 flex-wrap justify-end"
        :class="headerLayout === 'standalone' ? 'ml-auto' : ''"
      >

        <!-- Language filter chips + Translation toggle + Density toggler -->
        <div class="relative flex items-center gap-2">
          <span class="absolute bottom-full right-0 mb-1.5 text-xs text-gray-500 whitespace-nowrap text-center">{{ filteredEntries.length }} entries</span>

          <!-- Language filter chips (only when multiple source langs present) -->
          <div v-if="availableLangs.length > 1" class="flex items-center gap-1">
            <button
              v-for="lang in availableLangs"
              :key="lang"
              @click="toggleLang(lang)"
              :class="[
                'inline-flex items-center px-2 h-5 rounded-md text-xs leading-none transition-colors border',
                uiStore.activeLangs.length === 0
                  ? 'text-gray-500 border-surface-700 hover:text-gray-300 hover:border-surface-500'
                  : uiStore.activeLangs.includes(lang)
                    ? 'bg-primary-500/20 text-primary-400 border-primary-500/40'
                    : 'text-gray-700 border-surface-800 hover:text-gray-500',
              ]"
            ><span class="block -translate-y-px">{{ lang.replace('→', ' → ') }}</span></button>
          </div>

          <!-- Filter by color (icon + popup) -->
          <div v-if="availableColors.length > 0" class="relative" ref="colorFilterContainerRef">
            <button
              class="p-1.5 transition-colors rounded-lg border border-surface-700"
              :class="uiStore.activeColors.length > 0 ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
              @click.stop="showColorFilter = !showColorFilter"
              :title="uiStore.activeColors.length > 0 ? 'Color filter active' : 'Filter by color'"
            >
              <!-- Three overlapping circles — evokes a color palette / filter -->
              <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.3">
                <circle cx="6"  cy="6"  r="3.2"/>
                <circle cx="10" cy="6"  r="3.2"/>
                <circle cx="8"  cy="10" r="3.2"/>
              </svg>
            </button>
            <div
              v-if="showColorFilter"
              class="absolute top-full right-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[140px]"
              @click.stop
            >
              <button
                v-for="opt in availableColors"
                :key="opt"
                class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors flex items-center gap-2"
                :class="uiStore.activeColors.includes(opt)
                  ? 'text-primary-400 bg-primary-500/10'
                  : 'text-gray-300 hover:bg-surface-800'"
                @click="toggleColor(opt)"
              >
                <span
                  v-if="opt === 'none'"
                  class="inline-flex w-3 h-3 rounded-full border border-surface-600"
                />
                <span
                  v-else
                  class="inline-flex w-3 h-3 rounded-full"
                  :class="colorSwatchBg(opt)"
                />
                {{ colorOptionLabel(opt) }}
              </button>
            </div>
          </div>

          <!-- Translation toggle (icon) -->
          <button
            v-if="store.entries.length > 0"
            class="p-1.5 transition-colors rounded-lg border border-surface-700"
            :class="anyHintVisible ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
            @click="toggleAllHints"
            :title="anyHintVisible ? 'Hide all translations' : 'Show all translations'"
          >
            <svg v-if="anyHintVisible" viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8s-2.5 4.5-6.5 4.5S1.5 8 1.5 8z"/>
              <circle cx="8" cy="8" r="2"/>
            </svg>
            <svg v-else viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 2l12 12M6.5 6.6a2 2 0 0 0 2.9 2.9M3.3 5.2C2.2 6.3 1.5 8 1.5 8s2.5 4.5 6.5 4.5c1 0 1.9-.3 2.7-.7M13.1 10.4c.9-1 1.4-2.4 1.4-2.4s-2.5-4.5-6.5-4.5c-.5 0-1 .1-1.4.2"/>
            </svg>
          </button>

          <!-- Batch delete filtered entries (icon) -->
          <button
            v-if="filteredEntries.length > 0"
            class="p-1.5 transition-colors rounded-lg border border-surface-700 text-gray-500 hover:text-red-400 hover:border-red-500/40"
            @click="handleBatchDelete"
            :title="`Delete ${filteredEntries.length} filtered ${filteredEntries.length === 1 ? 'entry' : 'entries'}`"
          >
            <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2.5 4.5h11"/>
              <path d="M6 4.5V3a1 1 0 0 1 1-1h2a1 1 0 0 1 1 1v1.5"/>
              <path d="M4 4.5l.7 8.8a1 1 0 0 0 1 .9h4.6a1 1 0 0 0 1-.9l.7-8.8"/>
              <path d="M6.5 7.5v4"/>
              <path d="M9.5 7.5v4"/>
            </svg>
          </button>

          <!-- Side word-list panel toggle (icon) -->
          <button
            v-if="store.entries.length > 0"
            class="p-1.5 transition-colors rounded-lg border border-surface-700"
            :class="uiStore.sidePanelVisible ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
            @click="uiStore.sidePanelVisible = !uiStore.sidePanelVisible"
            :title="uiStore.sidePanelVisible ? 'Hide word list' : 'Show word list'"
          >
            <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/>
              <line x1="9.5" y1="2.5" x2="9.5" y2="13.5"/>
              <line x1="11" y1="5.5" x2="13" y2="5.5"/>
              <line x1="11" y1="8" x2="13" y2="8"/>
              <line x1="11" y1="10.5" x2="13" y2="10.5"/>
            </svg>
          </button>

          <!-- Density toggler -->
          <div class="flex items-center border border-surface-700 rounded-lg overflow-hidden">
          <button
            v-for="level in densityLevels"
            :key="level"
            @click="uiStore.density = level"
            :title="level.charAt(0).toUpperCase() + level.slice(1)"
            :class="[
              'p-1.5 transition-colors',
              uiStore.density === level
                ? 'text-primary-400 bg-primary-500/10'
                : 'text-gray-500 hover:text-gray-300',
            ]"
          >
            <!-- Compact: 5 thin columns -->
            <svg v-if="level === 'compact'" viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
              <rect x="0"   y="1" width="1.5" height="12" rx="0.4"/>
              <rect x="3"   y="1" width="1.5" height="12" rx="0.4"/>
              <rect x="6"   y="1" width="1.5" height="12" rx="0.4"/>
              <rect x="9"   y="1" width="1.5" height="12" rx="0.4"/>
              <rect x="12"  y="1" width="1.5" height="12" rx="0.4"/>
            </svg>
            <!-- Normal: 3 medium columns -->
            <svg v-else-if="level === 'normal'" viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
              <rect x="0"  y="1" width="3" height="12" rx="0.4"/>
              <rect x="5"  y="1" width="3" height="12" rx="0.4"/>
              <rect x="10" y="1" width="3" height="12" rx="0.4"/>
            </svg>
            <!-- Spacious: 2 wide columns -->
            <svg v-else viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
              <rect x="0" y="1" width="5.5" height="12" rx="0.4"/>
              <rect x="8" y="1" width="5.5" height="12" rx="0.4"/>
            </svg>
          </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Content row: main grid + optional right word-list panel -->
    <div class="flex gap-3 items-start">
      <div class="flex-1 min-w-0">
        <!-- Loading skeleton -->
        <div v-if="store.isLoading" class="grid gap-3" :style="gridStyle">
          <div v-for="i in 6" :key="i" class="h-16 bg-surface-800 rounded-2xl animate-pulse" />
        </div>

        <!-- Wordbook empty state -->
        <div v-else-if="!store.entries.length" class="py-16 text-center text-gray-500">
          <p class="text-lg mb-2">Your wordbook is empty.</p>
          <p class="text-sm">Translate something and click <strong>Save</strong> to add entries here.</p>
        </div>

        <!-- Filter empty state -->
        <div v-else-if="!filteredEntries.length" class="py-16 text-center text-gray-500">
          <p class="text-lg mb-2">No entries match the current filter.</p>
          <p class="text-sm">Clear a language, color or group filter to see more entries.</p>
        </div>

        <!-- Entry grid -->
        <div v-else class="grid gap-3" :style="gridStyle">
          <div
            v-for="entry in filteredEntries"
            :key="entry.id"
            :data-entry-id="entry.id"
            :draggable="!isEditing(entry.id)"
            @dragstart="onDragStart($event, entry.id)"
            @dragover.prevent="onCardDragOver(entry.id)"
            @dragleave="onCardDragLeave"
            @drop.prevent="onCardDrop(entry.id)"
            @dragend="onDragEnd"
            class="flex flex-col transition-opacity duration-150"
          >
            <WordbookEntry
              :entry="entry"
              :is-drag-target="dragOverId === entry.id && (draggedTabId !== null || (draggedId !== null && draggedId !== entry.id))"
              :group-name="uiStore.activeGroupId === null ? entryGroupNames[entry.id] : undefined"
              class="flex-1"
              @delete="handleDelete"
              @update="handleUpdate"
              @ungroup="handleUngroup"
              @filter-group="handleFilterByGroup"
            />
          </div>
        </div>
      </div>

      <!--
        Right-side vertical word-list panel.
        Alphabetical list of the currently filtered cards; clicking a word
        scrolls to + briefly highlights the corresponding card.
      -->
      <aside
        v-if="uiStore.sidePanelVisible && filteredEntries.length > 0"
        class="shrink-0 w-44 sm:w-56"
      >
        <div class="sticky top-20 card p-2 max-h-[calc(100vh-6rem)] overflow-y-auto">
          <ul class="space-y-0.5">
            <li v-for="entry in sortedPanelWords" :key="entry.id">
              <button
                class="w-full text-left px-2 py-1 text-xs rounded truncate transition-colors"
                :class="uiStore.highlightId === entry.id
                  ? 'text-primary-300 bg-primary-500/10'
                  : 'text-gray-300 hover:text-primary-300 hover:bg-surface-800'"
                :title="entry.source_text"
                @click="scrollToEntry(entry.id)"
              >{{ entry.source_text }}</button>
            </li>
          </ul>
        </div>
      </aside>
    </div>

    <!-- Delete entry confirmation dialog -->
    <ConfirmDialog
      v-model="showDeleteDialog"
      title="Delete Entry"
      message="Are you sure you want to delete this entry? This action cannot be undone."
      confirm-text="Delete"
      cancel-text="Cancel"
      variant="danger"
      @confirm="confirmDelete"
    />

    <!-- Delete group confirmation dialog -->
    <ConfirmDialog
      v-model="showDeleteTabDialog"
      title="Delete Group"
      message="Are you sure you want to delete this group? Entries in it will be unassigned but not deleted."
      confirm-text="Delete"
      cancel-text="Cancel"
      variant="danger"
      @confirm="confirmDeleteTab"
    />

    <!-- Batch delete confirmation dialog -->
    <ConfirmDialog
      v-model="showBatchDeleteDialog"
      title="Delete Entries"
      :message="batchDeleteMessage"
      confirm-text="Delete"
      cancel-text="Cancel"
      variant="danger"
      @confirm="confirmBatchDelete"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { useWordbookStore } from '@/stores/wordbook'
import { useWordbookUiStore, type DensityLevel } from '@/stores/wordbookUi'
import { useWordbookGroupsStore, type WordGroup } from '@/stores/wordbookGroups'
import WordbookEntry from '@/components/WordbookEntry.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/utils/error'
import {
  ENTRY_COLORS,
  ENTRY_COLOR_LABEL,
  ENTRY_COLOR_SWATCH_BG,
  isEntryColor,
  type EntryColor,
} from '@/utils/entryColors'

const store = useWordbookStore()
const toast = useToastStore()
const uiStore = useWordbookUiStore()
const groupsStore = useWordbookGroupsStore()

// ─── Density ─────────────────────────────────────────────────────────────────

const densityLevels: DensityLevel[] = ['compact', 'normal', 'spacious']

const DENSITY_MIN_WIDTH: Record<DensityLevel, string> = {
  compact: '160px',
  normal: '250px',
  spacious: '340px',
}

const gridStyle = computed(() => ({
  display: 'grid',
  gap: '0.75rem',
  gridTemplateColumns: `repeat(auto-fill, minmax(${DENSITY_MIN_WIDTH[uiStore.density]}, 1fr))`,
}))

// ─── Language filter ──────────────────────────────────────────────────────────

const availableLangs = computed(() => {
  const pairs = new Set(store.entries.map((e) => `${e.source_lang}→${e.target_lang}`))
  return [...pairs].sort()
})

function toggleLang(pair: string) {
  const current = [...uiStore.activeLangs]
  const idx = current.indexOf(pair)
  if (idx === -1) current.push(pair)
  else current.splice(idx, 1)
  uiStore.activeLangs = current
}

// Drop any active lang-pair filters whose chip has disappeared because the
// last entry of that pair was deleted. Without this the filter would stay
// "on" invisibly and silently hide unrelated entries.
watch(availableLangs, (pairs) => {
  if (uiStore.activeLangs.length === 0) return
  const valid = new Set(pairs)
  const cleaned = uiStore.activeLangs.filter((p) => valid.has(p))
  if (cleaned.length !== uiStore.activeLangs.length) {
    uiStore.activeLangs = cleaned
  }
})

// ─── Color filter ─────────────────────────────────────────────────────────

// 'none' is a sentinel that matches uncolored entries; real palette values
// follow in canonical order. Only options actually present in the entries
// list are shown so the popup stays terse.
const COLOR_FILTER_NONE = 'none'

const availableColors = computed<string[]>(() => {
  const present = new Set<string>()
  let hasUncolored = false
  for (const entry of store.entries) {
    if (isEntryColor(entry.color)) present.add(entry.color)
    else hasUncolored = true
  }
  const result = ENTRY_COLORS.filter((c) => present.has(c)) as string[]
  if (hasUncolored && result.length > 0) result.push(COLOR_FILTER_NONE)
  return result
})

function toggleColor(color: string) {
  const current = [...uiStore.activeColors]
  const idx = current.indexOf(color)
  if (idx === -1) current.push(color)
  else current.splice(idx, 1)
  uiStore.activeColors = current
}

function colorSwatchBg(color: string): string {
  return isEntryColor(color) ? ENTRY_COLOR_SWATCH_BG[color] : ''
}

function colorOptionLabel(color: string): string {
  return color === COLOR_FILTER_NONE ? 'No color' : ENTRY_COLOR_LABEL[color as EntryColor]
}

// Drop any active color filter whose option disappeared (last entry of that
// color removed / recolored). Same pattern as the lang-pair watcher above.
watch(availableColors, (options) => {
  if (uiStore.activeColors.length === 0) return
  const valid = new Set(options)
  const cleaned = uiStore.activeColors.filter((c) => valid.has(c))
  if (cleaned.length !== uiStore.activeColors.length) {
    uiStore.activeColors = cleaned
  }
})

const showColorFilter = ref(false)
const colorFilterContainerRef = ref<HTMLElement | null>(null)

/**
 * Capture-phase outside-click handler. Fires before any child `@click.stop`
 * (such as on the AudioButton or another card's actions menu trigger), so
 * the color-filter popup actually closes when the user interacts with any
 * other element on the page.
 */
function onColorFilterOutsideClick(e: MouseEvent) {
  const target = e.target as Node | null
  if (!target) return
  if (colorFilterContainerRef.value?.contains(target)) return
  showColorFilter.value = false
}
watch(showColorFilter, (open) => {
  if (open) document.addEventListener('click', onColorFilterOutsideClick, true)
  else document.removeEventListener('click', onColorFilterOutsideClick, true)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', onColorFilterOutsideClick, true)
})

// ─── Filtered entries ─────────────────────────────────────────────────────────

const filteredEntries = computed(() =>
  store.entries.filter((entry) => {
    const pair = `${entry.source_lang}→${entry.target_lang}`
    const langOk =
      uiStore.activeLangs.length === 0 || uiStore.activeLangs.includes(pair)
    const tabOk =
      uiStore.activeGroupId === null ||
      groupsStore.getAssignment(entry.id) === uiStore.activeGroupId
    const colorOk =
      uiStore.activeColors.length === 0 ||
      (isEntryColor(entry.color)
        ? uiStore.activeColors.includes(entry.color)
        : uiStore.activeColors.includes(COLOR_FILTER_NONE))
    return langOk && tabOk && colorOk
  }),
)

watch(filteredEntries, (entries) => {
  if (
    uiStore.activeCardId !== null &&
    uiStore.activeCardMode === 'editing' &&
    !entries.some((e) => e.id === uiStore.activeCardId)
  ) {
    uiStore.closeActive()
  }
})

// ─── Side panel (alphabetical word list) ─────────────────────────────────────

const sortedPanelWords = computed(() =>
  [...filteredEntries.value].sort((a, b) =>
    a.source_text.localeCompare(b.source_text, undefined, { sensitivity: 'base' }),
  ),
)

/**
 * Scroll the entry grid item with the given id into view and trigger a brief
 * visual flash. Called from the side panel and from the pending-highlight
 * handler (see below).
 *
 * Any currently-open details panel is collapsed first so the flash isn't
 * competing for attention with another card's expanded view. An in-progress
 * edit form is left alone to avoid dropping unsaved changes.
 */
async function scrollToEntry(id: number) {
  if (uiStore.activeCardId !== null && uiStore.activeCardMode === 'details') {
    uiStore.closeActive()
  }
  await nextTick()
  const el = document.querySelector(`[data-entry-id="${id}"]`) as HTMLElement | null
  if (el) {
    el.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  uiStore.highlightEntry(id)
}

/**
 * Consume a pending highlight request (set by TranslatorView before
 * navigating here) and run the scroll+flash action. Wrapped in nextTick so
 * any filter resets performed by requestShowEntry have already been applied
 * to the DOM before we attempt to find the card.
 */
async function handlePendingHighlight() {
  const id = uiStore.consumePendingHighlight()
  if (id === null) return
  // Ensure entries are loaded so the card is rendered.
  if (!store.isLoaded) await store.fetchEntries()
  await nextTick()
  await scrollToEntry(id)
}

const anyHintVisible = computed(() =>
  uiStore.showTranslations || store.entries.some((e) => uiStore.getReactive(e.id, 'hintVisible')),
)

function toggleAllHints() {
  uiStore.setAllHints(!anyHintVisible.value)
}

// ─── Group / tab CRUD ─────────────────────────────────────────────────────────

const vFocusSelect = {
  mounted: (el: HTMLElement) => { el.focus(); (el as HTMLInputElement).select?.() },
}

const editingTabId = ref<number | null>(null)
const tabEditName = ref('')

function selectTab(id: number) {
  if (editingTabId.value === id) return
  uiStore.activeGroupId = uiStore.activeGroupId === id ? null : id
}

function startTabEdit(tab: WordGroup) {
  editingTabId.value = tab.id
  tabEditName.value = tab.name
}

async function saveTabEdit(id: number) {
  if (editingTabId.value !== id) return
  const name = tabEditName.value.trim()
  editingTabId.value = null
  if (name) {
    try {
      await groupsStore.renameTab(id, name)
    } catch (e: unknown) {
      toast.error(extractErrorMessage(e, 'Failed to rename group'))
    }
  }
}

function cancelTabEdit() {
  editingTabId.value = null
}

async function addNewTab() {
  try {
    const tab = await groupsStore.addTab(`Group ${groupsStore.tabs.length + 1}`)
    startTabEdit(tab)
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to create group'))
  }
}

const showDeleteTabDialog = ref(false)
const pendingDeleteTabId = ref<number | null>(null)

function deleteTab(id: number) {
  pendingDeleteTabId.value = id
  showDeleteTabDialog.value = true
}

async function confirmDeleteTab() {
  if (pendingDeleteTabId.value === null) return
  const id = pendingDeleteTabId.value
  pendingDeleteTabId.value = null
  try {
    await groupsStore.deleteTab(id)
    if (uiStore.activeGroupId === id) uiStore.activeGroupId = null
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to delete group'))
  }
}

// ─── Header layout overflow detection ──────────────────────────────

// Maximum length for a word group name. Mirrors the Pydantic `Field(
// max_length=...)` constraint on `WordGroupCreate`/`WordGroupUpdate`.
const GROUP_NAME_MAX_LEN = 25

// Refs to the three header sections + the active layout mode. See the
// matching template comment for what each mode looks like visually.
//   - 'inline'        : everything fits on a single row.
//   - 'with-controls' : groups doesn't fit alongside title + controls,
//                       but groups + controls *do* fit on a row of
//                       their own — so both drop together below title.
//   - 'standalone'    : groups is wider than the row even without the
//                       title, so it takes a full-width row of its own
//                       and controls stays on row 1 with the title.
type HeaderLayout = 'inline' | 'with-controls' | 'standalone'
const headerRowEl = ref<HTMLElement | null>(null)
const titleEl = ref<HTMLElement | null>(null)
const groupsEl = ref<HTMLElement | null>(null)
const controlsEl = ref<HTMLElement | null>(null)
const headerLayout = ref<HeaderLayout>('inline')

// Pixel values matching the Tailwind gap classes on the corresponding
// containers (gap-3 outer, gap-1 between group pills).
const HEADER_OUTER_GAP_PX = 12
const HEADER_GROUPS_GAP_PX = 4

/**
 * Fractional width of `el` via `getBoundingClientRect`. We deliberately
 * avoid `offsetWidth` here because it is integer-rounded — over many
 * children that rounding can accumulate to a several-pixel error and
 * cause the wrap detector to falsely conclude that the group row "fits".
 */
function getWidth(el: HTMLElement): number {
  return el.getBoundingClientRect().width
}

/**
 * Natural rendered width of an element's contents, independent of its
 * own layout box.
 *
 * `getBoundingClientRect()` on the element itself reports the box width,
 * which equals the full container width when the element has been given
 * `w-full` (as the title does in `with-controls` mode). A `Range` over
 * the contents reports only the painted glyph extent — i.e. the natural
 * intrinsic width of the content — which is what the fit calculation
 * actually needs. Without this, `inlineTotal` would stay permanently
 * over the container width while in `with-controls` mode, blocking the
 * transition back to `inline` even after the groups shrink.
 */
function getContentWidth(el: HTMLElement): number {
  const range = document.createRange()
  range.selectNodeContents(el)
  return range.getBoundingClientRect().width
}

/**
 * Sum the rendered widths of `el`'s direct children plus the inter-child
 * gap. This gives the natural single-line width of a flex container with
 * `flex-wrap`, regardless of whether the children are currently wrapping.
 */
function sumChildrenWidth(el: HTMLElement, gapPx: number): number {
  const children = Array.from(el.children) as HTMLElement[]
  if (children.length === 0) return 0
  const sum = children.reduce((s, c) => s + getWidth(c), 0)
  return sum + Math.max(0, children.length - 1) * gapPx
}

// Slack required between the natural row width and the container width
// before we consider the row to fit inline. Without it, the row can
// nominally fit by a fraction of a pixel yet still trigger an internal
// `flex-wrap` inside the groups container — producing a multi-line tab
// row sandwiched between the title and the right controls. Sized to one
// inter-pill gap so the inline row always has at least one gap of
// breathing room before flipping to the wrapped layout.
const HEADER_FIT_SLACK_PX = HEADER_GROUPS_GAP_PX

/**
 * Pick the active header layout mode.
 *
 * Two natural-width totals are computed and compared (with a small
 * slack buffer) against the container width:
 *   - `inlineTotal`      = title + groups + controls + 2 outer gaps
 *                          — the width needed for the inline mode.
 *   - `groupsControlsRow` = groups + controls + 1 outer gap
 *                          — the width needed when title is on its own
 *                            row above and groups + controls share row 2.
 *
 * The widest fit wins:
 *   inlineTotal fits        → 'inline'
 *   else groupsControlsRow  → 'with-controls'
 *   else                    → 'standalone'
 *
 * `controls` is `shrink-0`, so its measured box width is already its
 * natural width. `title` gets `w-full` in `with-controls` mode (so its
 * box width is unreliable) — we use `getContentWidth` instead, which
 * reports just the rendered text extent. `groups` is laid out via
 * `flex-1` or `basis-full`, neither of which equals its natural width
 * — hence the explicit `sumChildrenWidth` for it.
 */
function checkGroupsFit() {
  const container = headerRowEl.value
  const title = titleEl.value
  const groups = groupsEl.value
  const controls = controlsEl.value
  if (!container || !title || !groups || !controls) return
  const containerWidth = getWidth(container)
  const titleWidth = getContentWidth(title)
  const groupsWidth = sumChildrenWidth(groups, HEADER_GROUPS_GAP_PX)
  const controlsWidth = getWidth(controls)
  const inlineTotal = titleWidth + groupsWidth + controlsWidth + 2 * HEADER_OUTER_GAP_PX
  const groupsControlsRow = groupsWidth + controlsWidth + HEADER_OUTER_GAP_PX
  const limit = containerWidth - HEADER_FIT_SLACK_PX

  if (inlineTotal <= limit) {
    headerLayout.value = 'inline'
  } else if (groupsControlsRow <= limit) {
    headerLayout.value = 'with-controls'
  } else {
    headerLayout.value = 'standalone'
  }
}

// ResizeObserver on the container catches window/parent resizes; the one
// on the controls catches changes to controls children sizes (e.g. lang
// chips appearing when entries with new lang pairs are added).
// A separate watcher below covers groups changes (rename / add / delete /
// inline edit), since the groups container's rendered width does not
// change with content while in inline `flex-1` mode.
let headerResizeObserver: ResizeObserver | null = null

watch(
  [() => groupsStore.tabs.map((t) => t.name).join('|'), tabEditName],
  () => { nextTick(() => checkGroupsFit()) },
)

// ─── Group name map for card badges ──────────────────────────────────

const entryGroupNames = computed(() => {
  const result: Record<number, string | undefined> = {}
  for (const entry of store.entries) {
    if (entry.group) result[entry.id] = entry.group.name
  }
  return result
})

async function handleUngroup(id: number) {
  try {
    await groupsStore.assignEntry(id, null)
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to remove from group'))
  }
}

/**
 * Switch the wordbook view's active group filter to the clicked entry's
 * own group. Emitted by the group badge inside `WordbookEntry.vue`, which
 * is only rendered when no group filter is active, so this is always a
 * "None → specific group" transition (never a toggle-off).
 */
function handleFilterByGroup(groupId: number) {
  uiStore.activeGroupId = groupId
}

// ─── Delete dialog ────────────────────────────────────────────────────────────

const showDeleteDialog = ref(false)
const pendingDeleteId = ref<number | null>(null)

function handleDelete(id: number) {
  pendingDeleteId.value = id
  showDeleteDialog.value = true
}

async function confirmDelete() {
  if (pendingDeleteId.value === null) return
  try {
    await store.deleteEntry(pendingDeleteId.value)
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to delete entry'))
  } finally {
    pendingDeleteId.value = null
  }
}

// ─── Batch delete dialog ──────────────────────────────────────────────────────

const showBatchDeleteDialog = ref(false)

const batchDeleteMessage = computed(() => {
  const n = filteredEntries.value.length
  return `Delete ${n} ${n === 1 ? 'entry' : 'entries'} matching the current filters? This action cannot be undone.`
})

function handleBatchDelete() {
  if (filteredEntries.value.length === 0) return
  showBatchDeleteDialog.value = true
}

async function confirmBatchDelete() {
  const ids = filteredEntries.value.map((e) => e.id)
  if (ids.length === 0) return
  try {
    await store.batchDeleteEntries(ids)
    uiStore.prune(store.entries.map((e) => e.id))
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to delete entries'))
  }
}

async function handleUpdate(
  id: number,
  data: { source_text?: string; target_text?: string; notes?: string; provider_code?: string | null; color?: string | null },
) {
  try {
    await store.updateEntry(id, data)
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to save changes'))
  }
}

// ─── Drag and drop ────────────────────────────────────────────────────────────

// Card reorder drag
const draggedId = ref<number | null>(null)
const cardDragSourceEl = ref<HTMLElement | null>(null)

// Tab → card group assignment drag, OR tab → tab reorder drag
// (custom pointer-based, single state machine for both)
const draggedTabId = ref<number | null>(null)
const dragOverId = ref<number | null>(null)
const dragOverTabId = ref<number | null>(null)

const DRAG_THRESHOLD = 5
const LONG_PRESS_DELAY = 500

const longPressReadyTabId = ref<number | null>(null)
let longPressTimerId: ReturnType<typeof setTimeout> | null = null

function clearLongPressTimer() {
  if (longPressTimerId !== null) { clearTimeout(longPressTimerId); longPressTimerId = null }
  longPressReadyTabId.value = null
}

// Drag ghost
let tabDragGhost: HTMLElement | null = null

function removeTabDragGhost() {
  tabDragGhost?.remove()
  tabDragGhost = null
}

interface TabInteraction {
  tabId: number
  startX: number
  startY: number
  startTime: number
  onDeleteButton: boolean
  isDragging: boolean
  sourceEl: HTMLElement
  grabOffsetX: number
  grabOffsetY: number
}
const tabInteraction = ref<TabInteraction | null>(null)

function isEditing(entryId: number): boolean {
  return uiStore.activeCardId === entryId && uiStore.activeCardMode === 'editing'
}

function onTabPointerDown(event: PointerEvent, tabId: number) {
  if (editingTabId.value === tabId) return
  if (editingTabId.value !== null) saveTabEdit(editingTabId.value)
  event.preventDefault()
  const sourceEl = event.currentTarget as HTMLElement
  sourceEl.setPointerCapture(event.pointerId)
  const rect = sourceEl.getBoundingClientRect()
  const onDeleteButton = !!(event.target as HTMLElement).closest('[data-delete-tab]')
  tabInteraction.value = {
    tabId, startX: event.clientX, startY: event.clientY, startTime: Date.now(),
    onDeleteButton, isDragging: false,
    sourceEl, grabOffsetX: event.clientX - rect.left, grabOffsetY: event.clientY - rect.top,
  }
  if (!onDeleteButton) {
    clearLongPressTimer()
    longPressTimerId = setTimeout(() => {
      longPressTimerId = null
      if (tabInteraction.value && !tabInteraction.value.isDragging) longPressReadyTabId.value = tabId
    }, LONG_PRESS_DELAY)
  }
}

function onTabPointerMove(event: PointerEvent) {
  const state = tabInteraction.value
  if (!state) return
  const dx = event.clientX - state.startX
  const dy = event.clientY - state.startY
  if (!state.isDragging && (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD)) {
    state.isDragging = true
    draggedTabId.value = state.tabId
    clearLongPressTimer()
    // Create ghost clone before Vue re-renders (opacity-40 not yet applied)
    const ghost = state.sourceEl.cloneNode(true) as HTMLElement
    const rect = state.sourceEl.getBoundingClientRect()
    ghost.style.cssText += `position:fixed;width:${rect.width}px;left:${event.clientX - state.grabOffsetX}px;top:${event.clientY - state.grabOffsetY}px;pointer-events:none;z-index:9999;opacity:0.85;margin:0;`
    document.body.appendChild(ghost)
    tabDragGhost = ghost
  }
  if (state.isDragging) {
    if (tabDragGhost) {
      tabDragGhost.style.left = `${event.clientX - state.grabOffsetX}px`
      tabDragGhost.style.top = `${event.clientY - state.grabOffsetY}px`
    }
    const under = document.elementsFromPoint(event.clientX, event.clientY)
    // Prefer another tab as drop target (→ reorder); fall back to a card
    // (→ assign-to-group). Hovering over self is a no-op.
    const tabEl = under.find(el => {
      const raw = el.getAttribute('data-tab-id')
      return raw !== null && Number(raw) !== state.tabId
    })
    if (tabEl) {
      dragOverTabId.value = Number(tabEl.getAttribute('data-tab-id'))
      dragOverId.value = null
    } else {
      dragOverTabId.value = null
      const cardEl = under.find(el => el.hasAttribute('data-entry-id'))
      dragOverId.value = cardEl ? Number(cardEl.getAttribute('data-entry-id')) : null
    }
  }
}

function onTabPointerUp(_event: PointerEvent) {
  clearLongPressTimer()
  removeTabDragGhost()
  const state = tabInteraction.value
  tabInteraction.value = null
  if (!state) return
  if (state.isDragging) {
    if (dragOverTabId.value !== null && dragOverTabId.value !== state.tabId) {
      // Reorder tabs: insert dragged tab at the target's position. Mirrors
      // the entry reorder logic in onCardDrop.
      const ids = groupsStore.tabs.map(t => t.id)
      const draggedIdx = ids.indexOf(state.tabId)
      const targetIdx = ids.indexOf(dragOverTabId.value)
      if (draggedIdx !== -1 && targetIdx !== -1) {
        const movingForward = draggedIdx < targetIdx
        const newIds = ids.filter(id => id !== state.tabId)
        const newTargetIdx = newIds.indexOf(dragOverTabId.value)
        newIds.splice(movingForward ? newTargetIdx + 1 : newTargetIdx, 0, state.tabId)
        groupsStore.reorderTabs(newIds)
      }
    } else if (dragOverId.value !== null) {
      groupsStore.assignEntry(dragOverId.value, state.tabId).catch((e: unknown) => {
        toast.error(extractErrorMessage(e, 'Failed to assign group'))
      })
    }
    draggedTabId.value = null
    dragOverId.value = null
    dragOverTabId.value = null
    return
  }
  const elapsed = Date.now() - state.startTime
  if (state.onDeleteButton) {
    deleteTab(state.tabId)
  } else if (elapsed < LONG_PRESS_DELAY) {
    selectTab(state.tabId)
  } else {
    const tab = groupsStore.tabs.find(t => t.id === state.tabId)
    if (tab) startTabEdit(tab)
  }
}

function onTabPointerCancel() {
  clearLongPressTimer()
  removeTabDragGhost()
  tabInteraction.value = null
  draggedTabId.value = null
  dragOverId.value = null
  dragOverTabId.value = null
}

// Card reorder drag (HTML5)
function onDragStart(event: DragEvent, entryId: number) {
  draggedId.value = entryId
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  cardDragSourceEl.value = event.currentTarget as HTMLElement
  cardDragSourceEl.value.style.opacity = '0.4'
}

function onCardDragOver(entryId: number) {
  if (!draggedId.value) return
  dragOverId.value = entryId
}

function onCardDragLeave() {
  dragOverId.value = null
}

function onCardDrop(targetEntryId: number) {
  const dragged = draggedId.value
  if (!dragged || dragged === targetEntryId) { onDragEnd(); return }

  const filteredIds = filteredEntries.value.map((e) => e.id)
  const movingForward = filteredIds.indexOf(dragged) < filteredIds.indexOf(targetEntryId)
  const newFiltered = filteredIds.filter((id) => id !== dragged)
  const targetIdx = newFiltered.indexOf(targetEntryId)
  newFiltered.splice(movingForward ? targetIdx + 1 : targetIdx, 0, dragged)

  const filteredSet = new Set(filteredIds)
  const allIds = store.entries.map((e) => e.id)
  let fi = 0
  const newOrder = allIds.map((id) => (filteredSet.has(id) ? newFiltered[fi++] : id))

  store.reorderEntries(newOrder)
  onDragEnd()
}

function onDragEnd() {
  if (cardDragSourceEl.value) {
    cardDragSourceEl.value.style.opacity = ''
    cardDragSourceEl.value = null
  }
  draggedId.value = null
  dragOverId.value = null
}

// ─── Lifecycle ────────────────────────────────────────────────────────────────
// True while this view is the active route. Used to prevent the
// pendingHighlightId watcher from consuming the ID before the kept-alive view
// has actually been activated and is ready to scroll.
const viewIsActive = ref(false)

onMounted(async () => {
  viewIsActive.value = true
  await Promise.all([store.fetchEntries(), groupsStore.fetchGroups()])
  uiStore.prune(store.entries.map((e) => e.id))
  await handlePendingHighlight()

  // Refs are assigned and initial data is loaded, so the first measurement
  // reflects the actual rendered content. Observe both the container (for
  // window/parent resizes) and the controls element (for visibility
  // changes of its children).
  if (typeof ResizeObserver !== 'undefined' && headerRowEl.value && controlsEl.value) {
    headerResizeObserver = new ResizeObserver(() => checkGroupsFit())
    headerResizeObserver.observe(headerRowEl.value)
    headerResizeObserver.observe(controlsEl.value)
  }
  await nextTick()
  checkGroupsFit()
})

onBeforeUnmount(() => {
  headerResizeObserver?.disconnect()
})

// Re-activated from <KeepAlive> when the user navigates back to this view
// (e.g. from TranslatorView via the “already in wordbook” checkmark).
onActivated(() => {
  viewIsActive.value = true
  handlePendingHighlight()
})

onDeactivated(() => {
  viewIsActive.value = false
})

// Defensive: if a pending highlight is set while the view is already active,
// react to it without waiting for the next activation. The active-view guard
// prevents the ID from being consumed during navigation before this view is
// ready to perform the scroll.
watch(
  () => uiStore.pendingHighlightId,
  (id) => { if (id !== null && viewIsActive.value) handlePendingHighlight() },
)
</script>
