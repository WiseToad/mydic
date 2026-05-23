<template>
  <div class="max-w-5xl mx-auto w-full flex-1 min-h-0 flex flex-col py-3">
  <div class="flex-1 min-h-0 overflow-y-auto">
  <div class="space-y-2">
    <!-- History navigation + language selectors -->
    <div class="relative flex items-center gap-3 flex-wrap">
      <!-- Back / Forward / Remove current -->
      <div class="flex gap-1">
        <button
          :disabled="!store.canGoBack"
          title="Go back"
          class="w-8 h-8 rounded-full flex items-center justify-center text-gray-500 hover:text-gray-200 hover:bg-surface-800 disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
          @click="onGoBack"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/></svg>
        </button>
        <button
          :disabled="!store.canGoForward"
          title="Go forward"
          class="w-8 h-8 rounded-full flex items-center justify-center text-gray-500 hover:text-gray-200 hover:bg-surface-800 disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
          @click="onGoForward"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8-8-8z"/></svg>
        </button>
        <!-- Remove current history entry -->
        <button
          v-if="store.historyIndex >= 0"
          title="Remove this entry from history"
          class="w-8 h-8 rounded-full flex items-center justify-center text-gray-600 hover:text-red-400 hover:bg-red-500/10 transition-colors"
          @click="onRemoveCurrentEntry"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
        </button>
      </div>

      <!-- Spacer -->
      <div class="flex-1" />

      <!-- Clear entire history -->
      <button
        v-if="store.historyIndex >= 0"
        title="Clear all history"
        class="flex items-center gap-1.5 text-sm text-gray-500 hover:text-red-400 transition-colors"
        @click="showClearHistoryDialog = true"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="currentColor"><path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
        Clear history
      </button>

      <!-- Swap languages button - absolutely centered -->
      <button
        :disabled="isSwapDisabled"
        :title="isSwapDisabled ? 'Cannot swap: detected language is disabled' : 'Swap languages (long press to clear & swap)'"
        class="absolute left-1/2 -translate-x-1/2 w-8 h-8 rounded-full flex items-center justify-center text-gray-400 hover:text-primary-400 hover:bg-surface-800 disabled:opacity-25 disabled:cursor-not-allowed transition-colors"
      @mousedown="onSwapPointerDown"
        @touchstart.prevent="onSwapPointerDown"
        @mouseup="onSwapPointerUp"
        @mouseleave="onSwapPointerUp"
        @touchend="onSwapTouchEnd"
        @touchcancel="onSwapPointerUp"
        @click="onSwapClick"
      >
        <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M6.99 12L3 16l3.99 4v-3H14v-2H6.99v-3zm14.02-1l-3.99-4v3H10v2h7.02v3L21 11z"/></svg>
      </button>
    </div>

      <!-- Single unified card. Sub-panels share the card background;
         thin dividers separate columns and rows instead of color difference. -->
    <div class="card overflow-hidden">
      <!-- Input / Result row -->
      <!--
        On mobile the two panels stack vertically and must be equal height.
        A CSS grid with `grid-template-rows: minmax(0,1fr) auto minmax(0,1fr)`
        and a fixed container height achieves this: both panel rows get exactly
        half the available height regardless of content length. On desktop
        (desk:) the layout switches to a single-row three-column grid so panels
        sit side-by-side and stretch to equal height automatically.
      -->
      <div ref="panelGridRef" :style="panelGridStyle" class="grid h-96 desk:h-auto [grid-template-rows:minmax(0,1fr)_auto_minmax(0,1fr)] desk:[grid-template-rows:auto] desk:[grid-template-columns:minmax(0,1fr)_auto_minmax(0,1fr)]">
        <!-- Source panel -->
        <div class="flex-1 p-4 flex flex-col gap-2 min-h-0 overflow-y-auto desk:overflow-visible">
          <div class="flex items-center gap-2 h-8">
            <select v-model="store.sourceLang" class="bg-surface-800 border border-surface-700 text-gray-200 rounded-lg px-2.5 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-colors" @change="retranslate">
              <option value="auto">Auto-detect</option>
              <!-- Ghost: code unknown to the language registry -->
              <option
                v-if="store.sourceLang !== 'auto' && !langStore.languages.some(l => l.code === store.sourceLang)"
                :value="store.sourceLang"
                disabled
              >🛇 {{ store.sourceLang }}</option>
              <!-- Enabled langs + current history entry's lang when it is disabled -->
              <option
                v-for="lang in visibleSourceLangs"
                :key="lang.code"
                :value="lang.code"
                :disabled="!lang.enabled"
                :title="!lang.enabled ? 'Excluded' : undefined"
              >{{ !lang.enabled ? `🛇 ${lang.name}` : lang.name }}</option>
            </select>
            <!--
              Detected lang badge: clickable when the detected language is
              enabled in the user's preferences (i.e. it appears as a
              selectable option in the source-language dropdown). Clicking
              "pins" the source to that language and re-translates.
            -->
            <button
              v-if="store.sourceLang === 'auto' && store.result?.detected_lang && detectedLangIsEnabled"
              class="text-sm text-primary-400 hover:text-primary-300 transition-colors"
              :title="`Pin source language to ${langStore.enabledLangs.find(l => l.code === store.result!.detected_lang)?.name ?? store.result!.detected_lang}`"
              @click="onDetectedLangClick"
            >
              {{ store.result.detected_lang }}
            </button>
            <span
              v-else-if="store.sourceLang === 'auto' && store.result?.detected_lang"
              class="text-sm text-gray-400"
              :title="store.result!.detected_lang_name ?? langStore.languages.find(l => l.code === store.result!.detected_lang)?.name"
            >
              {{ store.result.detected_lang }}
            </span>
            <div class="flex-1" />
            <!-- Already saved: click to jump to the wordbook card -->
            <button
              v-if="store.result && isAlreadyInWordbook && hasEnabledAvailableTranslationProvider"
              title="Already in Wordbook — show it"
              class="inline-flex items-center justify-center w-8 h-8 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/10 rounded-full transition-colors"
              @click="openInWordbook"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z"/></svg>
            </button>
            <!-- Not yet saved: add button (long-press to pick a group) -->
            <button
              v-else-if="store.result && hasEnabledAvailableTranslationProvider && !isSwapDisabled"
              ref="addToWordbookBtnRef"
              title="Add to Wordbook (long-press to pick group)"
              class="inline-flex items-center justify-center w-8 h-8 text-primary-400 hover:text-primary-300 hover:bg-primary-500/10 rounded-full transition-colors"
              @pointerdown.stop="onAddWordbookPointerDown"
              @pointerup.stop="onAddWordbookPointerUp"
              @pointerleave="onAddWordbookPointerUp"
              @pointercancel="onAddWordbookPointerUp"
              @click="onAddWordbookClick"
              @contextmenu.prevent
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10h-4v4h-2v-4H7v-2h4V7h2v4h4v2z"/></svg>
            </button>
            <button
              v-if="store.inputText"
              title="Clear input"
              class="inline-flex items-center justify-center w-8 h-8 text-gray-500 hover:text-gray-300 hover:bg-surface-800 rounded-full transition-colors"
              @click="clearInput"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="currentColor"><path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
            </button>
          </div>
          <textarea
            ref="inputTextareaRef"
            v-model="store.inputText"
            placeholder="Enter text to translate…"
            rows="4"
            maxlength="100"
            class="w-full flex-1 resize-none font-medium text-gray-100 placeholder:text-gray-600 bg-transparent focus:outline-none leading-relaxed overflow-y-auto"
            @input="onInput"
            @keydown="onInputActivity"
            @pointerdown="onInputPointerDown"
            @pointerup="onInputPointerUp"
            @pointercancel="onInputPointerCancel"
            @pointermove="onInputPointerMove"
            @keydown.ctrl.enter.prevent="onCtrlEnter"
          />
          <div class="flex items-center justify-between h-8">
            <AudioButton v-if="store.inputText" :text="store.inputText" :lang="resolvedSourceLang" title="Listen to input" />
