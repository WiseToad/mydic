Deployment and maintenance:
- Check service endpoints (health, apidoc, etc) - whether they exposed to Internet, and disable if it's the case

Bugs:
- Bottom system bar in Android still appears in white for app in dark mode, despite recent attempts to fix it
- After individual restarting kokoro tts container, its voices become unavailable

Features:
- Reorganize wordbook toolbars, collapse long group lists, reconsider layouts for different widths and densities. Fix wordbook layout for narrow Android screens. Maybe it would be better to completely disable different density selector, since it has no effect anyway
- Implement searching in wordbook
- Linked words feature
- Hidden group attribute

- Add ability to select default voice in settings (e.g., mark a voice as default with checkmark)
- Clicking in translator on some lexical provider result should pick that result into translation result as a new token; the translation result should become clickable after that to be able to remove tokens collected in such a way; tokens are separated by comma; add a retranslate button to revert to initial state - all of this needed to give the user an opportunity to prepare translated result before adding it into the wordbook

Architectural:
- Proactive speech generation for wordbook items by separate worker job
- Search for correlations between word cards with llm using cached definitions
- A voice repetitor, spelling the words from wordbook one-by-one and checking STT response from the user 
- Leverage Websockets to update UI on data change on other devices
- Implement Android app (the web-app already available)?

Tests:
- Cover all code with unit tests
- Make test set for disabled, unavailable, filtered out providers and influences in frontend if provider state changes back and forth

Prepare to promotion:
- UI localization
- Light theme, theming in general
- Definition providers with non-English output (non-English Wikitionary alternatives)
- Share group feature
- Store user requested provider along with cached results in db
- Metrics for inner and external api calls
- Per-user stats for external api usage

Distant future:
- Ability to manually force re-fetches around the cache (if it really needed for updating some invalid or stale outputs from provirers)
- Implement redis backend for cache, leveraging TTS mechanizm for failed responses. The challenge is that there is long text may be participated in the key, so maybe key hashes should be used, with array values instead of scalars, to work around cache collisions
- Switch from mp3 to ogg Opus for tts cache storage in ~1–2 years (starting from 2026) when iOS 16+ reaches >99% adoption (to reduce compatibility issues)

Questionable:
- Multi-select wordbook entries for batch delete or for assigning a group or a color (not so demanded to be worth to complicate the code)
- Leverage Kokoro TTS option of lozzy encoding immediately on pronunciation request (can increase response time)
- Alternative voice on audio (by pressing Alt?), slow pronunciation (by pressing Ctrl? or by RMB) (poorly applicable on Android)
- Batch import words into wordbook (not so demanded to be worth to complicate the code and workflow)
