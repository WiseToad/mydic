<template>
  <div class="flex-1 min-h-0 flex flex-col">
    <!-- Header: two fixed rows, does not scroll -->
    <div class="flex-none pt-3 pb-3">

      <!-- Row 1: Wordbook title · [lang popup button] · toolbar buttons -->
      <div ref="headerRow1El" class="flex items-center gap-2 overflow-visible">
        <h1 ref="titleEl" class="text-xl font-bold text-gray-100 shrink-0">Wordbook</h1>

        <!-- Search trigger button (hidden when search mode is active) -->
        <button
          v-if="!searchActive"
          class="p-1.5 transition-colors text-gray-500 hover:text-gray-300 shrink-0"
          title="Search wordbook"
          @click.stop="activateSearch"
        >
          <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="6.5" cy="6.5" r="4.5"/>
            <line x1="10" y1="10" x2="14" y2="14"/>
          </svg>
        </button>

        <!-- Flex spacer (hidden when search active; search input is flex-1 instead) -->
        <div v-if="!searchActive" class="flex-1 min-w-0" />

        <!-- Search input + dropdown (shown when search mode is active) -->
        <div
          v-if="searchActive"
          ref="searchContainerEl"
          class="relative"
          :style="searchToolbarHidden
            ? 'flex: 1 1 auto; min-width: 0'
            : `flex: 0 0 ${SEARCH_FIXED_WIDTH}px`"
          @click.stop
        >
          <!-- Search input row with embedded togglers -->
          <div class="flex items-center bg-surface-800 border border-surface-600 rounded-lg focus-within:border-primary-500/50">
            <input
              ref="searchInputEl"
              v-model="searchQuery"
              type="text"
              placeholder="Search…"
              autocomplete="off"
              spellcheck="false"
              class="flex-1 min-w-0 px-3 py-[3px] text-sm bg-transparent text-gray-200 placeholder-gray-600 focus:outline-none"
              @input="onSearchInput"
              @keydown="onSearchKeydown"
            />
            <!-- Clear search query button -->
            <button
              class="p-1.5 mr-0.5 transition-colors text-gray-500 hover:text-gray-300 shrink-0"
              title="Clear search"
              @click.stop="clearSearchQuery"
            >
              <svg viewBox="0 0 16 16" class="w-2.5 h-2.5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="3" y1="3" x2="13" y2="13"/>
                <line x1="13" y1="3" x2="3" y2="13"/>
              </svg>
            </button>
            <!-- Vertical separator -->
            <div class="w-px self-stretch my-1 bg-surface-600 shrink-0" />
            <!-- Search togglers -->
            <div class="flex items-center shrink-0 px-1 gap-0.5">
              <!-- Toggler 1: Apply language filter strictly -->
              <button
                class="p-1 transition-colors rounded"
                :class="searchUseLangFilter ? 'text-primary-400' : 'text-gray-500 hover:text-gray-300'"
                :title="searchUseLangFilter ? 'Use language filter: on' : 'Use language filter: off'"
                @click.stop="toggleSearchLangFilter"
              >
                <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.3">
                  <circle cx="8" cy="8" r="6.5"/>
                  <ellipse cx="8" cy="8" rx="2.8" ry="6.5"/>
                  <line x1="1.5" y1="8" x2="14.5" y2="8"/>
                  <line x1="2.2" y1="5" x2="13.8" y2="5"/>
                  <line x1="2.2" y1="11" x2="13.8" y2="11"/>
                </svg>
              </button>
              <!-- Toggler 2: Apply color filter strictly -->
              <button
                class="p-1 transition-colors rounded"
                :class="searchUseColorFilter ? 'text-primary-400' : 'text-gray-500 hover:text-gray-300'"
                :title="searchUseColorFilter ? 'Use color filter: on' : 'Use color filter: off'"
                @click.stop="toggleSearchColorFilter"
              >
                <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.3">
                  <circle cx="6"  cy="6"  r="3.2"/>
                  <circle cx="10" cy="6"  r="3.2"/>
                  <circle cx="8"  cy="10" r="3.2"/>
                </svg>
              </button>
              <!-- Toggler 3: Search-in (source_text → target_text → notes) -->
              <button
                class="p-1 transition-colors rounded"
                :class="searchIn === 'source_text' ? 'text-gray-500 hover:text-gray-300' : 'text-primary-400'"
                :title="searchInTitle"
                @click.stop="cycleSearchIn"
              >
                <!-- States source_text / target_text: swap-arrows icon -->
                <svg v-if="searchIn !== 'notes'" viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M2 5h9"/>
                  <path d="M8.5 2.5L11 5l-2.5 2.5"/>
                  <path d="M14 11H5"/>
                  <path d="M7.5 8.5L5 11l2.5 2.5"/>
                </svg>
                <!-- State notes: notepad icon -->
                <svg v-else viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                  <rect x="2.5" y="1.5" width="11" height="13" rx="1.5"/>
                  <line x1="5" y1="6" x2="11" y2="6"/>
                  <line x1="5" y1="9" x2="11" y2="9"/>
                  <line x1="5" y1="12" x2="8.5" y2="12"/>
                </svg>
              </button>
            </div>
          </div>
          <!-- Results dropdown -->
          <div
            v-if="searchResults.length > 0"
            class="absolute top-full left-0 right-0 mt-1 z-40 bg-surface-900 border border-surface-700 rounded-xl shadow-xl overflow-hidden"
          >
          <table ref="searchResultsTableEl" class="w-full border-collapse">
              <tbody>
                <tr
                  v-for="(result, resultIdx) in searchResults"
                  :key="result.id"
                  class="cursor-pointer transition-colors"
                  :class="[result.in_filter ? 'text-gray-300' : 'text-gray-500', (hoveredResultId === result.id || focusedResultIndex === resultIdx) ? (resultColorBgHover(result) || 'bg-surface-800') : resultColorBg(result)]"
                  @mouseenter="hoveredResultId = result.id"
                  @mouseleave="hoveredResultId = null"
                  @click="navigateToResult(result)"
                >
                  <td class="pl-3 pr-2 py-2 text-xs text-gray-500 whitespace-nowrap align-baseline"><span>{{ formatSearchLangPair(result) }}</span></td>
                  <td class="py-2 pr-2 align-baseline w-full text-sm" style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ uiStore.swapDisplay ? result.target_text : result.source_text }}</td>
                  <td class="py-2 pr-3 text-xs text-gray-500/60 whitespace-nowrap align-baseline">{{ result.group.name }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- No-results state -->
          <div
            v-else-if="searchDone && !searchLoading && searchQuery.length >= 2"
            class="absolute top-full left-0 right-0 mt-1 z-40 bg-surface-900 border border-surface-700 rounded-xl shadow-xl px-3 py-2 text-xs text-gray-500"
          >
            No results
          </div>
        </div>

        <!-- Toolbar buttons (hidden when search is active and there's insufficient space) -->
        <!-- ml-auto: right-aligns the toolbar when search is active (no spacer, single gap). -->
        <div
          ref="toolbarEl"
          class="flex items-center gap-2 shrink-0"
          :class="{ 'ml-auto': searchActive && !searchToolbarHidden }"
          v-show="!searchActive || !searchToolbarHidden"
        >

          <!-- Lang-pair filter popup button -->
          <div v-if="availableLangs.length > 0" class="relative" ref="langPopupContainerRef">
            <button
              class="p-1.5 transition-colors rounded-lg border border-surface-700"
              :class="uiStore.activeLangs.length > 0 ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
              @click.stop="showLangPopup = !showLangPopup"
              title="Filter by language pair"
            >
              <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.3">
                <circle cx="8" cy="8" r="6.5"/>
                <ellipse cx="8" cy="8" rx="2.8" ry="6.5"/>
                <line x1="1.5" y1="8" x2="14.5" y2="8"/>
                <line x1="2.2" y1="5" x2="13.8" y2="5"/>
                <line x1="2.2" y1="11" x2="13.8" y2="11"/>
              </svg>
            </button>
            <div
              v-if="showLangPopup"
              class="absolute top-full left-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[110px]"
              @click.stop
            >
              <button
                v-for="lang in availableLangs"
                :key="lang"
                class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors flex items-center gap-2"
                :class="uiStore.activeLangs.length === 0
                  ? 'text-gray-300 hover:bg-surface-800'
                  : uiStore.activeLangs.includes(lang)
                    ? 'text-primary-400 bg-primary-500/10'
                    : 'text-gray-300 hover:bg-surface-800'"
              @click="onLangItemClick($event, lang)"
                @pointerdown.prevent="onFilterItemPointerDown($event, () => toggleLang(lang))"
                @pointerup="onFilterItemPointerUp()"
                @pointerleave="onFilterItemCancel()"
                @pointercancel="onFilterItemCancel()"
                @contextmenu.prevent
              >
                <span class="flex-1 -translate-y-px">{{ formatLangPair(lang) }}</span>
                <span v-if="uiStore.activeLangs.length > 0 && uiStore.activeLangs.includes(lang)" class="shrink-0 text-primary-400">✓</span>
              </button>
            </div>
          </div>

          <!-- Filter by color (icon + popup) -->
          <div class="relative" ref="colorFilterContainerRef">
            <button
              class="p-1.5 transition-colors rounded-lg border border-surface-700"
              :class="availableColors.length === 0
                ? 'text-gray-700 cursor-not-allowed'
                : uiStore.activeColors.length > 0 ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
              :disabled="availableColors.length === 0"
              @click.stop="showColorFilter = !showColorFilter"
              :title="availableColors.length === 0 ? 'No colored entries' : uiStore.activeColors.length > 0 ? 'Color filter active' : 'Filter by color'"
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
              class="absolute top-full left-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[120px]"
              @click.stop
            >
              <button
                v-for="opt in availableColors"
                :key="opt"
                class="text-left px-3 py-1.5 text-xs whitespace-nowrap transition-colors flex items-center gap-2"
                :class="uiStore.activeColors.includes(opt)
                  ? 'text-primary-400 bg-primary-500/10'
                  : 'text-gray-300 hover:bg-surface-800'"
                @click="onColorItemClick($event, opt)"
                @pointerdown.prevent="onFilterItemPointerDown($event, () => toggleColor(opt))"
                @pointerup="onFilterItemPointerUp()"
                @pointerleave="onFilterItemCancel()"
                @pointercancel="onFilterItemCancel()"
                @contextmenu.prevent
              >
                <span
                  v-if="opt === 'none'"
                  class="shrink-0 inline-flex w-3 h-3 rounded-full border border-surface-600"
                />
                <span
                  v-else
                  class="shrink-0 inline-flex w-3 h-3 rounded-full"
                  :class="colorSwatchBg(opt)"
                />
                <span class="flex-1">{{ colorOptionLabel(opt) }}</span>
                <span v-if="uiStore.activeColors.includes(opt)" class="shrink-0 text-primary-400">✓</span>
              </button>
            </div>
          </div>

          <!-- Translation toggle (icon) -->
          <button
            class="p-1.5 transition-colors rounded-lg border border-surface-700"
            :class="store.entries.length === 0
              ? 'text-gray-700 cursor-not-allowed'
              : anyHintVisible ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
            :disabled="store.entries.length === 0"
            @click="toggleAllHints"
            :title="store.entries.length === 0 ? 'No entries' : anyHintVisible ? 'Hide all translations' : 'Show all translations'"
          >
            <svg v-if="anyHintVisible" viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8s-2.5 4.5-6.5 4.5S1.5 8 1.5 8z"/>
              <circle cx="8" cy="8" r="2"/>
            </svg>
            <svg v-else viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 2l12 12M6.5 6.6a2 2 0 0 0 2.9 2.9M3.3 5.2C2.2 6.3 1.5 8 1.5 8s2.5 4.5 6.5 4.5c1 0 1.9-.3 2.7-.7M13.1 10.4c.9-1 1.4-2.4 1.4-2.4s-2.5-4.5-6.5-4.5c-.5 0-1 .1-1.4.2"/>
            </svg>
          </button>

          <!-- Swap display mode toggle (icon) -->
          <button
            ref="swapDisplayBtnEl"
            class="p-1.5 transition-colors rounded-lg border border-surface-700"
            :class="store.entries.length === 0
              ? 'text-gray-700 cursor-not-allowed'
              : uiStore.swapDisplay ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
            :disabled="store.entries.length === 0"
            @click="uiStore.swapDisplay = !uiStore.swapDisplay"
            :title="store.entries.length === 0 ? 'No entries' : uiStore.swapDisplay ? 'Disable swap display' : 'Enable swap display'"
          >
            <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M2 5h9"/>
              <path d="M8.5 2.5L11 5l-2.5 2.5"/>
              <path d="M14 11H5"/>
              <path d="M7.5 8.5L5 11l2.5 2.5"/>
            </svg>
          </button>

          <!-- Side word-list panel toggle (icon) -->
          <button
            ref="sidePanelToggleBtnEl"
            class="p-1.5 transition-colors rounded-lg border border-surface-700"
            :class="store.entries.length === 0
              ? 'text-gray-700 cursor-not-allowed'
              : uiStore.sidePanelVisible ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
            :disabled="store.entries.length === 0"
            @click="uiStore.sidePanelVisible = !uiStore.sidePanelVisible"
            :title="store.entries.length === 0 ? 'No entries' : uiStore.sidePanelVisible ? 'Hide word list' : 'Show word list'"
          >
            <svg viewBox="0 0 16 16" class="w-3.5 h-3.5" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <rect x="1.5" y="2.5" width="13" height="11" rx="1.5"/>
              <line x1="9.5" y1="2.5" x2="9.5" y2="13.5"/>
              <line x1="11" y1="5.5" x2="13" y2="5.5"/>
              <line x1="11" y1="8" x2="13" y2="8"/>
              <line x1="11" y1="10.5" x2="13" y2="10.5"/>
            </svg>
          </button>

          <!-- Density toggler (hidden on very narrow screens) -->
          <div v-if="!isVeryNarrow" class="flex items-center border border-surface-700 rounded-lg overflow-hidden">
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
              <svg v-if="level === 'compact'" viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
                <rect x="0"   y="1" width="1.5" height="12" rx="0.4"/>
                <rect x="3"   y="1" width="1.5" height="12" rx="0.4"/>
                <rect x="6"   y="1" width="1.5" height="12" rx="0.4"/>
                <rect x="9"   y="1" width="1.5" height="12" rx="0.4"/>
                <rect x="12"  y="1" width="1.5" height="12" rx="0.4"/>
              </svg>
              <svg v-else-if="level === 'normal'" viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
                <rect x="0"  y="1" width="3" height="12" rx="0.4"/>
                <rect x="5"  y="1" width="3" height="12" rx="0.4"/>
                <rect x="10" y="1" width="3" height="12" rx="0.4"/>
              </svg>
              <svg v-else viewBox="0 0 14 14" class="w-3.5 h-3.5" fill="currentColor">
                <rect x="0" y="1" width="5.5" height="12" rx="0.4"/>
                <rect x="8" y="1" width="5.5" height="12" rx="0.4"/>
              </svg>
            </button>
          </div>

        </div>
      </div>

      <!-- Row 2: group tabs · [more... / + group] · entry count -->
      <div class="flex items-start gap-1 mt-2 min-w-0">
        <div ref="groupsRowEl" class="flex items-center gap-1 flex-wrap min-w-0 flex-1">

        <!-- Each group tab -->
        <div
        v-for="tab in groupsStore.filteredTabs"
          v-show="!overflowedTabIds.has(tab.id)"
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
          @contextmenu.prevent
        >
          <template v-if="editingTabId !== tab.id">
            <span
              class="px-3 py-1 text-xs transition-colors rounded-l-full"
              :class="uiStore.activeGroupId === tab.id ? 'text-primary-300' : 'text-gray-400'"
            >{{ tab.name }}</span>
            <button
              data-delete-tab
              class="pr-3 pl-1.5 py-1.5 text-gray-600 hover:text-red-400 transition-colors rounded-r-full text-xs leading-none"
              title="Delete group"
            >×</button>
          </template>
          <template v-else>
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

        <!-- Add group / more... popup / Delete zone while dragging -->
        <div v-if="!draggedTabId" class="relative" ref="addGroupBtnContainerEl">
          <button
            ref="addGroupBtnEl"
            class="px-2.5 py-1 text-xs border border-dashed rounded-full transition-colors"
            :class="groupsOverflow
              ? 'text-gray-400 border-surface-600 hover:text-gray-300 hover:border-surface-500'
              : 'text-gray-600 hover:text-gray-300 border-surface-700 hover:border-surface-500'"
            @click="groupsOverflow ? toggleGroupsPopup() : addNewTab()"
            :title="groupsOverflow ? 'Show all groups' : 'Add group'"
          >{{ groupsOverflow ? 'more ...' : groupsStore.filteredTabs.length === 0 ? 'New group' : 'New' }}</button>

          <!-- Groups overflow popup -->
          <div
            v-if="showGroupsPopup"
            ref="groupsPopupEl"
            class="absolute top-full left-0 mt-1 z-30 bg-surface-900 border border-surface-700 rounded-xl shadow-lg py-1 flex flex-col min-w-[160px] max-h-64 overflow-y-auto"
            @click.stop
          >
          <div
          v-for="tab in groupsStore.filteredTabs"
            :key="tab.id"
          :data-popup-group-item="tab.id"
            class="relative flex items-center text-xs whitespace-nowrap transition-colors select-none touch-none"
            :class="[
              uiStore.activeGroupId === tab.id
                ? 'text-primary-400 bg-primary-500/10'
                : 'text-gray-300 hover:bg-surface-800',
              longPressReadyPopupTabId === tab.id ? 'cursor-text' : 'cursor-default',
            ]"
            @mouseenter="hoveredPopupTabId = tab.id"
            @mouseleave="hoveredPopupTabId = null"
            @pointerdown.prevent="onPopupItemPointerDown($event, tab.id)"
            @pointermove="onPopupItemPointerMove"
            @pointerup="onPopupItemPointerUp"
            @pointercancel="onPopupItemPointerCancel"
            @contextmenu.prevent
          >
            <template v-if="editingPopupTabId !== tab.id">
              <span class="flex-1 px-3 py-1.5 truncate">{{ tab.name }}</span>
              <span
                v-if="uiStore.activeGroupId === tab.id && hoveredPopupTabId !== tab.id"
                class="shrink-0 pr-3 text-primary-400"
              >✓</span>
              <button
                v-if="hoveredPopupTabId === tab.id"
                class="shrink-0 pr-3 pl-2 py-1.5 text-gray-600 hover:text-red-400 transition-colors leading-none"
                title="Delete group"
                @pointerdown.stop
                @click.stop="deleteTabFromPopup(tab.id)"
              >×</button>
            </template>
            <template v-else>
              <span class="flex-1 px-3 py-1.5 invisible pointer-events-none" aria-hidden="true">{{ tabEditName }}</span>
              <input
                v-focus-select
                type="text"
                v-model="tabEditName"
                :maxlength="GROUP_NAME_MAX_LEN"
                class="absolute inset-0 px-3 py-1.5 text-xs bg-transparent text-gray-200 outline-none"
                @blur="saveTabEdit(tab.id)"
                @keydown.enter.prevent="saveTabEdit(tab.id)"
                @keydown.escape.prevent="cancelTabEdit"
                @pointerdown.stop
                @click.stop
              />
            </template>
          </div>
            <div class="border-t border-surface-700 mt-1 pt-1">
              <button
                class="w-full text-left px-3 py-1.5 text-xs text-gray-500 hover:text-gray-300 hover:bg-surface-800 transition-colors"
                @click="addNewTabFromPopup"
              >Add group</button>
            </div>
          </div>
        </div>
        <div
          v-else
          data-delete-tab-zone
          class="px-2.5 py-1 text-xs rounded-full border border-dashed transition-colors select-none"
          :class="dragOverDeleteZone
            ? 'text-red-400 bg-red-500/10 border-red-500/50'
            : 'text-gray-500 border-surface-600'"
        >Delete</div>
        </div>

        <!-- Entry count, right-aligned -->
        <span ref="entryCountLabelEl" class="pt-1 shrink-0 text-xs text-gray-500 select-none tabular-nums">{{ entryCountLabel }}</span>
      </div>
    </div>

    <!-- Content row: main grid + optional right word-list panel (fills remaining height) -->
    <div class="flex-1 min-h-0 flex gap-3 pb-3 relative">
      <div ref="cardsAreaEl" class="flex-1 min-w-0 overflow-y-auto -mx-0.5 p-0.5">
        <!-- Loading skeleton: shown after 200 ms regardless of previous content -->
        <div v-if="showSkeleton" class="grid gap-3" :style="gridStyle">
          <div v-for="i in 6" :key="i" class="h-16 bg-surface-800 rounded-2xl animate-pulse" />
        </div>

        <!-- Empty state: filteredEntries uses the frozen snapshot during loading,
             so this condition naturally reflects the previous group's content until
             the request completes or the skeleton kicks in. -->
        <div v-else-if="!filteredEntries.length && !store.isLoading" class="py-16 text-center text-gray-500">
          <template v-if="store.fetchError">
            <p class="text-lg mb-2">Fetch error.</p>
            <p class="text-sm"> Please, try again later.</p>
          </template>
          <template v-else-if="!store.entries.length">
            <p class="text-lg mb-2">This group is empty.</p>
            <p class="text-sm">Translate something and click <strong>Add to Wordbook</strong> to add entries here.</p>
          </template>
          <template v-else>
            <p class="text-lg mb-2">No entries match the current filter.</p>
            <p class="text-sm">Clear the color filter to see all entries in this group.</p>
          </template>
        </div>

        <!-- Entry grid -->
        <div
          v-else
          ref="gridEl"
          class="grid gap-3"
          :style="gridStyle"
          @pointerdown.capture="onCardGridPointerDown"
          @pointermove="onCardGridPointerMove"
          @pointerup="onCardGridPointerUpOrCancel"
          @pointercancel="onCardGridPointerUpOrCancel"
        >
          <div
            v-for="entry in filteredEntries"
            :key="entry.id"
            :data-entry-id="entry.id"
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
              class="flex-1"
              @delete="handleDelete"
              @update="handleUpdate"
              @move="handleMoveEntry"
              @find-similar="handleFindSimilarEntry"
            />
          </div>
        </div>
        <!-- Spacer: prevents scroll-height flicker when the details overlay collapses.
             Height = largest observed overlay-overflow past the grid bottom.
             Only shrinks once its dead zone scrolls below the visible area. -->
        <div
          ref="spacerEl"
          aria-hidden="true"
          class="pointer-events-none"
          :style="{ height: spacerHeight + 'px' }"
        />
      </div>

      <!--
        Right-side vertical word-list panel.
        Portrait: ephemeral overlay (absolute, does not affect grid width).
        Landscape: static sidebar that shrinks/caps to available height.
      -->
      <aside
        v-if="uiStore.sidePanelVisible && filteredEntries.length > 0"
        ref="sidePanelEl"
        class="shrink-0 w-44 sm:w-56 card p-2"
        :class="isPortrait
          ? 'absolute right-0 top-0 bottom-3 z-20 overflow-y-auto'
          : 'self-start max-h-full overflow-y-auto'"
        @click.stop
      >
        <ul class="space-y-0.5">
          <li v-for="entry in sortedPanelWords" :key="entry.id" class="flex items-center">
            <span
              class="w-3 shrink-0 text-center text-xs font-semibold text-primary-300"
              aria-hidden="true"
            >{{ panelWordLetterMap.get(entry.id) ?? '' }}</span>
            <button
              class="flex-1 min-w-0 text-left px-2 py-1 text-xs rounded truncate transition-colors"
              :class="uiStore.getFocusedEntry(entry.group.id) === entry.id
                ? 'text-gray-300 bg-surface-800 hover:text-primary-300 hover:bg-surface-800'
                : 'text-gray-300 hover:text-primary-300 hover:bg-surface-800'"
              :title="uiStore.swapDisplay ? entry.target_text : entry.source_text"
              @click="onSidePanelWordClick(entry.id)"
            >{{ uiStore.swapDisplay ? entry.target_text : entry.source_text }}</button>
          </li>
        </ul>
      </aside>
    </div>

    <!-- Entry context popup (long-press on details button, position: fixed) -->
    <div
      v-if="entryContextPopup"
      ref="entryContextPopupEl"
      class="fixed z-50 bg-surface-900 border border-gray-600 rounded-xl shadow-xl overflow-y-auto"
      :style="entryContextPopupStyle"
      @pointerdown.stop
      @click.stop
    >
      <table v-if="entryContextPopup.results.length > 0" class="w-full border-collapse">
        <tbody>
          <tr
            v-for="result in entryContextPopup.results"
            :key="result.id"
            class="cursor-pointer transition-colors"
            :class="[result.in_filter ? 'text-gray-300' : 'text-gray-500', hoveredContextResultId === result.id ? (contextResultColorBgHover(result) || 'bg-surface-800') : contextResultColorBg(result)]"
            @mouseenter="hoveredContextResultId = result.id"
            @mouseleave="hoveredContextResultId = null"
            @click="navigateFromContextPopup(result)"
          >
            <td class="py-2 pl-3 pr-2 align-baseline w-full text-sm" style="max-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{{ uiStore.swapDisplay ? result.target_text : result.source_text }}</td>
            <td class="py-2 pr-3 text-xs text-gray-500/60 whitespace-nowrap align-baseline">{{ result.group.name }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else-if="entryContextPopup.loading" class="px-3 py-2 text-xs text-gray-500">Loading…</div>
      <div v-else class="px-3 py-2 text-xs text-gray-500">No results</div>
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
      message="Are you sure you want to delete this group? All entries in it will also be permanently deleted."
      confirm-text="Delete"
      cancel-text="Cancel"
      variant="danger"
      @confirm="confirmDeleteTab"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref, watch } from 'vue'
import { registerBackHandler } from '@/composables/useBackButton'
import { onBeforeRouteLeave } from 'vue-router'
import { useWordbookStore } from '@/stores/wordbook'
import { useWordbookUiStore, type DensityLevel } from '@/stores/wordbookUi'
import { useWordbookGroupsStore, type WordGroup } from '@/stores/wordbookGroups'
import WordbookEntry from '@/components/WordbookEntry.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/utils/error'
import { SPINNER_DELAY_MS, LONG_PRESS_MS } from '@/utils/ui'
import { useLongPress } from '@/composables/useLongPress'
import {
  ENTRY_COLORS,
  ENTRY_COLOR_LABEL,
  ENTRY_COLOR_SWATCH_BG,
  ENTRY_COLOR_CARD_BG,
  ENTRY_COLOR_CARD_BG_FOCUSED,
  isEntryColor,
  type EntryColor,
} from '@/utils/entryColors'
import { wordbookApi } from '@/api/wordbook'
import type { WordbookEntry as WordbookEntryData, WordbookSearchEntry } from '@/types'

const store = useWordbookStore()
const toast = useToastStore()
const uiStore = useWordbookUiStore()
const groupsStore = useWordbookGroupsStore()

// ─── Skeleton delay + display freeze ────────────────────────────────────────
// stableEntries holds the last committed entry list. During the pre-skeleton
// loading window (< 200 ms) the display uses it so the current content stays
// frozen on screen — nothing flickers regardless of whether the outgoing or
// incoming group is empty.
// After 200 ms the skeleton replaces whatever was frozen.
const showSkeleton = ref(false)
const stableEntries = ref<typeof store.entries>([])
let skeletonTimer: ReturnType<typeof setTimeout> | null = null
watch(
  () => store.isLoading,
  (loading) => {
    if (loading) {
      skeletonTimer = setTimeout(() => { showSkeleton.value = true }, SPINNER_DELAY_MS)
    } else {
      if (skeletonTimer !== null) { clearTimeout(skeletonTimer); skeletonTimer = null }
      showSkeleton.value = false
      stableEntries.value = store.entries
    }
  },
)

// Entries to use for display: frozen during the pre-skeleton window so that
// the outgoing group's content remains visible, then live once loading ends
// or the skeleton has taken over.
const displayEntries = computed(() =>
  (store.isLoading && !showSkeleton.value) ? stableEntries.value : store.entries
)

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

// Lang pairs come from the backend via the groups store (server-sourced).
const availableLangs = computed(() => groupsStore.langPairs)

function toggleLang(pair: string) {
  const current = [...uiStore.activeLangs]
  const idx = current.indexOf(pair)
  if (idx === -1) current.push(pair)
  else current.splice(idx, 1)
  uiStore.activeLangs = current
}

function onLangItemClick(e: MouseEvent, lang: string) {
  toggleLang(lang)
  if (!e.ctrlKey) showLangPopup.value = false
}

// When the lang-pair filter changes, re-fetch groups (filtered) then entries.
watch(
  () => uiStore.activeLangs,
  async (newLangs) => {
    if (!viewIsActive.value) return
    await groupsStore.fetchGroups(newLangs.length > 0 ? [...newLangs] : undefined)
    const groupIdBefore = uiStore.activeGroupId
    uiStore.initActiveGroup(groupsStore.filteredTabs)
    // If initActiveGroup changed the active group, the activeGroupId watcher
    // will fetch entries for the new group — skip here to avoid a duplicate fetch.
    if (uiStore.activeGroupId !== groupIdBefore) return
    if (uiStore.activeGroupId !== null) {
      await store.fetchEntries(uiStore.activeGroupId, newLangs.length > 0 ? [...newLangs] : undefined)
      uiStore.prune(store.entries.map((e) => e.id))
    }
  },
)

// Stale activeLangs cleanup: drop any saved pairs that are no longer in the
// backend list (e.g. user deleted all entries with that pair).
watch(availableLangs, (pairs) => {
  if (uiStore.activeLangs.length === 0) return
  const valid = new Set(pairs)
  const cleaned = uiStore.activeLangs.filter((p) => valid.has(p))
  if (cleaned.length !== uiStore.activeLangs.length) {
    uiStore.activeLangs = cleaned
  }
})

// ─── Color filter ─────────────────────────────────────────────────────────

// 'none' is a sentinel that matches uncolored entries.
const COLOR_FILTER_NONE = 'none'

// Always show the full static palette — no scan of entries needed.
const availableColors: string[] = [...ENTRY_COLORS, COLOR_FILTER_NONE]

function toggleColor(color: string) {
  const current = [...uiStore.activeColors]
  const idx = current.indexOf(color)
  if (idx === -1) current.push(color)
  else current.splice(idx, 1)
  uiStore.activeColors = current
}

function onColorItemClick(e: MouseEvent, opt: string) {
  toggleColor(opt)
  if (!e.ctrlKey) showColorFilter.value = false
}

function colorSwatchBg(color: string): string {
  return isEntryColor(color) ? ENTRY_COLOR_SWATCH_BG[color] : ''
}

function colorOptionLabel(color: string): string {
  return color === COLOR_FILTER_NONE ? 'No color' : ENTRY_COLOR_LABEL[color as EntryColor]
}

// ─── Filter menu item long-press ─────────────────────────────────────────────
// A single useLongPress instance is shared across all lang-pair and color
// filter items.  Because the action varies per item, it is captured at
// pointerdown time via _filterLpAction and forwarded to the composable's
// onLongPress callback.  onShortPress is intentionally omitted: the
// short-press action flows through the normal @click handler, which also
// carries the MouseEvent needed for the Ctrl-click multi-select check.
let _filterLpAction: (() => void) | null = null
const {
  onPointerDown: _filterLpPointerDown,
  onPointerUp: onFilterItemPointerUp,
  onCancel: onFilterItemCancel,
} = useLongPress(
  () => { _filterLpAction?.() },
  { suppressClickAfterLongPress: true },
)

function onFilterItemPointerDown(e: PointerEvent, action: () => void) {
  _filterLpAction = action
  _filterLpPointerDown(e)
}

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

// ─── Filtered entries ─────────────────────────────────────────────────────────
// Group and lang-pair filtering is now server-side; only the color filter
// is applied client-side on the current group's loaded entries.

const filteredEntries = computed(() =>
  displayEntries.value.filter((entry) => {
    if (uiStore.activeColors.length === 0) return true
    return isEntryColor(entry.color)
      ? uiStore.activeColors.includes(entry.color)
      : uiStore.activeColors.includes(COLOR_FILTER_NONE)
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

// ─── Entry count label ─────────────────────────────────────────────────────────────────
// Shows total when no filter active; filtered/total when any filter
// (color or lang-pair) actually reduces the visible count.

const entryCountLabel = computed(() => {
  const filtered = filteredEntries.value.length
  const total = store.totalEntries
  const anyFilterActive = uiStore.activeColors.length > 0 || uiStore.activeLangs.length > 0
  const suffix = isVeryNarrow.value ? '' : ' entries'
  if (anyFilterActive && filtered < total) return `${filtered}/${total}${suffix}`
  return `${total}${suffix}`
})

// ─── Side panel (alphabetical word list) ───────────────────────────────────────────────────

const sortedPanelWords = computed(() =>
  [...filteredEntries.value].sort((a, b) => {
    const textA = uiStore.swapDisplay ? a.target_text : a.source_text
    const textB = uiStore.swapDisplay ? b.target_text : b.source_text
    return textA.localeCompare(textB, undefined, { sensitivity: 'base' })
  }),
)

const panelWordLetterMap = computed(() => {
  const map = new Map<number, string>()
  let lastLetter = ''
  for (const entry of sortedPanelWords.value) {
    const text = uiStore.swapDisplay ? entry.target_text : entry.source_text
    const letter = text.charAt(0).toUpperCase().normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    if (letter !== lastLetter) {
      map.set(entry.id, letter)
      lastLetter = letter
    }
  }
  return map
})

function formatLangPair(pair: string): string {
  const [src, tgt] = pair.split(':', 2)
  if (!uiStore.swapDisplay) return `${src} → ${tgt}`
  return `${tgt} ← ${src}`
}

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
  const entry = store.entries.find((e) => e.id === id)
  if (entry) uiStore.setFocusedEntry(id, entry.group.id)
  if (uiStore.activeCardId !== null && uiStore.activeCardMode === 'details') {
    uiStore.closeActive()
  }
  await nextTick()
  const el = document.querySelector(`[data-entry-id="${id}"]`) as HTMLElement | null
  if (!el) {
    uiStore.highlightEntry(id)
    return
  }

  // Check whether the card is already within the viewport.
  const rect = el.getBoundingClientRect()
  const offScreen = rect.bottom < 0 || rect.top > window.innerHeight

  el.scrollIntoView({ behavior: 'smooth', block: 'center' })

  if (!offScreen) {
    // Card was already visible — any centering scroll is tiny; highlight now.
    uiStore.highlightEntry(id)
    return
  }

  // Card was off-screen. Start the flash as soon as ~50 % of the card
  // scrolls into view (mid-scroll, not after the scroll finishes) so the
  // animation feels immediate while the card is still visibly arriving.
  // IntersectionObserver fires reactively during the smooth scroll;
  // the timeout is a safety net for edge cases.
  let done = false
  const triggerHighlight = () => {
    if (done) return
    done = true
    observer.disconnect()
    uiStore.highlightEntry(id)
  }
  const observer = new IntersectionObserver(
    (entries) => { if (entries[0].isIntersecting) triggerHighlight() },
    { threshold: 0.5 },
  )
  observer.observe(el)
  setTimeout(triggerHighlight, 800)
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
  // If a group-switch fetch is already in flight (started by the activeGroupId
  // watcher), wait for it to complete — that watcher owns the fetch and prune.
  // Starting a second fetch here would race against it and corrupt the result.
  if (store.isLoading) {
    await new Promise<void>((resolve) => {
      const stop = watch(() => store.isLoading, (loading) => {
        if (!loading) { stop(); resolve() }
      })
    })
    // After the load completes, the activeGroupId watcher schedules a nextTick
    // to restore cardsAreaEl.scrollTop. Use setTimeout(0) to let all pending
    // microtasks (Vue ticks, scroll restoration) settle before scrolling.
    await new Promise<void>(resolve => setTimeout(resolve, 0))
  } else if (!store.isLoaded && uiStore.activeGroupId !== null) {
    await store.fetchEntries(uiStore.activeGroupId, uiStore.activeLangs.length > 0 ? [...uiStore.activeLangs] : undefined)
  }
  await nextTick()
  await scrollToEntry(id)
}

const anyHintVisible = computed(() =>
  uiStore.showTranslations || store.entries.some((e) => uiStore.getReactive(e.id, 'hintVisible')),
)

function toggleAllHints() {
  uiStore.setAllHints(!anyHintVisible.value)
}

// ─── Scroll position memory per group ───────────────────────────────────────

const cardsAreaEl = ref<HTMLElement | null>(null)

/**
 * In-memory map of group id (or null for "All") → last scroll position.
 * Populated when leaving a group; consumed when entering one.
 */
const groupScrollPositions = new Map<number | null, number>()

function restoreDetailsIfEntryExists(entryId: number | undefined): void {
  if (entryId === undefined) return
  if (!store.entries.some((e) => e.id === entryId)) return
  uiStore.openDetails(entryId)
}

/**
 * Watcher fires at `flush: 'pre'` — before Vue applies DOM updates — so
 * `cardsAreaEl.scrollTop` still reflects the *outgoing* group. We save it,
 * then restore the incoming group's position after the DOM settles.
 * `scrollTop` assignment is instantaneous (no animation).
 */
// Save the current group's scroll position just before navigating away.
// onBeforeRouteLeave fires before KeepAlive detaches the DOM, so scrollTop
// is still valid here. onDeactivated is too late — Firefox resets scrollTop
// to 0 when elements are moved to a detached container, which happens before
// onDeactivated runs.
onBeforeRouteLeave(() => {
  if (cardsAreaEl.value) {
    groupScrollPositions.set(uiStore.activeGroupId ?? null, cardsAreaEl.value.scrollTop)
  }
  closeEntryContextPopup()
})

watch(
  () => uiStore.activeGroupId,
  async (newGroupId, oldGroupId) => {
    if (!viewIsActive.value) return
    if (cardsAreaEl.value) {
      groupScrollPositions.set(oldGroupId ?? null, cardsAreaEl.value.scrollTop)
    }
    uiStore.saveOpenDetailsForGroup(oldGroupId ?? null)
    uiStore.closeActive()
    uiStore.switchGroup(newGroupId)
    // Re-fetch entries for the newly-activated group.
    if (newGroupId !== null) {
      await store.fetchEntries(newGroupId, uiStore.activeLangs.length > 0 ? [...uiStore.activeLangs] : undefined)
      // Guard: another group switch may have fired while this fetch was in flight.
      // If the active group has already moved on, this call is stale — bail out
      // so prune and restore don't run against the wrong group's in-memory map.
      if (uiStore.activeGroupId !== newGroupId) return
      uiStore.prune(store.entries.map((e) => e.id))
      restoreDetailsIfEntryExists(uiStore.getOpenDetailsForGroup(newGroupId))
    } else {
      store.reset()
    }
    nextTick(() => {
      if (cardsAreaEl.value) {
        cardsAreaEl.value.scrollTop = groupScrollPositions.get(newGroupId) ?? 0
      }
    })
  },
)

// ─── Group / tab CRUD ─────────────────────────────────────────────────────────

const vFocusSelect = {
  mounted: (el: HTMLElement) => { el.focus(); (el as HTMLInputElement).select?.() },
}

const editingTabId = ref<number | null>(null)
const editingPopupTabId = ref<number | null>(null)
const tabEditName = ref('')

function selectTab(id: number) {
  if (editingTabId.value === id) return
  uiStore.activeGroupId = id  // always activate; toggling off is not allowed
}

function startTabEdit(tab: WordGroup) {
  editingTabId.value = tab.id
  editingPopupTabId.value = null
  tabEditName.value = tab.name
}

function startPopupTabEdit(tab: WordGroup) {
  editingPopupTabId.value = tab.id
  editingTabId.value = null
  tabEditName.value = tab.name
}

async function saveTabEdit(id: number) {
  if (editingTabId.value !== id && editingPopupTabId.value !== id) return
  const name = tabEditName.value.trim()
  editingTabId.value = null
  editingPopupTabId.value = null
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
  editingPopupTabId.value = null
}

async function addNewTab() {
  const existingNames = new Set(groupsStore.tabs.map((t) => t.name))
  let n = groupsStore.filteredTabs.length + 1
  while (existingNames.has(`Group ${n}`)) n++
  try {
    const tab = await groupsStore.addTab(`Group ${n}`)
    uiStore.activeGroupId = tab.id
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
  const wasActive = uiStore.activeGroupId === id
  const deletedIndex = groupsStore.filteredTabs.findIndex((t) => t.id === id)
  try {
    await groupsStore.deleteTab(id)
    uiStore.deleteGroupEntries(id)
    if (wasActive) {
      const next = groupsStore.filteredTabs[deletedIndex] ?? groupsStore.filteredTabs[groupsStore.filteredTabs.length - 1] ?? null
      uiStore.activeGroupId = next?.id ?? null  // the activeGroupId watcher handles the rest
    }
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to delete group'))
  }
}

// ─── Header layout measurement ───────────────────────────────────────────────

const GROUP_NAME_MAX_LEN = 25

// Row 1 refs
const headerRow1El = ref<HTMLElement | null>(null)
const titleEl = ref<HTMLElement | null>(null)
const toolbarEl = ref<HTMLElement | null>(null)
// Lang popup
const showLangPopup = ref(false)
const langPopupContainerRef = ref<HTMLElement | null>(null)

function onLangPopupOutsideClick(e: MouseEvent) {
  if (!(e.target as Node | null)) return
  if (langPopupContainerRef.value?.contains(e.target as Node)) return
  showLangPopup.value = false
}
watch(showLangPopup, (open) => {
  if (open) document.addEventListener('click', onLangPopupOutsideClick, true)
  else document.removeEventListener('click', onLangPopupOutsideClick, true)
})

// Row 2 refs
const groupsRowEl = ref<HTMLElement | null>(null)
const addGroupBtnContainerEl = ref<HTMLElement | null>(null)
const addGroupBtnEl = ref<HTMLElement | null>(null)
const entryCountLabelEl = ref<HTMLElement | null>(null)
const tabWidths = new Map<number, number>()
const overflowedTabIds = ref(new Set<number>())
const groupsOverflow = ref(false)
const visibleTabCount = ref(0)

// Groups popup
const showGroupsPopup = ref(false)
const groupsPopupEl = ref<HTMLElement | null>(null)

function onGroupsPopupOutsideClick(e: MouseEvent) {
  if (!(e.target as Node | null)) return
  if (addGroupBtnContainerEl.value?.contains(e.target as Node)) return
  showGroupsPopup.value = false
}
watch(showGroupsPopup, (open) => {
  if (open) {
    document.addEventListener('click', onGroupsPopupOutsideClick, true)
  } else {
    document.removeEventListener('click', onGroupsPopupOutsideClick, true)
    hoveredPopupTabId.value = null
    clearPopupLongPressTimer()
    popupItemInteraction.value = null
    if (editingPopupTabId.value !== null) cancelTabEdit()
  }
})

// Portrait / narrow detection
const isPortrait = ref(false)
const isVeryNarrow = ref(false)
let portraitMq: MediaQueryList | null = null

function onPortraitChange() {
  const newPortrait = portraitMq?.matches ?? false
  if (isPortrait.value !== newPortrait) {
    isPortrait.value = newPortrait
    if (uiStore.sidePanelVisible) dismissSidePanel()
    nextTick(() => checkTabsFit())
  }
}

watch(isVeryNarrow, (narrow) => {
  if (narrow && uiStore.density !== 'normal') uiStore.density = 'normal'
})

// Side panel portrait overlay
const sidePanelEl = ref<HTMLElement | null>(null)
const sidePanelToggleBtnEl = ref<HTMLElement | null>(null)
const swapDisplayBtnEl = ref<HTMLElement | null>(null)

function dismissSidePanel() {
  uiStore.sidePanelVisible = false
}

function onSidePanelOutsideClick(e: MouseEvent) {
  const target = e.target as Node | null
  if (!target || !sidePanelEl.value) return
  if (sidePanelEl.value.contains(target)) return
  // The toggle button manages its own state via @click; skip here so the
  // capture-phase dismiss doesn't race with the button's bubble-phase toggle.
  if (sidePanelToggleBtnEl.value?.contains(target)) return
  dismissSidePanel()
}

watch(
  [() => uiStore.sidePanelVisible, isPortrait],
  ([visible, portrait]) => {
    if (visible && portrait) document.addEventListener('click', onSidePanelOutsideClick, true)
    else document.removeEventListener('click', onSidePanelOutsideClick, true)
  },
)

async function onSidePanelWordClick(id: number) {
  if (isPortrait.value) dismissSidePanel()
  await scrollToEntry(id)
}

// ─── Row 1: search toolbar fit check ─────────────────────────────────────────

function getWidth(el: HTMLElement): number {
  return el.getBoundingClientRect().width
}

function getContentWidth(el: HTMLElement): number {
  const range = document.createRange()
  range.selectNodeContents(el)
  return range.getBoundingClientRect().width
}

let _lastToolbarWidth = 0

function checkLangFit() {
  const row1 = headerRow1El.value
  const title = titleEl.value
  const toolbar = toolbarEl.value
  if (!row1 || !title || !toolbar) return
  const containerWidth = getWidth(row1)

  // Cache toolbar width whenever it is rendered (v-show keeps it in the DOM
  // but collapses to 0 when searchToolbarHidden is true).
  const toolbarW = getWidth(toolbar)
  if (toolbarW > 0) _lastToolbarWidth = toolbarW
  const effectiveToolbarW = toolbarW > 0 ? toolbarW : _lastToolbarWidth

  if (searchActive.value) {
    // In search mode: determine whether the toolbar must be hidden entirely.
    // gap-2 between flex items = 8 px; account for two gaps (title|input, input|toolbar).
    const ROW_GAP = 8
    searchToolbarHidden.value =
      getContentWidth(title) + ROW_GAP + SEARCH_FIXED_WIDTH + ROW_GAP + effectiveToolbarW > containerWidth
  } else {
    searchToolbarHidden.value = false
  }
}

// ─── Row 2: tab overflow fit check ───────────────────────────────────────────

const HEADER_GROUPS_GAP_PX = 4
// Tracks the largest button width seen across both "+ group" and "more ..."
// states. Using the running max prevents the simulation from oscillating:
// if the two texts have different rendered widths, alternating between them
// causes each checkTabsFit call to flip groupsOverflow, which triggers
// another call, which flips again — an infinite resize feedback loop.
let _maxSeenBtnW = 0

function measureTabWidths() {
  const rowEl = groupsRowEl.value
  if (!rowEl) return
  for (const el of Array.from(rowEl.querySelectorAll<HTMLElement>('[data-tab-id]'))) {
    const id = Number(el.getAttribute('data-tab-id'))
    if (isNaN(id)) continue
    const w = el.getBoundingClientRect().width
    if (w > 0) tabWidths.set(id, w)
  }
}

/**
 * Simulate flex-wrap placement of all tabs + the add/more button.
 * Hides tabs (via overflowedTabIds) that would push the button beyond
 * maxLines (1 for landscape, 2 for portrait).
 */
function checkTabsFit() {
  measureTabWidths()
  const rowEl = groupsRowEl.value
  const addBtn = addGroupBtnEl.value
  if (!rowEl || !addBtn) return

  const tabs = groupsStore.filteredTabs
  const containerWidth = getWidth(rowEl)
  let btnW = getWidth(addBtn)
  if (btnW === 0) btnW = 64
  // Always use the largest button width seen so far. This prevents oscillation
  // between the "+ group" and "more ..." states whose rendered widths differ:
  // once we've seen the wider state we keep using it, so the simulation's
  // outcome is identical on every call for the same container width.
  _maxSeenBtnW = Math.max(_maxSeenBtnW, btnW)
  btnW = _maxSeenBtnW
  const maxLines = isPortrait.value ? 2 : 1
  const gap = HEADER_GROUPS_GAP_PX

  for (const tab of tabs) {
    if (!tabWidths.has(tab.id)) {
      overflowedTabIds.value = new Set()
      groupsOverflow.value = false
      visibleTabCount.value = tabs.length
      if (containerWidth > 0) nextTick(() => checkTabsFit())
      return
    }
  }

  /**
   * Place tab[i] at cursor position x (on line `line`), then simulate where
   * the button would land. Returns true if the button would exceed maxLines.
   */
  function wouldOverflow(x: number, line: number, w: number): boolean {
    if (x > 0 && x + gap + w > containerWidth) { line++; x = w }
    else { x = x === 0 ? w : x + gap + w }
    const btnLine = (x + gap + btnW <= containerWidth) ? line : line + 1
    return btnLine > maxLines
  }

  let x = 0, line = 1
  for (let i = 0; i < tabs.length; i++) {
    const w = tabWidths.get(tabs[i].id)!
    if (wouldOverflow(x, line, w)) {
      overflowedTabIds.value = new Set(tabs.slice(i).map(t => t.id))
      groupsOverflow.value = true
      visibleTabCount.value = i
      return
    }
    // Actually advance x/line for real.
    if (x > 0 && x + gap + w > containerWidth) { line++; x = w }
    else { x = x === 0 ? w : x + gap + w }
  }

  // Post-loop: verify button fits after all visible tabs.
  // This also handles the zero-tabs case where the loop body never ran.
  {
    const btnLine = (x === 0 || x + gap + btnW <= containerWidth) ? line : line + 1
    if (btnLine > maxLines && tabs.length > 0) {
      // This shouldn't happen if the loop above is correct, but guard anyway.
      const lastIdx = tabs.length - 1
      overflowedTabIds.value = new Set([tabs[lastIdx].id])
      groupsOverflow.value = true
      visibleTabCount.value = lastIdx
      return
    }
  }

  overflowedTabIds.value = new Set()
  groupsOverflow.value = false
  visibleTabCount.value = tabs.length
}

async function toggleGroupsPopup() {
  if (showGroupsPopup.value) { showGroupsPopup.value = false; return }
  showGroupsPopup.value = true
  await nextTick()
  const popup = groupsPopupEl.value
  if (!popup) return
  const activeId = uiStore.activeGroupId
  const tabs = groupsStore.filteredTabs
  const activeIndex = tabs.findIndex(t => t.id === activeId)
  if (activeIndex === -1) return
  const items = Array.from(popup.querySelectorAll<HTMLElement>('[data-popup-group-item]'))
  if (items.length === 0 || activeIndex >= items.length) return
  const activeItem = items[activeIndex]
  popup.scrollTop = activeItem.offsetTop - popup.clientHeight / 2 + activeItem.offsetHeight / 2
}

function selectTabFromPopup(id: number) {
  selectTab(id)
  showGroupsPopup.value = false
}

async function addNewTabFromPopup() {
  showGroupsPopup.value = false
  await addNewTab()
}

// ─── Groups popup item interactions ──────────────────────────────────────────
const hoveredPopupTabId = ref<number | null>(null)

interface PopupItemInteraction {
  tabId: number
  startX: number
  startY: number
  startTime: number
}
const popupItemInteraction = ref<PopupItemInteraction | null>(null)
const longPressReadyPopupTabId = ref<number | null>(null)
let popupLongPressTimerId: ReturnType<typeof setTimeout> | null = null

function clearPopupLongPressTimer() {
  if (popupLongPressTimerId !== null) { clearTimeout(popupLongPressTimerId); popupLongPressTimerId = null }
  longPressReadyPopupTabId.value = null
}

function onPopupItemPointerDown(event: PointerEvent, tabId: number) {
  if (editingPopupTabId.value === tabId || editingTabId.value === tabId) return
  event.preventDefault()
  if (editingTabId.value !== null) saveTabEdit(editingTabId.value)
  if (editingPopupTabId.value !== null) saveTabEdit(editingPopupTabId.value)
  popupItemInteraction.value = { tabId, startX: event.clientX, startY: event.clientY, startTime: Date.now() }
  clearPopupLongPressTimer()
  // Same two-step pattern as the tab row: timer sets the visual cursor-text cue;
  // the actual commit (rename or select) happens on pointer-up via elapsed check.
  popupLongPressTimerId = setTimeout(() => {
    popupLongPressTimerId = null
    if (popupItemInteraction.value?.tabId === tabId) longPressReadyPopupTabId.value = tabId
  }, LONG_PRESS_MS)
}

function onPopupItemPointerMove(event: PointerEvent) {
  const state = popupItemInteraction.value
  if (!state) return
  const dx = event.clientX - state.startX
  const dy = event.clientY - state.startY
  if (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD) {
    clearPopupLongPressTimer()
    popupItemInteraction.value = null
  }
}

function onPopupItemPointerUp(_event: PointerEvent) {
  clearPopupLongPressTimer()
  const state = popupItemInteraction.value
  popupItemInteraction.value = null
  if (!state) return
  const elapsed = Date.now() - state.startTime
  if (elapsed >= LONG_PRESS_MS) {
    const tab = groupsStore.filteredTabs.find(t => t.id === state.tabId)
    if (tab) startPopupTabEdit(tab)
  } else {
    selectTabFromPopup(state.tabId)
  }
}

function onPopupItemPointerCancel() {
  clearPopupLongPressTimer()
  popupItemInteraction.value = null
}

function deleteTabFromPopup(id: number) {
  showGroupsPopup.value = false
  deleteTab(id)
}

// ─── Combined header layout check ────────────────────────────────────────────

function checkHeaderLayout() {
  const row1 = headerRow1El.value
  if (!row1) return
  const w = getWidth(row1)
  // When the view is deactivated via KeepAlive, elements are detached and
  // getBoundingClientRect returns 0. Scheduling checkTabsFit from a detached
  // state causes an infinite loop (labelW stays 0 → endless nextTick retries).
  if (w === 0) return
  const wasVeryNarrow = isVeryNarrow.value
  isVeryNarrow.value = w < 480
  if (!wasVeryNarrow && isVeryNarrow.value && uiStore.density !== 'normal') uiStore.density = 'normal'
  checkLangFit()
  nextTick(() => checkTabsFit())
}

let headerResizeObserver: ResizeObserver | null = null

watch(
  [() => groupsStore.filteredTabs.map((t) => t.name).join('|'), tabEditName],
  () => { nextTick(() => checkHeaderLayout()) },
)
watch(
  () => groupsStore.filteredTabs.length,
  () => { nextTick(() => checkTabsFit()) },
)
// Re-check when label text changes (width may change: "42" vs "42 entries")
watch(entryCountLabel, () => { nextTick(() => checkTabsFit()) })
// Re-check when the overflow flag flips: the button text toggles between
// "New" and "more...", which have different widths. The first checkTabsFit
// call that sets groupsOverflow uses the old button width; this watch fires
// after Vue re-renders the button so the follow-up call measures the new
// width and updates _maxSeenBtnW before the browser paints.
watch(groupsOverflow, () => { nextTick(() => checkTabsFit()) })

// ─── Search ──────────────────────────────────────────────────────────────────

const SEARCH_FIXED_WIDTH = 250  // px — fixed width of the search input box
const SEARCH_RESULT_LIMIT = 10  // max results returned by the search API

const searchActive = ref(false)
const searchQuery = ref('')
const searchResults = ref<WordbookSearchEntry[]>([])
const searchLoading = ref(false)
const searchDone = ref(false)
const searchContainerEl = ref<HTMLElement | null>(null)
const searchInputEl = ref<HTMLInputElement | null>(null)
const searchResultsTableEl = ref<HTMLElement | null>(null)
const searchToolbarHidden = ref(false)
const focusedResultIndex = ref(-1)

// ─── Search togglers (in-memory; not reset on cancelSearch) ──────────────────
// Toggler 1: strict lang-pair filter when active (non-relaxed search)
const searchUseLangFilter = ref(true)
// Toggler 2: strict color filter when active (non-relaxed search)
const searchUseColorFilter = ref(false)
// Toggler 3: search_in param — three-state, synced bidirectionally with swapDisplay
const searchIn = ref<'source_text' | 'target_text' | 'notes'>(
  uiStore.swapDisplay ? 'target_text' : 'source_text',
)

const searchInTitle = computed(() => {
  if (searchIn.value === 'source_text') return 'Search in source text'
  if (searchIn.value === 'target_text') return 'Search in target text'
  return 'Search in notes'
})

function toggleSearchLangFilter() {
  searchUseLangFilter.value = !searchUseLangFilter.value
}

function toggleSearchColorFilter() {
  searchUseColorFilter.value = !searchUseColorFilter.value
}

function cycleSearchIn() {
  if (searchIn.value === 'source_text') {
    searchIn.value = 'target_text'
    uiStore.swapDisplay = true
  } else if (searchIn.value === 'target_text') {
    searchIn.value = 'notes'
    uiStore.swapDisplay = false
  } else {
    searchIn.value = 'source_text'
    // swapDisplay is already false; no change needed
  }
}

let _searchDebounceTimer: ReturnType<typeof setTimeout> | null = null
let _searchSeq = 0

function clearSearchQuery() {
  if (_searchDebounceTimer !== null) { clearTimeout(_searchDebounceTimer); _searchDebounceTimer = null }
  searchQuery.value = ''
  searchResults.value = []
  searchDone.value = false
  focusedResultIndex.value = -1
  searchInputEl.value?.focus()
}

async function activateSearch() {
  searchActive.value = true
  await nextTick()
  searchInputEl.value?.focus()
  document.addEventListener('click', onSearchOutsideClick, true)
}

function cancelSearch() {
  if (_searchDebounceTimer !== null) { clearTimeout(_searchDebounceTimer); _searchDebounceTimer = null }
  searchActive.value = false
  searchQuery.value = ''
  searchResults.value = []
  searchLoading.value = false
  searchDone.value = false
  focusedResultIndex.value = -1
  document.removeEventListener('click', onSearchOutsideClick, true)
}

function onSearchOutsideClick(e: MouseEvent) {
  const target = e.target as Node | null
  if (!target || searchContainerEl.value?.contains(target)) return
  cancelSearch()
}

function onSearchKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape') { e.preventDefault(); cancelSearch(); return }
  const count = searchResults.value.length
  if (!count) return
  if (e.key === 'ArrowDown') {
    e.preventDefault()
    focusedResultIndex.value = Math.min(focusedResultIndex.value + 1, count - 1)
    nextTick(() => {
      const rows = searchResultsTableEl.value?.querySelectorAll<HTMLElement>('tr')
      rows?.[focusedResultIndex.value]?.scrollIntoView({ block: 'nearest' })
    })
  } else if (e.key === 'ArrowUp') {
    e.preventDefault()
    focusedResultIndex.value = Math.max(focusedResultIndex.value - 1, -1)
    if (focusedResultIndex.value >= 0) {
      nextTick(() => {
        const rows = searchResultsTableEl.value?.querySelectorAll<HTMLElement>('tr')
        rows?.[focusedResultIndex.value]?.scrollIntoView({ block: 'nearest' })
      })
    }
  } else if (e.key === 'Enter' && focusedResultIndex.value >= 0) {
    e.preventDefault()
    navigateToResult(searchResults.value[focusedResultIndex.value])
  }
}

function onSearchInput() {
  searchResults.value = []
  searchDone.value = false
  focusedResultIndex.value = -1
  if (_searchDebounceTimer !== null) { clearTimeout(_searchDebounceTimer); _searchDebounceTimer = null }
  if (searchQuery.value.trim().length < 2) return
  _searchDebounceTimer = setTimeout(runSearch, 300)
}

async function runSearch() {
  const seq = ++_searchSeq
  const q = searchQuery.value.trim()
  if (q.length < 2) return
  searchLoading.value = true
  try {
    const relaxedFilters: Array<'lang_pairs' | 'colors'> = []
    if (!searchUseLangFilter.value) relaxedFilters.push('lang_pairs')
    if (!searchUseColorFilter.value) relaxedFilters.push('colors')
    const resp = await wordbookApi.search(
      q,
      searchIn.value,
      uiStore.activeLangs,
      uiStore.activeColors,
      relaxedFilters,
      SEARCH_RESULT_LIMIT,
    )
    if (seq !== _searchSeq) return
    searchResults.value = resp.results
  } catch {
    if (seq !== _searchSeq) return
    searchResults.value = []
  } finally {
    if (seq === _searchSeq) { searchLoading.value = false; searchDone.value = true }
  }
}

function _showFilterChangeToast(langsBefore: string[], colorsBefore: string[]) {
  const parts: string[] = []
  const addedLang = uiStore.activeLangs.find(l => !langsBefore.includes(l))
  if (addedLang) {
    const [src, tgt] = addedLang.split(':', 2)
    parts.push(uiStore.swapDisplay ? `${tgt} ← ${src}` : `${src} → ${tgt}`)
  }
  const addedColor = uiStore.activeColors.find(c => !colorsBefore.includes(c))
  if (addedColor) {
    parts.push(addedColor === 'none' ? 'No color' : (isEntryColor(addedColor) ? ENTRY_COLOR_LABEL[addedColor as EntryColor] : addedColor))
  }
  if (parts.length > 0) toast.warn(`Filters expanded with: ${parts.join(', ')}`)
}

function navigateToResult(result: WordbookSearchEntry) {
  cancelSearch()
  _histNavStart()
  recordNavHistoryEntry(result)
  const langsBefore = [...uiStore.activeLangs]
  const colorsBefore = [...uiStore.activeColors]
  uiStore.requestShowEntry(
    result.id,
    `${result.source_lang}:${result.target_lang}`,
    result.group.id,
    result.color ?? null,
  )
  _showFilterChangeToast(langsBefore, colorsBefore)
  _histNavEndSoon(500)
}

function resultColorBg(result: WordbookSearchEntry): string {
  if (!result.color || !isEntryColor(result.color)) return ''
  return ENTRY_COLOR_CARD_BG[result.color as EntryColor]
}

function resultColorBgHover(result: WordbookSearchEntry): string {
  if (!result.color || !isEntryColor(result.color)) return ''
  return ENTRY_COLOR_CARD_BG_FOCUSED[result.color as EntryColor]
}

const hoveredResultId = ref<number | null>(null)

function formatSearchLangPair(result: WordbookSearchEntry): string {
  if (!uiStore.swapDisplay) return `${result.source_lang}→${result.target_lang}`
  return `${result.target_lang}←${result.source_lang}`
}

// Sync searchIn toggler when swapDisplay changes externally (e.g. toolbar button).
// The combined toggler watcher below handles any resulting re-search.
watch(() => uiStore.swapDisplay, (newVal) => {
  if (newVal && searchIn.value !== 'target_text') {
    searchIn.value = 'target_text'
  } else if (!newVal && searchIn.value === 'target_text') {
    searchIn.value = 'source_text'
  }
})
// Re-search when any search toggler changes while search is active.
watch([searchUseLangFilter, searchUseColorFilter, searchIn], () => {
  if (searchActive.value && searchQuery.value.trim().length >= 2) {
    searchResults.value = []
    runSearch()
  }
})
// Recompute search layout whenever search mode is toggled.
watch(searchActive, () => { nextTick(() => checkLangFit()) })

// ─── Navigation history ─────────────────────────────────────────────────────
// Records transitions made via search-result and similarity-popup clicks so
// the user can navigate back (Ctrl+Z) and forward (Ctrl+Y / Ctrl+Shift+Z).
// History is kept in-memory only; it is cleared when the active group changes
// or the focused entry changes from a direct user action (card click, side
// panel, etc.). Search/popup clicks and Ctrl+Z/Y navigation suppress clearing
// via the _histNavInProgress flag.

interface NavHistoryEntry {
  id: number
  pair: string          // 'source_lang:target_lang'
  groupId: number | null
  color: string | null
}

const navHistory = ref<NavHistoryEntry[]>([])
const navHistoryCursor = ref(-1)
let _histNavInProgress = false
let _histNavTimer: ReturnType<typeof setTimeout> | null = null

function clearNavHistory() {
  navHistory.value = []
  navHistoryCursor.value = -1
}

function recordNavHistoryEntry(result: WordbookSearchEntry) {
  const dest: NavHistoryEntry = {
    id: result.id,
    pair: `${result.source_lang}:${result.target_lang}`,
    groupId: result.group.id,
    color: result.color ?? null,
  }

  // Truncate the tail when recording from mid-history
  const cutAt = navHistoryCursor.value + 1
  if (cutAt < navHistory.value.length) {
    navHistory.value = navHistory.value.slice(0, cutAt)
  }

  // Record the current focused entry as the source (where the user is navigating
  // FROM) so that Ctrl+Z can return to it.
  const focusedId = uiStore.getFocusedEntry(uiStore.activeGroupId)
  if (focusedId !== undefined) {
    const srcEntry = store.entries.find(e => e.id === focusedId)
    if (srcEntry) {
      const src: NavHistoryEntry = {
        id: srcEntry.id,
        pair: `${srcEntry.source_lang}:${srcEntry.target_lang}`,
        groupId: srcEntry.group.id,
        color: srcEntry.color ?? null,
      }
      const last = navHistory.value[navHistory.value.length - 1]
      if (!last || last.id !== src.id) navHistory.value.push(src)
    }
  }

  // Record the destination so Ctrl+Y can go forward to it.
  const last = navHistory.value[navHistory.value.length - 1]
  if (!last || last.id !== dest.id) navHistory.value.push(dest)

  navHistoryCursor.value = navHistory.value.length - 1
}

function _histNavStart() {
  if (_histNavTimer !== null) { clearTimeout(_histNavTimer); _histNavTimer = null }
  _histNavInProgress = true
}

function _histNavEndSoon(ms = 0) {
  if (_histNavTimer !== null) clearTimeout(_histNavTimer)
  _histNavTimer = setTimeout(() => { _histNavTimer = null; _histNavInProgress = false }, ms)
}

// Clear history when the active group changes unless a history/search op is in flight.
watch(
  () => uiStore.activeGroupId,
  (newId, oldId) => {
    if (newId !== oldId && !_histNavInProgress) clearNavHistory()
  },
)

// Clear history when the focused entry in the current group changes via a
// direct user action (card click, side-panel, find-similar, etc.).
watch(
  () => uiStore.getFocusedEntry(uiStore.activeGroupId),
  () => {
    if (!_histNavInProgress) clearNavHistory()
  },
)

function _navHistNavigate(entry: NavHistoryEntry) {
  _histNavStart()
  uiStore.requestShowEntry(entry.id, entry.pair, entry.groupId, entry.color)
  _histNavEndSoon(500)
}

function navigateHistoryBack() {
  if (navHistoryCursor.value <= 0) return
  navHistoryCursor.value--
  _navHistNavigate(navHistory.value[navHistoryCursor.value])
}

function navigateHistoryForward() {
  if (navHistoryCursor.value >= navHistory.value.length - 1) return
  navHistoryCursor.value++
  _navHistNavigate(navHistory.value[navHistoryCursor.value])
}

function onNavHistoryKeyDown(e: KeyboardEvent) {
  if (!viewIsActive.value) return
  const target = e.target as HTMLElement
  if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return
  if (!e.ctrlKey || e.metaKey) return
  if (e.key === 'z' && !e.shiftKey) {
    e.preventDefault()
    navigateHistoryBack()
  } else if (e.key === 'y' && !e.shiftKey) {
    e.preventDefault()
    navigateHistoryForward()
  } else if (e.shiftKey && (e.key === 'Z' || e.key === 'z')) {
    e.preventDefault()
    navigateHistoryForward()
  }
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
    uiStore.clearFocusedEntryById(pendingDeleteId.value)
    uiStore.clearDetailsContent(pendingDeleteId.value)
    // Refresh lang-pairs in case this was the last entry with that pair.
    groupsStore.fetchLangPairs().catch(() => {})
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to delete entry'))
  } finally {
    pendingDeleteId.value = null
  }
}

function handleFindSimilarEntry(id: number) {
  const entry = store.entries.find((e) => e.id === id)
  if (!entry) return
  uiStore.setFocusedEntry(id, entry.group.id)
  if (uiStore.activeCardMode === 'details') uiStore.closeActive()
  showEntryContextPopup(entry)
}

async function handleMoveEntry(id: number, groupId: number) {
  try {
    await groupsStore.assignEntry(id, groupId)
    uiStore.clearFocusedEntryById(id)
    uiStore.clearDetailsContent(id)
    groupsStore.fetchLangPairs().catch(() => {})
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to move entry'))
  }
}

async function handleUpdate(
  id: number,
  data: { source_text?: string; target_text?: string; notes?: string; provider_code?: string | null; color?: string | null },
) {
  try {
    await store.updateEntry(id, data)
    // Source text may have changed — clear cached panel content so the
    // next time details opens it fetches fresh definitions/examples.
    if (data.source_text !== undefined) uiStore.clearDetailsContent(id)
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to save changes'))
  }
}

// ─── Drag and drop ────────────────────────────────────────────────────────────

// Card reorder drag
const draggedId = ref<number | null>(null)
const cardDragSourceEl = ref<HTMLElement | null>(null)
/** Last pointer type that touched the card grid; used to suppress HTML5 DnD on touch. */
let _lastCardPointerType = 'mouse'

// Touch long-press card reorder state (Android)
// After a long-press reorder, the bubble-phase pointerup handler restores
// focus to the moved entry (overriding the card's capture-phase setFocused).
let _reorderFocusRestore: { entryId: number; groupId: number | null } | null = null

interface CardLongPressState {
  entryId: number
  pointerId: number
  startX: number
  startY: number
}
const cardLongPressState = ref<CardLongPressState | null>(null)
let cardLongPressTimer: ReturnType<typeof setTimeout> | null = null

function clearCardLongPress() {
  if (cardLongPressTimer !== null) { clearTimeout(cardLongPressTimer); cardLongPressTimer = null }
  cardLongPressState.value = null
}

// Tab → card group assignment drag, OR tab → tab reorder drag
// (custom pointer-based, single state machine for both)
const draggedTabId = ref<number | null>(null)
const dragOverId = ref<number | null>(null)
const dragOverTabId = ref<number | null>(null)
const dragOverDeleteZone = ref(false)

const DRAG_THRESHOLD = 5

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

function onTabPointerDown(event: PointerEvent, tabId: number) {
  if (editingTabId.value === tabId) return
  if (editingTabId.value !== null) saveTabEdit(editingTabId.value)
  if (editingPopupTabId.value !== null) saveTabEdit(editingPopupTabId.value)
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
    // Tab long-press uses a two-step mechanism deliberately:
    //  1. The timer fires at LONG_PRESS_MS and sets longPressReadyTabId, which
    //     only changes the cursor to cursor-text — a mid-hold visual cue that
    //     "releasing now will rename this tab".
    //  2. The actual rename action is committed in onTabPointerUp via an elapsed
    //     check, so it triggers on release rather than mid-gesture.
    // This action-on-release pattern gives the user a clear visual signal
    // before committing, and lets them abort by dragging instead of releasing.
    clearLongPressTimer()
    longPressTimerId = setTimeout(() => {
      longPressTimerId = null
      if (tabInteraction.value && !tabInteraction.value.isDragging) longPressReadyTabId.value = tabId
    }, LONG_PRESS_MS)
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
    // Prefer another tab as drop target (→ reorder); fall back to the
    // delete zone (→ delete group) or a card (→ assign-to-group).
    // Hovering over self is a no-op.
    const tabEl = under.find(el => {
      const raw = el.getAttribute('data-tab-id')
      return raw !== null && Number(raw) !== state.tabId
    })
    if (tabEl) {
      dragOverTabId.value = Number(tabEl.getAttribute('data-tab-id'))
      dragOverId.value = null
      dragOverDeleteZone.value = false
    } else {
      dragOverTabId.value = null
      const deleteZoneEl = under.find(el => el.hasAttribute('data-delete-tab-zone'))
      if (deleteZoneEl) {
        dragOverDeleteZone.value = true
        dragOverId.value = null
      } else {
        dragOverDeleteZone.value = false
        const cardEl = under.find(el => el.hasAttribute('data-entry-id'))
        dragOverId.value = cardEl ? Number(cardEl.getAttribute('data-entry-id')) : null
      }
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
    if (dragOverDeleteZone.value) {
      deleteTab(state.tabId)
    } else if (dragOverTabId.value !== null && dragOverTabId.value !== state.tabId) {
      // Reorder tabs: insert dragged tab at the target's position. Mirrors
      // the entry reorder logic in onCardDrop.
      groupsStore.reorderTabs(state.tabId, dragOverTabId.value)
    } else if (dragOverId.value !== null) {
      groupsStore.assignEntry(dragOverId.value, state.tabId).catch((e: unknown) => {
        toast.error(extractErrorMessage(e, 'Failed to assign group'))
      })
    }
    draggedTabId.value = null
    dragOverId.value = null
    dragOverTabId.value = null
    dragOverDeleteZone.value = false
    return
  }
  // Elapsed check is the second half of the two-step tab long-press (see
  // onTabPointerDown). The timer already showed the visual preview; this
  // commits the rename (or falls back to select) on release.
  const elapsed = Date.now() - state.startTime
  if (state.onDeleteButton) {
    deleteTab(state.tabId)
  } else if (elapsed < LONG_PRESS_MS) {
    selectTab(state.tabId)
  } else {
    const tab = groupsStore.filteredTabs.find(t => t.id === state.tabId)
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
  dragOverDeleteZone.value = false
}

// Card reorder drag (HTML5)
function onCardGridPointerDown(e: PointerEvent) {
  _lastCardPointerType = e.pointerType
  const target = e.target as Element | null
  if (!target) return
  // Don't arm any long-press when pressing on the open details overlay.
  if (target.closest('[data-details-overlay]')) return
  // Don't arm long-press when pressing on interactive card children
  // (buttons, links, inputs, or the hint-toggle span).
  if (target.closest('button, input, textarea, a, [data-hint-toggle]')) return
  const cardEl = target.closest('[data-entry-id]') as HTMLElement | null
  if (!cardEl) return
  const entryId = Number(cardEl.getAttribute('data-entry-id'))
  if (isNaN(entryId)) return
  const entry = filteredEntries.value.find((en) => en.id === entryId)
  if (!entry) return
  const groupId = entry.group.id
  // Touch only: long-press on an unfocused card reorders the focused card here.
  if (e.pointerType !== 'touch') return
  const focusedId = uiStore.getFocusedEntry(groupId)
  if (!focusedId) return
  clearCardLongPress()
  cardLongPressState.value = { entryId, pointerId: e.pointerId, startX: e.clientX, startY: e.clientY }
  cardLongPressTimer = setTimeout(() => {
    cardLongPressTimer = null
    const state = cardLongPressState.value
    if (!state || state.entryId !== entryId) return
    const currentFocused = uiStore.getFocusedEntry(groupId)
    if (!currentFocused || currentFocused === entryId) { clearCardLongPress(); return }
    // Guard: focused entry must still be visible in the current filter.
    if (!filteredEntries.value.some((en) => en.id === currentFocused)) { clearCardLongPress(); return }
    performCardReorder(currentFocused, entryId)
    _reorderFocusRestore = { entryId: currentFocused, groupId: groupId as number | null }
    clearCardLongPress()
  }, LONG_PRESS_MS)
}

function onCardGridPointerMove(e: PointerEvent) {
  const state = cardLongPressState.value
  if (!state || state.pointerId !== e.pointerId) return
  const dx = e.clientX - state.startX
  const dy = e.clientY - state.startY
  if (Math.abs(dx) > DRAG_THRESHOLD || Math.abs(dy) > DRAG_THRESHOLD) clearCardLongPress()
}

function onCardGridPointerUpOrCancel(e: PointerEvent) {
  // Bubble phase: fires after the card's capture-phase setFocused().
  // If a long-press reorder just happened, override focus back to the moved entry.
  if (_reorderFocusRestore) {
    uiStore.setFocusedEntry(_reorderFocusRestore.entryId, _reorderFocusRestore.groupId)
    _reorderFocusRestore = null
  }
  const state = cardLongPressState.value
  if (state && state.pointerId === e.pointerId) clearCardLongPress()
}

function onDragStart(event: DragEvent, entryId: number) {
  // Card drag is desktop-only; suppress it on touch (Android).
  if (_lastCardPointerType === 'touch') { event.preventDefault(); return }
  // If the gesture started inside the details overlay, cancel the card drag
  // so the browser falls back to normal text-selection behaviour.
  if (document.elementsFromPoint(event.clientX, event.clientY)
      .some(el => el.hasAttribute('data-details-overlay'))) {
    event.preventDefault()
    return
  }
  draggedId.value = entryId
  const draggedEntry = store.entries.find((e) => e.id === entryId)
  if (draggedEntry) uiStore.setFocusedEntry(entryId, draggedEntry.group.id)
  if (event.dataTransfer) event.dataTransfer.effectAllowed = 'move'
  cardDragSourceEl.value = event.currentTarget as HTMLElement
  cardDragSourceEl.value.style.opacity = '0.4'
  // Close any active overlay on this card (details panel) and its action menu.
  // Editing is already prevented by the :draggable guard, so activeCardMode
  // can only be 'details' here — no need to check the mode explicitly.
  uiStore.activeMenuId = null
  if (uiStore.activeCardId === entryId) uiStore.closeActive()
}

function onCardDragOver(entryId: number) {
  if (!draggedId.value) return
  dragOverId.value = entryId
}

function onCardDragLeave() {
  dragOverId.value = null
}

/** Shared reorder logic: move `draggedEntryId` to `targetEntryId`'s position. */
function performCardReorder(draggedEntryId: number, targetEntryId: number) {
  const prevAllIds = store.entries.map((e) => e.id)

  const filteredIds = filteredEntries.value.map((e) => e.id)
  const movingForward = filteredIds.indexOf(draggedEntryId) < filteredIds.indexOf(targetEntryId)
  const newFiltered = filteredIds.filter((id) => id !== draggedEntryId)
  const targetIdx = newFiltered.indexOf(targetEntryId)
  newFiltered.splice(movingForward ? targetIdx + 1 : targetIdx, 0, draggedEntryId)
  const filteredSet = new Set(filteredIds)
  const allIds = store.entries.map((e) => e.id)
  let fi = 0
  const newOrder = allIds.map((id) => (filteredSet.has(id) ? newFiltered[fi++] : id))
  store.reorderEntries(newOrder, draggedEntryId, targetEntryId)

  // Compute the undo target: entry that was immediately after draggedEntryId in the
  // previous order, or the one before it if it was last.
  const prevIdx = prevAllIds.indexOf(draggedEntryId)
  const undoTargetId = prevIdx + 1 < prevAllIds.length
    ? prevAllIds[prevIdx + 1]
    : prevAllIds[prevIdx - 1]

  toast.undo('Entries reordered', () => {
    store.reorderEntries(prevAllIds, draggedEntryId, undoTargetId)
  })
}

function onCardDrop(targetEntryId: number) {
  const dragged = draggedId.value
  if (!dragged || dragged === targetEntryId) { onDragEnd(); return }
  performCardReorder(dragged, targetEntryId)
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

// ─── Entry context popup (long-press on details button) ─────────────────────────

interface EntryContextPopupState {
  entry: WordbookEntryData
  results: WordbookSearchEntry[]
  loading: boolean
  done: boolean
  anchorLeft: number
  anchorWidth: number
  anchorBottom: number
  anchorTop: number
}

const entryContextPopup = ref<EntryContextPopupState | null>(null)
const entryContextPopupEl = ref<HTMLElement | null>(null)
const hoveredContextResultId = ref<number | null>(null)
function closeEntryContextPopup() {
  entryContextPopup.value = null
  hoveredContextResultId.value = null
}

function onEntryContextPopupOutsidePointerDown(e: PointerEvent) {
  const target = e.target as Node | null
  if (!target || entryContextPopupEl.value?.contains(target)) return
  closeEntryContextPopup()
}

/** Re-read the anchor card's viewport rect and update the popup position on scroll/resize. */
function _updateEntryContextPopupPosition() {
  if (!entryContextPopup.value) return
  const entry = entryContextPopup.value.entry
  const cardEl = document.querySelector(`[data-entry-id="${entry.id}"]:not([data-details-overlay])`) as HTMLElement | null
  if (!cardEl) return
  const rect = cardEl.getBoundingClientRect()
  entryContextPopup.value = {
    ...entryContextPopup.value,
    anchorLeft: rect.left,
    anchorWidth: rect.width,
    anchorBottom: rect.bottom,
    anchorTop: rect.top,
  }
}

// Watch the open/closed boolean rather than the object reference so position
// updates (which replace the object) don't re-register the same listeners.
watch(() => !!entryContextPopup.value, (open) => {
  if (open) {
    document.addEventListener('pointerdown', onEntryContextPopupOutsidePointerDown, true)
    window.addEventListener('scroll', closeEntryContextPopup, { passive: true, capture: true })
    window.addEventListener('resize', _updateEntryContextPopupPosition)
  } else {
    document.removeEventListener('pointerdown', onEntryContextPopupOutsidePointerDown, true)
    window.removeEventListener('scroll', closeEntryContextPopup, { capture: true } as EventListenerOptions)
    window.removeEventListener('resize', _updateEntryContextPopupPosition)
  }
})

async function showEntryContextPopup(entry: WordbookEntryData) {
  // Use the card wrapper's rect for positioning (excludes the overlay child).
  const cardEl = document.querySelector(`[data-entry-id="${entry.id}"]:not([data-details-overlay])`) as HTMLElement | null
  const rect = cardEl?.getBoundingClientRect()
  const anchorLeft = rect?.left ?? 0
  const anchorWidth = rect?.width ?? 240
  const anchorBottom = rect?.bottom ?? 0
  const anchorTop = rect?.top ?? 0

  const searchTerm = uiStore.swapDisplay ? entry.target_text : entry.source_text
  const langPair = `${entry.source_lang}:${entry.target_lang}`

  entryContextPopup.value = { entry, results: [], loading: true, done: false, anchorLeft, anchorWidth, anchorBottom, anchorTop }

  try {
    const resp = await wordbookApi.search(
      searchTerm,
      uiStore.swapDisplay ? 'target_text' : 'source_text',
      [langPair],
      uiStore.activeColors,
      ['colors'],
      SEARCH_RESULT_LIMIT + 1,
    )
    if (entryContextPopup.value?.entry.id === entry.id) {
      entryContextPopup.value = { ...entryContextPopup.value, results: resp.results.filter(r => r.id !== entry.id), loading: false, done: true }
    }
  } catch {
    if (entryContextPopup.value?.entry.id === entry.id) {
      entryContextPopup.value = { ...entryContextPopup.value, results: [], loading: false, done: true }
    }
  }
}

function navigateFromContextPopup(result: WordbookSearchEntry) {
  closeEntryContextPopup()
  _histNavStart()
  recordNavHistoryEntry(result)
  const langsBefore = [...uiStore.activeLangs]
  const colorsBefore = [...uiStore.activeColors]
  uiStore.requestShowEntry(
    result.id,
    `${result.source_lang}:${result.target_lang}`,
    result.group.id,
    result.color ?? null,
  )
  _showFilterChangeToast(langsBefore, colorsBefore)
  _histNavEndSoon(500)
}

function contextResultColorBg(result: WordbookSearchEntry): string {
  if (!result.color || !isEntryColor(result.color)) return ''
  return ENTRY_COLOR_CARD_BG[result.color as EntryColor]
}

function contextResultColorBgHover(result: WordbookSearchEntry): string {
  if (!result.color || !isEntryColor(result.color)) return ''
  return ENTRY_COLOR_CARD_BG_FOCUSED[result.color as EntryColor]
}

const entryContextPopupStyle = computed(() => {
  if (!entryContextPopup.value) return {}
  const { anchorLeft, anchorWidth, anchorBottom, anchorTop } = entryContextPopup.value
  const POPUP_MAX_HEIGHT = 240
  const spaceBelow = window.innerHeight - anchorBottom - 8
  const spaceAbove = anchorTop - 8
  if (spaceBelow >= 80 || spaceBelow >= spaceAbove) {
    return {
      left: `${anchorLeft}px`,
      top: `${anchorBottom + 4}px`,
      bottom: '',
      width: `${anchorWidth}px`,
      maxHeight: `${Math.min(POPUP_MAX_HEIGHT, Math.max(60, spaceBelow))}px`,
    }
  } else {
    return {
      left: `${anchorLeft}px`,
      top: '',
      bottom: `${window.innerHeight - anchorTop + 4}px`,
      width: `${anchorWidth}px`,
      maxHeight: `${Math.min(POPUP_MAX_HEIGHT, Math.max(60, spaceAbove))}px`,
    }
  }
})

// ─── Bottom-spacer flicker prevention ─────────────────────────────────────────
// The details overlay (`position: absolute; top: 100%`) causes cardsAreaEl to
// expand its scroll height when it extends past the grid's bottom edge.
// Switching to another entry (or tab) briefly collapses the old overlay before
// the new one grows, shrinking the scroll height and producing a visible jump.
//
// Fix: keep a zero-height spacer div anchored right after the grid. When the
// active overlay extends past the grid bottom, the spacer grows to exactly
// cover that overflow — holding the scroll height stable. It only shrinks
// once its "dead zone" (from the current overlay bottom down to the spacer
// bottom) scrolls entirely below the visible area of cardsAreaEl.

const gridEl = ref<HTMLElement | null>(null)
const spacerEl = ref<HTMLElement | null>(null)
const spacerHeight = ref(0)
let _overlayResizeObs: ResizeObserver | null = null

/** Pixels by which the active overlay extends past the grid's bottom edge. */
function _getOverlayOverflow(): number {
  if (!gridEl.value || uiStore.activeCardId === null || uiStore.activeCardMode !== 'details') return 0
  const overlayEl = cardsAreaEl.value?.querySelector<HTMLElement>(
    `[data-details-overlay][data-entry-id="${uiStore.activeCardId}"]`,
  )
  if (!overlayEl) return 0
  return Math.max(0, overlayEl.getBoundingClientRect().bottom - gridEl.value.getBoundingClientRect().bottom)
}

/** Grow the spacer when the active overlay overflows past the grid bottom. */
function updateSpacer() {
  const overflow = _getOverlayOverflow()
  if (overflow > spacerHeight.value) spacerHeight.value = overflow
}

/**
 * Shrink the spacer when its dead zone (between the current overlay's bottom
 * and the spacer's bottom) scrolls entirely below cardsAreaEl's visible fold.
 * Since both measurements are viewport-relative their difference is
 * scroll-invariant, making the comparison correct regardless of scroll offset.
 */
function checkSpacerShrink() {
  if (spacerHeight.value <= 0 || !cardsAreaEl.value || !gridEl.value) return
  const scrollBottom = cardsAreaEl.value.getBoundingClientRect().bottom
  // Dead-zone top = where the current overlay ends in the viewport.
  // Falls back to the grid bottom when no overlay is active.
  let deadZoneTop: number
  if (uiStore.activeCardId !== null && uiStore.activeCardMode === 'details') {
    const ov = cardsAreaEl.value.querySelector<HTMLElement>(
      `[data-details-overlay][data-entry-id="${uiStore.activeCardId}"]`,
    )
    deadZoneTop = ov
      ? ov.getBoundingClientRect().bottom
      : gridEl.value.getBoundingClientRect().bottom
  } else {
    deadZoneTop = gridEl.value.getBoundingClientRect().bottom
  }
  if (deadZoneTop >= scrollBottom || cardsAreaEl.value.scrollTop === 0) {
    const newH = Math.max(0, _getOverlayOverflow())
    if (newH < spacerHeight.value) spacerHeight.value = newH
  }
}

function _disconnectOverlayObs() {
  _overlayResizeObs?.disconnect()
  _overlayResizeObs = null
}

async function _connectOverlayObs() {
  _disconnectOverlayObs()
  const targetId = uiStore.activeCardId
  if (targetId === null || uiStore.activeCardMode !== 'details') return
  await nextTick()
  await new Promise<void>((r) => requestAnimationFrame(() => r()))
  // Guard: active card may have changed during the awaits.
  if (uiStore.activeCardId !== targetId || uiStore.activeCardMode !== 'details') return
  const overlayEl = cardsAreaEl.value?.querySelector<HTMLElement>(
    `[data-details-overlay][data-entry-id="${targetId}"]`,
  )
  if (!overlayEl || typeof ResizeObserver === 'undefined') return
  _overlayResizeObs = new ResizeObserver(updateSpacer)
  _overlayResizeObs.observe(overlayEl)
  updateSpacer()
}

// Reconnect the observer whenever the active card or mode changes.
watch(
  [() => uiStore.activeCardId, () => uiStore.activeCardMode],
  () => _connectOverlayObs(),
)

// ─── Back button ────────────────────────────────────────────────────────────
let _unregisterBack: (() => void) | null = null
onActivated(() => {
  _unregisterBack = registerBackHandler(() => {
    if (showDeleteDialog.value) { showDeleteDialog.value = false; return true }
    if (showDeleteTabDialog.value) { showDeleteTabDialog.value = false; return true }
    if (navHistoryCursor.value > 0) { navigateHistoryBack(); return true }
    return false
  })
})
onDeactivated(() => { _unregisterBack?.(); _unregisterBack = null })

// ─── Lifecycle ────────────────────────────────────────────────────────────────
// True while this view is the active route. Used to prevent the
// pendingHighlightId watcher from consuming the ID before the kept-alive view
// has actually been activated and is ready to scroll.
const viewIsActive = ref(false)

onMounted(() => {
  // Portrait detection
  if (window.matchMedia) {
    portraitMq = window.matchMedia('(orientation: portrait)')
    isPortrait.value = portraitMq.matches
    portraitMq.addEventListener('change', onPortraitChange)
  }
  // ResizeObserver on header rows + toolbar for layout re-checks
  if (typeof ResizeObserver !== 'undefined') {
    headerResizeObserver = new ResizeObserver(() => {
      checkHeaderLayout()
    })
    if (headerRow1El.value) headerResizeObserver.observe(headerRow1El.value)
    if (toolbarEl.value) headerResizeObserver.observe(toolbarEl.value)
    if (groupsRowEl.value) headerResizeObserver.observe(groupsRowEl.value)
  }
  nextTick(() => checkHeaderLayout())
  cardsAreaEl.value?.addEventListener('scroll', checkSpacerShrink, { passive: true })
  document.addEventListener('keydown', onNavHistoryKeyDown)
})

onBeforeUnmount(() => {
  portraitMq?.removeEventListener('change', onPortraitChange)
  headerResizeObserver?.disconnect()
  clearCardLongPress()
  clearPopupLongPressTimer()
  _disconnectOverlayObs()
  cardsAreaEl.value?.removeEventListener('scroll', checkSpacerShrink)
  document.removeEventListener('click', onColorFilterOutsideClick, true)
  document.removeEventListener('click', onLangPopupOutsideClick, true)
  document.removeEventListener('click', onGroupsPopupOutsideClick, true)
  document.removeEventListener('click', onSidePanelOutsideClick, true)
  document.removeEventListener('pointerdown', onEntryContextPopupOutsidePointerDown, true)
  window.removeEventListener('scroll', closeEntryContextPopup, { capture: true } as EventListenerOptions)
  window.removeEventListener('resize', _updateEntryContextPopupPosition)
  document.removeEventListener('keydown', onNavHistoryKeyDown)
  cancelSearch()
  closeEntryContextPopup()
})

// Re-activated from <KeepAlive> when the user navigates back to this view
// (e.g. from TranslatorView via the “already in wordbook” checkmark).
onActivated(async () => {
  viewIsActive.value = true
  // Capture the target group at the start of this activation. If the user
  // switches a group tab before the fetches below complete, the stale check
  // below ensures we don't prune the wrong group's in-memory map.
  const activatedGroupId = uiStore.activeGroupId
  // Restore scroll immediately so the view appears at the saved position
  // from the first visible frame, rather than jumping from 0 after the
  // async fetch below completes. KeepAlive guarantees the DOM (and therefore
  // cardsAreaEl) is already mounted when onActivated fires.
  if (cardsAreaEl.value) {
    const saved = groupScrollPositions.get(activatedGroupId ?? null)
    if (saved !== undefined) cardsAreaEl.value.scrollTop = saved
  }
  // Restore the open card immediately using stale entries — eliminates the
  // visible close/reopen flicker. prune() will clear activeCardId if the
  // entry was deleted while away.
  restoreDetailsIfEntryExists(uiStore.getOpenDetailsForGroup(activatedGroupId ?? null))
  // Run all three fetches in parallel — they are independent. Old entries
  // remain visible while the refresh is in flight (stale-while-revalidate),
  // so no loading skeleton is shown on activation.
  const langPairsTask = groupsStore.fetchLangPairs()
  const groupsTask = groupsStore.fetchGroups(uiStore.activeLangs.length > 0 ? [...uiStore.activeLangs] : undefined)
  uiStore.switchGroup(activatedGroupId)
  if (activatedGroupId !== null) {
    await store.fetchEntries(activatedGroupId, uiStore.activeLangs.length > 0 ? [...uiStore.activeLangs] : undefined)
    // Guard: if the user switched a group tab while the fetch was in flight,
    // the group-switch watcher has already taken over — skip prune so it
    // doesn't run against the wrong group's in-memory map.
    if (uiStore.activeGroupId === activatedGroupId) {
      uiStore.prune(store.entries.map((e) => e.id))
    }
  }
  await Promise.all([langPairsTask, groupsTask])
  uiStore.initActiveGroup(groupsStore.filteredTabs)
  handlePendingHighlight()
})

onDeactivated(() => {
  viewIsActive.value = false
  uiStore.saveOpenDetailsForGroup(uiStore.activeGroupId ?? null)
  showColorFilter.value = false
  showLangPopup.value = false
  showGroupsPopup.value = false
  dismissSidePanel()
  uiStore.closeActive()
  uiStore.activeMenuId = null
  clearCardLongPress()
  clearLongPressTimer()
  tabInteraction.value = null
  _reorderFocusRestore = null
  cancelSearch()
  closeEntryContextPopup()
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