<p v-if="store.inputText" class="text-xs text-gray-600 ml-auto">{{ store.inputText.length }} / 100</p>
          </div>
        </div>

        <!-- Unified divider: horizontal on mobile, vertical on desktop -->
        <div class="h-px desk:h-auto desk:w-px bg-surface-700 desk:mt-4" :class="{ 'desk:mb-4': !store.result }" />

        <!-- Result panel -->
        <div class="flex-1 p-4 flex flex-col gap-2 min-h-0 overflow-y-auto desk:overflow-visible">
          <div class="flex items-center gap-2 h-8">
            <!-- Target lang select hidden when no enabled langs exist and no history entry to display -->
            <select
              v-if="langStore.enabledLangs.length > 0 || store.historyIndex >= 0"
              v-model="store.targetLang"
              class="bg-surface-800 border border-surface-700 text-gray-200 rounded-lg px-2.5 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-colors"
              @change="retranslateExplicitTarget"
            >
              <!-- Ghost: target lang disabled in user prefs -->
              <option
                v-if="isTargetLangDisabled"
                :value="store.targetLang"
                disabled
                title="Excluded"
              >🛇 {{ langStore.languages.find(l => l.code === store.targetLang)?.name ?? store.targetLang }}</option>
              <!-- Ghost: target lang not in the language registry at all -->
              <option
                v-else-if="store.targetLang && !langStore.languages.some(l => l.code === store.targetLang)"
                :value="store.targetLang"
                disabled
              >🛇 {{ store.targetLang }}</option>
              <option v-for="lang in langStore.enabledLangs" :key="lang.code" :value="lang.code">{{ lang.name }}</option>
            </select>
            <div class="flex-1" />
            <!-- Translation provider selector (top-right of result panel).
                 Hidden when there are no enabled providers AND no saved code
                 to display as a ghost.  When hidden, the lexical selector is
                 implicitly hidden as well. -->
            <select
              v-if="translationDropdownVisible"
              class="bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-colors"
              title="Translation provider"
              @change="onProviderChange"
            >
              <!-- Saved provider not in the registry at all (ghost) -->
              <option
                v-if="ghostTranslationProviderCode"
                :value="ghostTranslationProviderCode"
                :selected="ghostTranslationProviderCode === dropdownTranslationCode"
                disabled
                title="Used for this history entry — no longer available"
              >🛇 {{ ghostTranslationProviderCode }}</option>
              <option
                v-for="p in visibleTranslationProviders"
                :key="p.code"
                :value="p.code"
                :selected="p.code === dropdownTranslationCode"
                :disabled="!p.enabled || !p.available"
                :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
              >{{ !p.enabled ? `🛇 ${isNarrow ? p.abbrev : p.name}` : (!p.available ? `⚠ ${isNarrow ? p.abbrev : p.name}` : (isNarrow ? p.abbrev : p.name)) }}</option>
            </select>
            <!--
              Lexical provider selector (sits next to the translation
              provider <select>; same styling).  Lists every provider
              returned by the backend for the current lang pair, with
              disabled / unavailable ones shown but unpickable.  An extra
              "None" option lets the user explicitly deactivate lexical
              fetching.  Hidden when the backend returns an empty list OR
              when the translation dropdown itself is hidden — in either
              case the saved code is left intact.
            -->
            <select
              class="bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 transition-colors"
              title="Lexical provider"
              @change="onLexProviderChange"
            >
              <option value="" :selected="dropdownLexCode === ''">{{ isNarrow ? 'No lexical' : 'No lexical provider' }}</option>
              <!-- Saved lexical provider removed from registry (ghost) -->
              <option
                v-if="ghostLexProviderCode"
                :value="ghostLexProviderCode"
                :selected="ghostLexProviderCode === dropdownLexCode"
                disabled
                title="Used for this history entry — no longer available"
              >🛇 {{ ghostLexProviderCode }}</option>
              <option
                v-for="p in visibleLexProviders"
                :key="p.code"
                :value="p.code"
                :selected="p.code === dropdownLexCode"
                :disabled="!p.enabled || !p.available"
                :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
              >{{ !p.enabled ? `🛇 ${isNarrow ? p.abbrev : p.name}` : (!p.available ? `⚠ ${isNarrow ? p.abbrev : p.name}` : (isNarrow ? p.abbrev : p.name)) }}</option>
            </select>
          </div>

          <div v-if="store.isLoading" class="flex-1 flex items-center justify-center text-gray-500 text-sm">
            Translating…
          </div>
          <!-- Passive state messages: supersede any stale history result when relevant -->
          <p v-else-if="noTargetLangs && store.historyIndex < 0" class="flex-1 font-medium text-gray-500 italic">No languages available.</p>
          <p v-else-if="isTargetLangDisabled" class="flex-1 font-medium text-gray-500 italic">Language unavailable.</p>
          <p v-else-if="noTranslationProviders" class="flex-1 font-medium text-gray-500 italic">No providers available.</p>
          <p v-else-if="translationProvidersLoaded && translationDropdownVisible && !effectiveTranslationCode" class="flex-1 font-medium text-gray-500 italic">Provider unavailable.</p>
          <!-- API error (red): only shown when no passive condition applies -->
          <div v-else-if="store.error" class="flex-1 text-sm text-red-400 bg-red-500/10 rounded-lg px-3 py-2">{{ store.error }}</div>
          <p v-else-if="store.result && translationProvidersLoaded" ref="resultContainerRef" class="text-medium leading-relaxed whitespace-pre-wrap flex-1 overflow-y-auto">
            {{ store.result.translated_text }}
          </p>
          <!-- <p v-else class="flex-1 font-medium text-gray-600">Translation will appear here…</p> -->
          <p v-else class="flex-1 font-medium text-gray-600">&nbsp;</p>

          <!--
            Lexical matches inline row.  Driven entirely by the view's
            resolved lexical code; when no usable provider exists (or the
            translation dropdown is hidden), `effectiveLexCode` is null and
            the panel renders nothing — no message, just silence.
          -->
          <LexicalPanel
            v-if="store.result && effectiveLexCode"
            :key="`lex-${store.historyIndex}`"
            :word="store.inputText.trim()"
            :source-lang="resolvedSourceLang"
            :target-lang="store.targetLang"
            :inline="true"
            :initial-data="store.currentEntry?.lexicalMatches"
            :initial-provider-code="effectiveLexCode"
            @fetched="store.saveLexicalMatches($event)"
            @provider-changed="store.saveLexProvider($event)"
          />

          <div v-if="store.result && hasEnabledAvailableTranslationProvider && (!settingsStore.loaded || settingsStore.ttsChoicesForLang(store.targetLang).length > 0)" class="flex items-center h-8">
            <AudioButton :text="store.result.translated_text" :lang="store.targetLang" title="Listen to translation" />
          </div>
        </div>
      </div>

      <!-- Bottom action row: border divider + show/hide toggle (matching WordbookEntry style) -->
      <div v-if="store.result" class="mx-4 pt-2 pb-3 border-t border-surface-700 flex items-center">
        <button
          class="text-xs text-gray-500 hover:text-gray-300 transition-colors ml-auto"
          @click="detailsVisible = !detailsVisible"
        >
          {{ detailsVisible ? 'Hide details' : 'Definition &amp; Context' }}
        </button>
      </div>

      <!-- Definition + Context panels (collapsible).
           The view owns the provider selectors (same pattern as translation/lex);
           panels run in inline mode and trust the validated effective code. -->
      <div v-if="store.result && detailsVisible" class="px-4 pb-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
        <!-- Definition panel -->
        <div class="bg-surface-800 rounded-xl p-3">
          <div class="flex items-center mb-3">
            <h3 class="text-xs font-semibold uppercase tracking-widest text-gray-500">Definition</h3>
            <select
              v-if="defDropdownVisible"
              class="ml-auto bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500/50 transition-colors"
              title="Definition provider"
              @change="onDefProviderChange"
            >
              <option v-if="ghostDefProviderCode" :value="ghostDefProviderCode" :selected="ghostDefProviderCode === dropdownDefCode" disabled title="Used for this entry — no longer available">🛇 {{ ghostDefProviderCode }}</option>
              <option
                v-for="p in visibleDefProviders"
                :key="p.code"
                :value="p.code"
                :selected="p.code === dropdownDefCode"
                :disabled="!p.enabled || !p.available"
                :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
              >{{ !p.enabled ? `🛇 ${p.name}` : (!p.available ? `⚠ ${p.name}` : p.name) }}</option>
            </select>
          </div>
          <!-- No providers for this language (dropdown hidden, list loaded) -->
          <p v-if="defProvidersLoaded && !defDropdownVisible" class="text-sm text-gray-500 italic">No providers available.</p>
          <!-- Provider exists but is disabled / unavailable / ghost -->
          <p v-else-if="defProvidersLoaded && defDropdownVisible && !effectiveDefCode" class="text-sm text-gray-500 italic">Provider unavailable.</p>
          <DefinitionPanel
            v-else
            :key="`def-${store.historyIndex}`"
            :word="store.inputText.trim()"
            :lang="resolvedSourceLang"
            :inline="true"
            :initial-data="store.currentEntry?.definition"
            :initial-provider-code="effectiveDefCode"
            @fetched="store.saveDefinition($event)"
            @provider-changed="store.saveDefProvider($event)"
          />
        </div>
        <!-- Context panel -->
        <div class="bg-surface-800 rounded-xl p-3">
          <div class="flex items-center mb-3">
            <h3 class="text-xs font-semibold uppercase tracking-widest text-gray-500">Context examples</h3>
            <div class="ml-auto flex items-center gap-2">
            <button
              v-if="ctxExamplesRef?.state === 'done' && ctxExamplesRef?.hasTargets"
              class="p-1 transition-colors rounded-lg border border-surface-700"
              :class="ctxExamplesRef?.anyVisible() ? 'text-primary-400 bg-primary-500/10' : 'text-gray-500 hover:text-gray-300'"
              :title="ctxExamplesRef?.anyVisible() ? 'Hide translations' : 'Show translations'"
              @click="ctxExamplesRef?.toggleAllVisible()"
            >
              <svg v-if="ctxExamplesRef?.anyVisible()" viewBox="0 0 16 16" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M1.5 8s2.5-4.5 6.5-4.5S14.5 8 14.5 8s-2.5 4.5-6.5 4.5S1.5 8 1.5 8z"/>
                <circle cx="8" cy="8" r="2"/>
              </svg>
              <svg v-else viewBox="0 0 16 16" class="w-3 h-3" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M2 2l12 12M6.5 6.6a2 2 0 0 0 2.9 2.9M3.3 5.2C2.2 6.3 1.5 8 1.5 8s2.5 4.5 6.5 4.5c1 0 1.9-.3 2.7-.7M13.1 10.4c.9-1 1.4-2.4 1.4-2.4s-2.5-4.5-6.5-4.5c-.5 0-1 .1-1.4.2"/>
              </svg>
            </button>
            <select
              v-if="ctxDropdownVisible"
              class="bg-surface-800 border border-surface-700 text-gray-400 rounded-lg px-2 py-0.5 text-xs focus:outline-none focus:ring-1 focus:ring-primary-500/50 transition-colors"
              title="Context provider"
              @change="onCtxProviderChange"
            >
              <option v-if="ghostCtxProviderCode" :value="ghostCtxProviderCode" :selected="ghostCtxProviderCode === dropdownCtxCode" disabled title="Used for this entry — no longer available">🛇 {{ ghostCtxProviderCode }}</option>
              <option
                v-for="p in visibleCtxProviders"
                :key="p.code"
                :value="p.code"
                :selected="p.code === dropdownCtxCode"
                :disabled="!p.enabled || !p.available"
                :title="!p.enabled ? 'Excluded' : (!p.available ? (p.unavailable_reason ?? 'Not available') : undefined)"
              >{{ !p.enabled ? `🛇 ${p.name}` : (!p.available ? `⚠ ${p.name}` : p.name) }}</option>
            </select>
            </div>
          </div>
          <!-- No providers for this language pair (dropdown hidden, list loaded) -->
          <p v-if="ctxProvidersLoaded && !ctxDropdownVisible" class="text-sm text-gray-500 italic">No providers available.</p>
          <!-- Provider exists but is disabled / unavailable / ghost -->
          <p v-else-if="ctxProvidersLoaded && ctxDropdownVisible && !effectiveCtxCode" class="text-sm text-gray-500 italic">Provider unavailable.</p>
          <ContextExamples
            ref="ctxExamplesRef"
            v-else
            :key="`ctx-${store.historyIndex}`"
            :text="store.inputText.trim()"
            :source-lang="resolvedSourceLang"
            :target-lang="store.targetLang"
            :inline="true"
            :initial-examples="store.currentEntry?.contextExamples"
            :initial-provider-code="effectiveCtxCode"
            :show-all-by-default="store.ctxAllVisible"
            @fetched="store.saveContextExamples($event)"
            @provider-changed="store.saveCtxProvider($event)"
            @toggle-all="store.setCtxAllVisible($event)"
          />
        </div>
      </div>
    </div>
  </div>
  </div>
  </div>

  <ConfirmDialog
    v-model="showClearHistoryDialog"
    title="Clear History"
    message="Are you sure you want to clear all translation history? This action cannot be undone."
    confirm-text="Clear"
    cancel-text="Cancel"
    variant="danger"
    @confirm="onClearHistory"
  />

  <Teleport to="body">
    <button
      v-if="resultButtonVisible"
      :style="{ left: resultButtonLeft + 'px', top: resultButtonTop + 'px' }"
      class="fixed z-50 flex items-center justify-center p-1.5 bg-surface-900 border border-surface-700 rounded-lg text-primary-400 hover:text-primary-300 hover:bg-surface-800 shadow-lg transition-colors"
      @pointerdown.prevent
      @click="onResultSelectionTranslate"
    >
      <svg xmlns="http://www.w3.org/2000/svg" class="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.87 15.07l-2.54-2.51.03-.03A17.52 17.52 0 0 0 14.07 6H17V4h-7V2H8v2H1v2h11.17C11.5 7.92 10.44 9.75 9 11.35 8.07 10.32 7.3 9.19 6.69 8h-2c.73 1.63 1.73 3.17 2.98 4.56l-5.09 5.02L4 19l5-5 3.11 3.11.76-2.04zM18.5 10h-2L12 22h2l1.12-3h4.75L21 22h2l-4.5-12zm-2.62 7l1.62-4.33L19.12 17h-3.24z"/>
      </svg>
    </button>
  </Teleport>

  <!-- Group picker popup for long-press on "add to wordbook" -->
  <Teleport to="body">
    <div
      v-if="groupMenuVisible"
      ref="groupMenuPopupRef"
      :style="{ left: groupMenuLeft + 'px', top: groupMenuTop + 'px' }"
      class="fixed z-50 max-h-72 bg-surface-900 border border-surface-700 rounded-xl shadow-2xl min-w-[160px] flex flex-col"
      @pointerdown.stop
      @click.stop
    >
      <p class="px-3 pt-1 pb-0.5 text-xs text-gray-500 font-semibold uppercase tracking-wide shrink-0">Add to group</p>
      <div class="overflow-auto py-1">
        <button
          v-for="group in wordbookGroupsStore.tabs"
          :key="group.id"
          type="button"
          class="w-full text-left px-3 py-1.5 text-sm transition-colors flex items-center gap-2"
          :class="wordbookUiStore.activeGroupId === group.id
            ? 'text-primary-300 bg-primary-500/10 hover:bg-primary-500/15'
            : 'text-gray-200 hover:bg-surface-700'"
          @click="addToWordbookInGroup(group.id)"
        >
          <svg
            v-if="wordbookUiStore.activeGroupId === group.id"
            xmlns="http://www.w3.org/2000/svg"
            class="w-3.5 h-3.5 text-primary-400 shrink-0"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
          ><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
          <span v-else class="w-3.5 h-3.5 shrink-0" aria-hidden="true" />
          {{ group.name }}
        </button>
        <p v-if="wordbookGroupsStore.tabs.length === 0" class="px-3 py-1.5 text-sm text-gray-500 italic">No groups yet</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTranslatorStore } from '@/stores/translator'
