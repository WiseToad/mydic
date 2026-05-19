Deployment and maintenance:
- Check service endpoints (health, apidoc, etc) - whether they exposed to Internet, and disable if it's the case

Bugs:
- On invalid login it shows error message for a very short time and then UI state of login form quickly resets back with no message - it produces unpleasant and pointless flicker

Bugs encountered when running in Android device browser:
- In wordbook, it's impossible to change voice by long press on audio button. Instead, the card itself is enetering dragging mode.
- It's impossible to translate selection - the translate button do not appears. Instead, there is standard android toolbar appeared.

Not-so-critical bugs:
- Avoid up-down pulling when switching def/ctx/lex tabs in wordbook near the bottom edge of the screen. Possible solution: artificial bottom spacer.
- On narrow screens (Android) shrink translation and lexical provider names
- After individual restarting kokoro tts container, its voices become unavailable

Features:
* Add spinner when doing re-translate in edit mode in wordbook, if request takes longer than 150 ms
* Clicking on detected lang in translator sets this lang as current, if it in list of enabled langs (by system and by user)
- "Ephemeral details" in wordbook - clicking outside details panel closes this sub-panel; dragging detail panel selects text inside it and do not lead to dragging word card

- Independent scrolling of main field and side panel in wordbook; top bar also stays at the top and not scrolls past the top of the screen
- Add swapped display mode for wordbook
- ~~Dragging "add to wordbook" onto lexical example saves a new wordbook entry with this example as a translation (translation provider is empty for a new entry in such a case)~~
- Clicking in translator on some lexical provider result should pick that result into translation result as a new token; the translation result should become clickable after that to be able to remove tokens collected in such a way; tokens are separated by comma; add a retranslate button to revert to initial state - all of this needed to give the user an opportunity to prepare translated result before adding it into the wordbook
- Add ability to select default voice in settings (e.g., mark a voice as default with checkmark)
- Alternative voice on audio (by pressing Alt?), slow pronunciation (by pressing Ctrl? or by RMB)
- Proactive speech generation for wordbook items by separate worker job
- A concept of currently selected card(s) in wordbook - to help find it/them when changing density, or to delete group; items lost when changing filter are excluded from list 
- On narrow screens (Android) maybe it's better to completely disable different density selector, since it has no effect anyway

Presentation:
- Add about dialog with version info
- Add icons for the app

Architectural:
- Search for correlations between word cards woth llm using cached definitions
- Leverage Websockets to update UI on data change on other devices
- Implement Android app

Tests:
- Cover all code with unit tests
- Make test set for disabled, unavailable, filtered out providers and influences in frontend if provider state changes back and forth

Questionable:
- Add a list view for translation history
- Search in wordbook by typing a text (though, the counterpoint is the same as above)
- Multi-select wordbook entries for batch delete or for assigning a group or a color
- Leverage Kokoro TTS option of lozzy encoding initially (on pronunciation request)?

Distant future:
- Metrics for inner and external api calls
- Per-user stats for external api usage
- UI localization
- Light theme, theming in general
- Batch import words into wordbook
- Ability to force re-fetches around the cache (if it really needed)
- Implement redis backend for cache, leveraging TTS mechanizm for failed responses. Notice, that there is long text may be participated in the key, so maybe key hashes should be used, with array values instead of scalars, to work around cache collisions
- Switch from mp3 to ogg Opus for tts cache storage in ~1–2 years (starting from 2026) when iOS 16+ reaches >99% adoption (to reduce compatibility issues)
