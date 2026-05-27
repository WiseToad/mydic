Deployment and maintenance:
- Check service endpoints (health, apidoc, etc) - whether they exposed to Internet, and disable if it's the case

Bugs:
- On invalid login it shows error message for a very short time and then UI state of login form quickly resets back with no message. It produces unpleasant and pointless flicker for the user

Bugs encountered when running in Android device browser:
- Bottom system bar in Android still appears in white for app in dark mode, despite recent attempts to fix it

Not-so-critical bugs:
- Avoid up-down pulling when switching def/ctx/lex tabs in wordbook near the bottom edge of the screen. Possible solution: artificial bottom spacer. Implement it by storing in-memory extra height value for wordbook cards, to prevent screen twitching when user changes details for cards near bottom of the screen
- After individual restarting kokoro tts container, its voices become unavailable

Features:
+ Long-pressing non-focused wordbook item on Android moved it in it's place
- Add about dialog with version info
- Updating installed web app - how?
- DB: Move group filtering in wordbook from frontend to backend, add "no group" tab, change filtering principle, so some group strictly should be active. Rename "group" to "tab"?
- Fix wordbook layout for narrow Android screens. Maybe it would be better to completely disable different density selector, since it has no effect anyway
- Typing a word in translator suggest words found in wordbook
- Add ability to select default voice in settings (e.g., mark a voice as default with checkmark)
- Clicking in translator on some lexical provider result should pick that result into translation result as a new token; the translation result should become clickable after that to be able to remove tokens collected in such a way; tokens are separated by comma; add a retranslate button to revert to initial state - all of this needed to give the user an opportunity to prepare translated result before adding it into the wordbook

Architectural:
- Proactive speech generation for wordbook items by separate worker job
- Search for correlations between word cards woth llm using cached definitions
- A voice repetitor, spelling the words from wordbook one-by-one and checking STT response from the user 
- Leverage Websockets to update UI on data change on other devices
- Implement Android app

Tests:
- Cover all code with unit tests
- Make test set for disabled, unavailable, filtered out providers and influences in frontend if provider state changes back and forth

Questionable:
- Multi-select wordbook entries for batch delete or for assigning a group or a color
- Leverage Kokoro TTS option of lozzy encoding immediately on pronunciation request?
- Alternative voice on audio (by pressing Alt?), slow pronunciation (by pressing Ctrl? or by RMB)

Distant future:
- Metrics for inner and external api calls
- Per-user stats for external api usage
- Store user requested provider along with cached results in db
- UI localization
- Definition providers with non-english output (non-english Wikitionary alternatives)
- Light theme, theming in general
- Batch import words into wordbook
- Ability to manually force re-fetches around the cache (if it really needed)
- Implement redis backend for cache, leveraging TTS mechanizm for failed responses. Notice, that there is long text may be participated in the key, so maybe key hashes should be used, with array values instead of scalars, to work around cache collisions
- Switch from mp3 to ogg Opus for tts cache storage in ~1–2 years (starting from 2026) when iOS 16+ reaches >99% adoption (to reduce compatibility issues)