import { useLanguageSettingsStore } from '@/stores/languageSettings'
import { useSettingsStore } from '@/stores/settings'
import { useTextSelectionButton } from '@/composables/useTextSelectionButton'
import { useWordbookStore } from '@/stores/wordbook'
import { useWordbookGroupsStore } from '@/stores/wordbookGroups'
import { useWordbookUiStore } from '@/stores/wordbookUi'
import AudioButton from '@/components/AudioButton.vue'
import DefinitionPanel from '@/components/DefinitionPanel.vue'
import ContextExamples from '@/components/ContextExamples.vue'
import LexicalPanel from '@/components/LexicalPanel.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { translateApi } from '@/api/translate'
import { lexicalApi } from '@/api/lexical'
import { dictionaryApi } from '@/api/dictionary'
import { clearSlow, stopTts } from '@/api/tts'
import { useToastStore } from '@/stores/toast'
import { extractErrorMessage } from '@/utils/error'
import type { ProviderItem } from '@/types'

const store = useTranslatorStore()
const wordbookStore = useWordbookStore()
const wordbookGroupsStore = useWordbookGroupsStore()
const wordbookUiStore = useWordbookUiStore()
const toast = useToastStore()
const langStore = useLanguageSettingsStore()
const settingsStore = useSettingsStore()
const router = useRouter()

onMounted(async () => {
  if (!wordbookStore.isLoaded) wordbookStore.fetchEntries()
  // load() is guarded by isLoaded – safe to call from multiple views
  await langStore.load()
  // When starting fresh (no history), default the target lang to the first
  // enabled language in the user's configured list.
  if (store.historyIndex < 0 && langStore.enabledLangs.length > 0) {
    store.targetLang = langStore.enabledLangs[0].code
  }
})

// Source lang resolved to a concrete code (auto-detect → detected lang, or first enabled lang as fallback).
const resolvedSourceLang = computed(() =>
  store.sourceLang === 'auto'
    ? (store.result?.detected_lang ?? langStore.enabledLangs[0]?.code ?? '')
    : store.sourceLang
)

// ─── Language selectors ─────────────────────────────────────────

// Languages visible in source/target dropdowns: enabled ones + current history
// entry's lang if it is disabled (mirrors provider dropdown behaviour).
const visibleSourceLangs = computed(() =>
  langStore.languages.filter(l => l.enabled || (
    store.sourceLang !== 'auto' &&
    l.code === store.sourceLang &&
    (langStore.enabledLangs.length > 0 || store.historyIndex >= 0)
  ))
)

// When all languages are disabled and there is no history entry to display,
// reset source lang to auto-detect — the only valid option.
watch(
  [() => langStore.enabledLangs.length, () => store.historyIndex],
  ([len, idx]) => {
    if (len === 0 && idx < 0 && store.sourceLang !== 'auto') {
      store.sourceLang = 'auto'
    }
  },
  { immediate: true }
)

const noTargetLangs = computed(() => langStore.enabledLangs.length === 0)
const isTargetLangDisabled = computed(() =>
  langStore.languages.some(l => l.code === store.targetLang) &&
  !langStore.enabledLangs.some(l => l.code === store.targetLang)
)

// True when the auto-detected language is enabled in the user's settings,
// meaning it appears as a legitimate selectable option in the source dropdown.
const detectedLangIsEnabled = computed(() => {
  const detected = store.result?.detected_lang
  if (!detected) return false
  return langStore.enabledLangs.some(l => l.code === detected)
})

// Pin the detected language as the explicit source and retranslate.
function onDetectedLangClick() {
  const detected = store.result?.detected_lang
  if (!detected || !detectedLangIsEnabled.value) return
  store.sourceLang = detected
  retranslate()
}

// Swap is disabled when source is auto-detect and the detected language is
// not in the user's enabled list — swapping would produce a disabled target.
const isSwapDisabled = computed(() => {
  if (store.sourceLang !== 'auto') return false
  const detected = store.result?.detected_lang
  if (!detected) return false
  return !langStore.enabledLangs.some(l => l.code === detected)
})

// When a previously-disabled target lang is re-enabled, auto-translate.
watch(isTargetLangDisabled, (disabled, wasDisabled) => {
  if (wasDisabled && !disabled && store.inputText.trim()) {
    retranslate()
  }
})

const isAlreadyInWordbook = computed(() => {
  if (!store.result) return false
  return !!wordbookStore.findDuplicate(resolvedSourceLang.value, store.targetLang, store.inputText.trim())
})

const ctxExamplesRef = ref<InstanceType<typeof ContextExamples> | null>(null)
const inputTextareaRef = ref<HTMLTextAreaElement | null>(null)
const detailsVisible = ref(false)
const showClearHistoryDialog = ref(false)

// ─── Translation provider list ──────────────────────────────────
//
// The view owns the translation provider list — re-queried on every
// language pair change and after settings save.  No carry-over lives in
// the store; the dropdown's value derives from the current history
// entry (or, transiently, the user's pending pick) and the API call
// uses the same value (with a fallback to the first usable provider).
const translationProviders = ref<ProviderItem[]>([])
const translationProvidersLoaded = ref(false)

async function loadTranslationProviders() {
  if (!store.targetLang) return
  translationProvidersLoaded.value = false
  try {
    const list = await translateApi.getProviders(store.sourceLang, store.targetLang)
    translationProviders.value = [...list].sort((a, b) => a.position - b.position)
    translationProvidersLoaded.value = true
  } catch {
    // Non-critical; keep the existing list if the request fails
  }
}

watch(
  () => [store.sourceLang, store.targetLang],
  loadTranslationProviders,
  { immediate: true },
)
watch(() => settingsStore.saveCount, loadTranslationProviders)

// User's pending translation provider override — set when the user picks
// from the dropdown without input text yet, cleared on history navigation
// so navigating to another entry resets the dropdown to that entry's saved
// code.  Once a translation actually runs the new entry's `providerCode`
// reflects the choice, so the override is no longer needed and is also
// cleared then.
const pendingTranslationCode = ref<string | null>(null)
// Pending provider overrides for def/ctx: take highest priority in the
// dropdown computeds so that a stale @provider-changed emit from an old
// panel instance (completing after a navigation or lang-pair change) cannot
// silently revert a deliberate user selection.
const pendingDefCode = ref<string | null>(null)
const pendingCtxCode = ref<string | null>(null)

function _clearPendingProviderCodes() {
  pendingTranslationCode.value = null
  pendingDefCode.value = null
  pendingCtxCode.value = null
}
watch(() => store.currentEntry, _clearPendingProviderCodes)
// Also clear whenever the user changes the language pair
// (the entry doesn't change in that case, so the entry watch above won't fire).
watch(
  () => [store.sourceLang, store.targetLang] as const,
  _clearPendingProviderCodes,
)

// True only when the displayed history entry's lang pair matches the current
// UI lang pair.  When false (user changed source/target after navigating to a
// history entry without yet translating), the entry's saved provider codes
// are stale for the new pair and must not drive the dropdowns.
const entryMatchesLangPair = computed(() => {
  const entry = store.currentEntry
  if (!entry) return false
  return entry.sourceLang === store.sourceLang && entry.targetLang === store.targetLang
})

// Visible providers: enabled ones (available or not) + the entry's saved
// code when it is disabled (to keep the saved selection visible as a ghost).
const visibleTranslationProviders = computed(() => {
  const list = translationProviders.value
  const entryCode = entryMatchesLangPair.value
    ? store.currentEntry?.providerCode
    : undefined
  return list.filter(p => p.enabled || p.code === entryCode)
})

// Set when the entry's saved code is no longer in the registry at all.
const ghostTranslationProviderCode = computed<string | null>(() => {
  if (!entryMatchesLangPair.value) return null
  const code = store.currentEntry?.providerCode
  if (!code) return null
  if (translationProviders.value.some(p => p.code === code)) return null
  return code
})

// What the dropdown shows as currently selected.  Order of preference:
// 1. Pending user pick (explicit dropdown interaction).
// 2. Current entry's saved code when the entry matches the active lang pair
//    (includes the case where result is null / user is typing a new query).
// 3. Last entry's provider code carried across a lang-pair change, when that
//    provider is still enabled+available in the new pair's list.  This
//    prevents the selection from silently resetting to the first provider
//    every time the user switches source or target language.
// 4. First enabled+available provider as ultimate fallback.
const dropdownTranslationCode = computed<string>(() => {
  if (pendingTranslationCode.value) return pendingTranslationCode.value
  if (entryMatchesLangPair.value) {
    const entryCode = store.currentEntry?.providerCode
    if (entryCode) return entryCode
  }
  // Lang pair changed: carry the last-used provider if it is still usable.
  const lastCode = store.currentEntry?.providerCode
  if (lastCode) {
    const p = translationProviders.value.find(pr => pr.code === lastCode)
    if (p?.enabled && p?.available) return lastCode
  }
  return translationProviders.value.find(p => p.enabled && p.available)?.code ?? translationProviders.value.find(p => p.enabled)?.code ?? ''
})

// What we send to the API.  Same as the displayed value, but if it is not
// usable (disabled, unavailable, or not in the registry) we fall back to
// the first enabled+available provider.  null means no translation is
// possible for this language pair right now.
const effectiveTranslationCode = computed<string | null>(() => {
  const code = dropdownTranslationCode.value
  if (code) {
    const p = translationProviders.value.find(pr => pr.code === code)
    if (p?.enabled && p?.available) return code
  }
  return translationProviders.value.find(p => p.enabled && p.available)?.code ?? null
})

const translationDropdownVisible = computed(() =>
  visibleTranslationProviders.value.length > 0 || !!ghostTranslationProviderCode.value
)
const noTranslationProviders = computed(() =>
  translationProvidersLoaded.value && !translationDropdownVisible.value
)
// True while providers are still loading OR when at least one enabled+available
// provider exists.  Buttons that require a working provider (add-to-wordbook,
// listen-to-translation) are hidden when this is false.
const hasEnabledAvailableTranslationProvider = computed(() =>
  !translationProvidersLoaded.value || effectiveTranslationCode.value !== null
)

// ─── Lexical provider list ──────────────────────────────────────
const lexicalProviders = ref<ProviderItem[]>([])
const lexicalProvidersLoaded = ref(false)

async function loadLexicalProviders() {
  if (!store.targetLang) return
  lexicalProvidersLoaded.value = false
  try {
    const list = await lexicalApi.providers(resolvedSourceLang.value, store.targetLang)
    lexicalProviders.value = [...list].sort((a, b) => a.position - b.position)
    lexicalProvidersLoaded.value = true
  } catch {
    // Non-critical; the dropdown stays empty / hidden.
  }
}

// Reload on explicit lang-selector changes.  We intentionally watch
// store.sourceLang (not resolvedSourceLang) so that clearing the result
// while auto-detect is active — which changes the resolved value from the
// detected lang to the first-enabled-lang fallback — does NOT reload the
// provider list with the wrong source lang mid-typing.
watch(
  () => [store.sourceLang, store.targetLang] as const,
  loadLexicalProviders,
  { immediate: true },
)
// When auto-detect resolves to a (different) lang via a new translation
// result, reload providers for the real source lang.  The guard
// `store.result !== null` prevents this from firing when the result is
// cleared (typing starts), which would switch to the fallback lang.
watch(resolvedSourceLang, (newLang, oldLang) => {
  if (store.result !== null && newLang !== oldLang) loadLexicalProviders()
})
watch(() => settingsStore.saveCount, loadLexicalProviders)

// Visible lexical providers: enabled (incl. unavailable) + saved-but-disabled
// from the current history entry.  Disabled ones render as unpickable items
// with the appropriate marker.
const visibleLexProviders = computed(() => {
  const list = lexicalProviders.value
  const entryCode = entryMatchesLangPair.value ? store.currentEntry?.lexProviderCode : undefined
  return list.filter(p => p.enabled || p.code === entryCode)
})

// Set when the entry's saved lex code is no longer in the registry at all.
const ghostLexProviderCode = computed<string | null>(() => {
  if (!entryMatchesLangPair.value) return null
  const code = store.currentEntry?.lexProviderCode
  if (!code) return null
  if (!lexicalProvidersLoaded.value) return null
  if (lexicalProviders.value.some(p => p.code === code)) return null
  return code
})

// Bound to the <select> value: '' for explicit / implicit None, otherwise
// the saved string code (rendered as-is even if disabled/unavailable).
// Only honour the entry's saved code when the entry's lang pair matches
// the current UI pair; otherwise fall back to first enabled+available.
const dropdownLexCode = computed<string>(() => {
  if (entryMatchesLangPair.value) {
    const code = store.currentEntry?.lexProviderCode
    if (code === null) return ''  // explicit None preserved across reloads
    if (typeof code === 'string') return code
  }
  // undefined or lang pair mismatch: default to first enabled+available
  return lexicalProviders.value.find(p => p.enabled && p.available)?.code ?? ''
})

// Validated lex code to carry into a new history entry.
// Since the lex dropdown is always visible, we always commit a concrete value
// (never undefined): if the entry has no explicit code yet, resolve it to
// whatever the dropdown currently shows so the new entry records the actual
// displayed selection.  Explicit null ("No lexical provider") is preserved.
// Disabled / unavailable codes fall back to first usable (or null).
const resolvedCarryLexCode = computed<string | null>(() => {
  const code = store.currentEntry?.lexProviderCode
  if (code === null) return null  // explicit None: preserve
  if (code === undefined) {
    // Never explicitly set: commit whatever the dropdown currently shows.
    const displayed = dropdownLexCode.value
    return displayed || null
  }
  if (!lexicalProvidersLoaded.value) return code  // not yet known: carry as-is
  const p = lexicalProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code  // valid: carry
  // Disabled, unavailable, or removed from registry: fall back
  return lexicalProviders.value.find(pr => pr.enabled && pr.available)?.code ?? null
})

// Effective code passed to LexicalPanel for fetching.  Null when the
// dropdown is hidden, when "None" is selected, or when no usable provider
// can serve the current pair (fallback exhausted).
const effectiveLexCode = computed<string | null>(() => {
  const code = dropdownLexCode.value
  if (code === '') return null  // explicit None
  const p = lexicalProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code
  return lexicalProviders.value.find(pr => pr.enabled && pr.available)?.code ?? null
})

// ─── Definition provider list ────────────────────────────────────
// Owns the definition provider list — re-queried on every source-lang
// change and after settings save, matching the pattern for translation/lex.
const defProviders = ref<ProviderItem[]>([])
const defProvidersLoaded = ref(false)

// Records which source lang the def provider list was fetched for, so the
// carry-code computed can detect staleness when the lang changes mid-flight.
const defProvidersLang = ref<string | null>(null)

async function loadDefProviders() {
  defProvidersLoaded.value = false
  const lang = resolvedSourceLang.value
  try {
    const list = await dictionaryApi.definitionProviders(lang)
    defProviders.value = [...list].sort((a, b) => a.position - b.position)
    defProvidersLang.value = lang
    defProvidersLoaded.value = true
  } catch {
    // Restore loaded state so effectiveDefCode can resolve and panels don't
    // stay blank indefinitely — empty list shows "No providers available."
    defProvidersLoaded.value = true
  }
}

watch(resolvedSourceLang, loadDefProviders, { immediate: true })
watch(() => settingsStore.saveCount, loadDefProviders)

// Visible providers: enabled ones + the entry's saved code when disabled.
const visibleDefProviders = computed(() => {
  const list = defProviders.value
  const entryCode = entryMatchesLangPair.value ? store.currentEntry?.defProviderCode : undefined
  return list.filter(p => p.enabled || p.code === entryCode)
})

// Set when the entry's saved def code is no longer in the registry at all.
const ghostDefProviderCode = computed<string | null>(() => {
  if (!entryMatchesLangPair.value) return null
  const code = store.currentEntry?.defProviderCode
  if (!code) return null
  if (!defProvidersLoaded.value) return null
  if (defProviders.value.some(p => p.code === code)) return null
  return code
})

// What the dropdown shows: pending user pick → entry's saved code (same lang pair) → first enabled+available.
const dropdownDefCode = computed<string>(() => {
  if (pendingDefCode.value) return pendingDefCode.value
  const entryCode = entryMatchesLangPair.value ? store.currentEntry?.defProviderCode : undefined
  if (entryCode) return entryCode
  return defProviders.value.find(p => p.enabled && p.available)?.code ?? defProviders.value.find(p => p.enabled)?.code ?? ''
})

// Validated code passed to DefinitionPanel (inline mode).  Null when
// providers are still loading, ghost, disabled, or unavailable — the panel
// shows nothing so no stale content from a different provider is displayed.
const effectiveDefCode = computed<string | null>(() => {
  if (!defProvidersLoaded.value) return null
  const code = dropdownDefCode.value
  if (!code) return null
  const p = defProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code
  return null
})

const defDropdownVisible = computed(() =>
  visibleDefProviders.value.length > 0 || !!ghostDefProviderCode.value
)

// Validated def code to carry into the next history entry.
// Returns null when the provider list is stale (lang changed since last load)
// so a provider for the wrong language is never inherited by a new entry.
const resolvedCarryDefCode = computed<string | null | undefined>(() => {
  const code = store.currentEntry?.defProviderCode
  if (code === null || code === undefined) return code
  if (defProvidersLang.value !== resolvedSourceLang.value) return null  // stale list
  if (!defProvidersLoaded.value) return code  // loading for current lang: carry as-is
  const p = defProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code
  return null  // disabled / unavailable / removed from registry
})

function onDefProviderChange(e: Event) {
  const code = (e.target as HTMLSelectElement).value || null
  pendingDefCode.value = code
  store.saveDefProvider(code)
}

// ─── Context provider list ─────────────────────────────────────────
const ctxProviders = ref<ProviderItem[]>([])
const ctxProvidersLoaded = ref(false)

// Records which lang pair the ctx provider list was fetched for.
const ctxProvidersLangs = ref<readonly [string, string] | null>(null)

async function loadCtxProviders() {
  if (!store.targetLang) return
  ctxProvidersLoaded.value = false
  const src = resolvedSourceLang.value
  const tgt = store.targetLang
  try {
    const list = await dictionaryApi.contextProviders(src, tgt)
    ctxProviders.value = [...list].sort((a, b) => a.position - b.position)
    ctxProvidersLangs.value = [src, tgt]
    ctxProvidersLoaded.value = true
  } catch {
    // Restore loaded state so effectiveCtxCode can resolve and the panel
    // doesn't stay blank indefinitely.
    ctxProvidersLoaded.value = true
  }
}

watch([resolvedSourceLang, () => store.targetLang], loadCtxProviders, { immediate: true })
watch(() => settingsStore.saveCount, loadCtxProviders)

const visibleCtxProviders = computed(() => {
  const list = ctxProviders.value
  const entryCode = entryMatchesLangPair.value ? store.currentEntry?.ctxProviderCode : undefined
  return list.filter(p => p.enabled || p.code === entryCode)
})

const ghostCtxProviderCode = computed<string | null>(() => {
  if (!entryMatchesLangPair.value) return null
  const code = store.currentEntry?.ctxProviderCode
  if (!code) return null
  if (!ctxProvidersLoaded.value) return null
  if (ctxProviders.value.some(p => p.code === code)) return null
  return code
})

const dropdownCtxCode = computed<string>(() => {
  if (pendingCtxCode.value) return pendingCtxCode.value
  const entryCode = entryMatchesLangPair.value ? store.currentEntry?.ctxProviderCode : undefined
  if (entryCode) return entryCode
  return ctxProviders.value.find(p => p.enabled && p.available)?.code ?? ctxProviders.value.find(p => p.enabled)?.code ?? ''
})

const effectiveCtxCode = computed<string | null>(() => {
  if (!ctxProvidersLoaded.value) return null
  const code = dropdownCtxCode.value
  if (!code) return null
  const p = ctxProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code
  return null
})

const ctxDropdownVisible = computed(() =>
  visibleCtxProviders.value.length > 0 || !!ghostCtxProviderCode.value
)

// Validated ctx code to carry into the next history entry.
const resolvedCarryCtxCode = computed<string | null | undefined>(() => {
  const code = store.currentEntry?.ctxProviderCode
  if (code === null || code === undefined) return code
  if (!ctxProvidersLangs.value ||
      ctxProvidersLangs.value[0] !== resolvedSourceLang.value ||
      ctxProvidersLangs.value[1] !== store.targetLang) return null  // stale list
  if (!ctxProvidersLoaded.value) return code
  const p = ctxProviders.value.find(pr => pr.code === code)
  if (p?.enabled && p?.available) return code
  return null
})

function onCtxProviderChange(e: Event) {
  const code = (e.target as HTMLSelectElement).value || null
  pendingCtxCode.value = code
  store.saveCtxProvider(code)
}

// ─── Handlers ───────────────────────────────────────────────────

function onProviderChange(e: Event) {
  const code = (e.target as HTMLSelectElement).value
  if (!code) return
  pendingTranslationCode.value = code
  if (store.inputText.trim()) {
    // When source lang is 'auto', the new translation provider may detect a
    // different source language than the current entry.  In that case any
    // lex/def/ctx codes saved for the old language would be invalid for the
    // newly created entry.  Pass `undefined` so the new entry starts with a
    // fresh fallback rather than inheriting stale provider preferences.
    const isAuto = store.sourceLang === 'auto'
    store.translate(
      code, false,
      isAuto ? undefined : resolvedCarryLexCode.value,
      isAuto ? undefined : resolvedCarryDefCode.value,
      isAuto ? undefined : resolvedCarryCtxCode.value,
    )
  }
}

function onLexProviderChange(e: Event) {
  const value = (e.target as HTMLSelectElement).value
  store.saveLexProvider(value || null)
}

const resultContainerRef = ref<HTMLElement | null>(null)
const {
  selectedText: resultSelectedText,
  buttonVisible: resultButtonVisible,
  buttonLeft: resultButtonLeft,
  buttonTop: resultButtonTop,
  dismiss: resultDismiss,
} = useTextSelectionButton(resultContainerRef)

function onResultSelectionTranslate() {
  const text = resultSelectedText.value
  resultDismiss()
  store.translateWord(text, 'auto')
}

// Re-translate when user manually changes a language selector.
async function retranslate() {
  await loadTranslationProviders()
  if (noTargetLangs.value || isTargetLangDisabled.value) {
    store.clearResult()
    return
  }
  const code = effectiveTranslationCode.value
  if (store.inputText.trim() && code) store.translate(code, false, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
}

async function retranslateExplicitTarget() {
  await loadTranslationProviders()
  const code = effectiveTranslationCode.value
  if (store.inputText.trim() && code) store.translate(code, true, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
}

// Debounced auto-translate on input
let debounceTimer: ReturnType<typeof setTimeout> | null = null

/**
 * Resets the pending debounce timer whenever the user does anything in the
 * input box (cursor movement, clicks, selection, etc.) without changing the
 * text.  Has no effect when no debounce is pending.
 */
function onInputActivity() {
  if (debounceTimer === null) return
  clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    const code = effectiveTranslationCode.value
    if (code) store.translate(code, false, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
  }, 1500)
}

/** True while a pointer button is held down inside the input textarea. */
let _inputPointerDown = false

function onInputPointerDown() {
  _inputPointerDown = true
  onInputActivity()
}

function onInputPointerUp() {
  _inputPointerDown = false
  onInputActivity()
}

function onInputPointerCancel() {
  // Browser took over the pointer (e.g. native scroll) — clear the flag
  // but don't reset the debounce since this wasn't a deliberate selection.
  _inputPointerDown = false
}

function onInputPointerMove() {
  // Only reset the debounce while a button is held (i.e. during a drag-
  // selection). Idle hover movements should not interfere with the timer.
  if (_inputPointerDown) onInputActivity()
}

function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  resetAudioContext()
  store.clearResult()  // clear result immediately on any keystroke
  if (!store.inputText.trim()) return
  if (noTargetLangs.value || isTargetLangDisabled.value) return
  debounceTimer = setTimeout(() => {
    const code = effectiveTranslationCode.value
    if (code) store.translate(code, false, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
  }, 1500)
}

/** Stop any active TTS playback and release slow-mode ownership. */
function resetAudioContext() {
  stopTts()
  clearSlow()
}

function onGoBack() {
  resetAudioContext()
  store.goBack()
}

function onGoForward() {
  resetAudioContext()
  store.goForward()
}

function onRemoveCurrentEntry() {
  resetAudioContext()
  store.removeCurrentEntry()
}

function onClearHistory() {
  resetAudioContext()
  store.clearHistory()
}

// Ctrl+Enter: trigger an immediate (non-debounced) translation.
async function onCtrlEnter() {
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  if (noTargetLangs.value || isTargetLangDisabled.value) return
  if (!store.result && store.inputText.trim()) {
    const code = effectiveTranslationCode.value
    if (code) await store.translate(code, false, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
  }
}

// Long press on swap button: clear input + swap langs
let longPressTimer: ReturnType<typeof setTimeout> | null = null
let longPressDidFire = false

function onSwapPointerDown() {
  longPressDidFire = false
  longPressTimer = setTimeout(() => {
    longPressDidFire = true
    resetAudioContext()
    clearInput()
    store.swapLangs()
  }, 600)
}

function onSwapPointerUp() {
  if (longPressTimer) {
    clearTimeout(longPressTimer)
    longPressTimer = null
  }
}

// On touch devices @touchstart.prevent suppresses the synthetic click event,
// so the tap action is handled here instead of in onSwapClick.
async function onSwapTouchEnd() {
  onSwapPointerUp()
  await onSwapClick()
}

async function onSwapClick() {
  if (longPressDidFire) {
    longPressDidFire = false
    return
  }
  resetAudioContext()
  store.reverse(false)
  if (store.inputText.trim() && !noTargetLangs.value && !isTargetLangDisabled.value) {
    // Load providers for the new (swapped) lang pair so dropdownTranslationCode
    // can carry the previously-selected provider across the swap, matching the
    // behaviour of retranslate().  resolvedCarryDefCode/CtxCode will both be
    // null here (stale list) so those entries start fresh.
    await loadTranslationProviders()
    const code = effectiveTranslationCode.value
    if (code) store.translate(code, false, resolvedCarryLexCode.value, resolvedCarryDefCode.value, resolvedCarryCtxCode.value)
  }
}

function clearInput() {
  store.inputText = ''
  store.clearResult()
  detailsVisible.value = false
  if (debounceTimer) {
    clearTimeout(debounceTimer)
    debounceTimer = null
  }
  nextTick(() => inputTextareaRef.value?.focus())
}

/**
 * Jump to the Wordbook view and scroll to + flash the card matching the
 * current translation. Active filters that would hide this card are widened
 * or switched to include it; unrelated active filters are preserved.
 */
function openInWordbook() {
  if (!store.result) return
  const entry = wordbookStore.findDuplicate(resolvedSourceLang.value, store.targetLang, store.inputText.trim())
  if (!entry) return
  const pair = `${entry.source_lang}→${entry.target_lang}`
  wordbookUiStore.requestShowEntry(entry.id, pair, entry.group?.id ?? null, entry.color ?? null)
  router.push({ name: 'wordbook' })
}

async function addToWordbook() {
  if (!store.result) return
  if (isAlreadyInWordbook.value) {
    toast.error('This word is already in your wordbook')
    return
  }
  try {
    const entry = await wordbookStore.addEntry({
      source_lang: resolvedSourceLang.value,
      target_lang: store.targetLang,
      source_text: store.inputText.trim(),
      target_text: store.result.translated_text,
      provider_code: store.currentEntry?.providerCode ?? null,
    })
    // Migrate def/ctx/lex provider codes from the current translator history
    // entry into the wordbook UI store (localStorage) so the entry opens with
    // the same providers the user was already using in the translation session.
    const cur = store.currentEntry
    if (cur?.defProviderCode != null)
      wordbookUiStore.setProvider(entry.id, 'def', cur.defProviderCode)
    if (cur?.ctxProviderCode != null)
      wordbookUiStore.setProvider(entry.id, 'ctx', cur.ctxProviderCode)
    if (cur?.lexProviderCode != null)
      wordbookUiStore.setProvider(entry.id, 'lex', cur.lexProviderCode)
    if (wordbookUiStore.activeGroupId !== null) {
      wordbookGroupsStore.assignEntry(entry.id, wordbookUiStore.activeGroupId)
    }
    toast.success('Added to Wordbook')
  } catch (e: unknown) {
    toast.error(extractErrorMessage(e, 'Failed to save to wordbook'))
  }
}

// ─── Add-to-wordbook long-press: group picker ────────────────────
const addToWordbookBtnRef = ref<HTMLButtonElement | null>(null)
const groupMenuPopupRef = ref<HTMLElement | null>(null)
const groupMenuVisible = ref(false)
const groupMenuLeft = ref(0)
const groupMenuTop = ref(0)
let _addWbLongPressTimer: ReturnType<typeof setTimeout> | null = null
let _addWbLongPressDidFire = false

function onAddWordbookPointerDown(e: PointerEvent) {
  if (e.button !== 0) return
  _addWbLongPressDidFire = false
  if (_addWbLongPressTimer) clearTimeout(_addWbLongPressTimer)
  _addWbLongPressTimer = setTimeout(async () => {
    _addWbLongPressDidFire = true
    _addWbLongPressTimer = null
    if (wordbookGroupsStore.tabs.length === 0) {
      try { await wordbookGroupsStore.fetchGroups() } catch { /* non-critical */ }
    }
    _openGroupMenu()
  }, 600)
}

function onAddWordbookPointerUp() {
  if (_addWbLongPressTimer) {
    clearTimeout(_addWbLongPressTimer)
    _addWbLongPressTimer = null
  }
}

async function onAddWordbookClick() {
  if (_addWbLongPressDidFire) {
    _addWbLongPressDidFire = false
    return
  }
  await addToWordbook()
}

function _openGroupMenu() {
  const btn = addToWordbookBtnRef.value
  if (!btn) return
  const rect = btn.getBoundingClientRect()
  // First-pass: right-align below the button
  groupMenuLeft.value = Math.max(8, rect.right - 160)
  groupMenuTop.value = rect.bottom + 4
  groupMenuVisible.value = true
  document.addEventListener('pointerdown', _onGroupMenuOutsidePointerDown, true)
  nextTick(() => _repositionGroupMenu(rect))
}

function _repositionGroupMenu(buttonRect: DOMRect) {
  const popup = groupMenuPopupRef.value
  if (!popup) return
  const popupRect = popup.getBoundingClientRect()
  const margin = 4
  // Vertical: prefer below; flip above when there is more space
  const spaceBelow = window.innerHeight - buttonRect.bottom
  const spaceAbove = buttonRect.top
  if (spaceBelow < popupRect.height + margin && spaceAbove > spaceBelow) {
    groupMenuTop.value = Math.max(margin, buttonRect.top - popupRect.height - margin)
  } else {
    groupMenuTop.value = buttonRect.bottom + margin
  }
  // Horizontal: right-align to the button; flip left-align when near the left edge
  if (buttonRect.right - popupRect.width < margin) {
    groupMenuLeft.value = Math.max(margin, buttonRect.left)
  } else {
    groupMenuLeft.value = buttonRect.right - popupRect.width
  }
}

function _onGroupMenuOutsidePointerDown(e: PointerEvent) {
  if (groupMenuPopupRef.value?.contains(e.target as Node)) return
  groupMenuVisible.value = false
  document.removeEventListener('pointerdown', _onGroupMenuOutsidePointerDown, true)
  e.stopPropagation()
}

async function addToWordbookInGroup(groupId: number) {
  groupMenuVisible.value = false
  document.removeEventListener('pointerdown', _onGroupMenuOutsidePointerDown, true)
  wordbookUiStore.activeGroupId = groupId
  await addToWordbook()
}

// ─── Narrow-screen detection ─────────────────────────────────────
// Drives short provider abbreviations and dynamic panel height on very
// small viewports (portrait phones).
const isNarrow = ref(false)
let _narrowMq: MediaQueryList | null = null

// Panel grid height for narrow screens — measured dynamically so the
// input+result block fills exactly the viewport without a scrollbar when
// the details section is collapsed.  A ~44 px reserve is always kept for
// the action row ("Definition & Context" toggle) beneath the grid.
// The height is set once and does NOT change when details open or close,
// so closing details restores the correct view without any content resize.
const panelGridRef = ref<HTMLElement | null>(null)
const narrowPanelHeight = ref<number | null>(null)

const panelGridStyle = computed(() =>
  narrowPanelHeight.value !== null ? { height: `${narrowPanelHeight.value}px` } : undefined
)

function updateNarrowPanelHeight() {
  if (!isNarrow.value) { narrowPanelHeight.value = null; return }
  const el = panelGridRef.value
  if (!el) { narrowPanelHeight.value = null; return }
  const top = el.getBoundingClientRect().top
  narrowPanelHeight.value = Math.max(200, window.innerHeight - top - 44)
}

function _onNarrowMqChange(e: MediaQueryListEvent) {
  isNarrow.value = e.matches
  nextTick(updateNarrowPanelHeight)
}

function _onWindowResize() { updateNarrowPanelHeight() }

onMounted(() => {
  _narrowMq = window.matchMedia('(max-width: 479px)')
  isNarrow.value = _narrowMq.matches
  _narrowMq.addEventListener('change', _onNarrowMqChange)
  window.addEventListener('resize', _onWindowResize)
  nextTick(updateNarrowPanelHeight)
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', _onGroupMenuOutsidePointerDown, true)
  if (_addWbLongPressTimer) clearTimeout(_addWbLongPressTimer)
  _narrowMq?.removeEventListener('change', _onNarrowMqChange)
  window.removeEventListener('resize', _onWindowResize)
})
</script>
