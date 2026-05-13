- Add about dialog with version info
- Leverage Kokoro TTS option of lozzy encoding initially (on pronunciation request)?
- Leverage Websockets to update UI on data change on other devices
- Implement Android app
- Login page by default should disallow new user registering, now it allows even if api call was failed
- Check service endpoints (health, apidoc, etc)-  whether they exposed to Internet, and disable if it's the case
- Fix piper-voices.toml for prod environment
- Add wrappers in scripts dir for scripts that sit in backend docker container (user mgmt, tts-encode, etc); fix README and systemd units
- Describe setup for background TTS encoder worker in README
- On invalid login it shows error message for a very short time and then UI state of login form quickly resets back with no message - it produces unpleasant and pointless flicker
- On audio button press, add visual spinner while generating a speech on the server (may take some noticeable time), before it gets actually played back 
- LibreTranslate didn't loaded, investigate reasons and give instructions how to fix
- Add icons for app
- on Android device browser, when some translation history entry is displayed in the translator, then there is no possibility to ever type something in input panel. If cursor is placed in, then Android keyboard slides in as well, but then it immediately slides out. User is forced to clear history to be able to type or paste something in.

Tests:
- Cover all code with unit tests
- Make test set for disabled, unavailable, filtered out providers and influences in frontend if provider state changes back and forth

Not-so-critical:
- Avoid up-down pulling when switching def/ctx/lex tabs in wordbook near the bottom edge of the screen. Possible solution: artificial bottom spacer.
- On def/ctx fetch error, do not display "No definition/examples found" in panel. Show "Fetch error" instead

Questionable:
- Add a list view for translation history
- Independent scrolling of main field and side panel in wordbook (though, it's better to not hold large groups of words)
- Search in wordbook by typing a text (though, the counterpoint is the same as above)
- Multi-select wordbook entries for batch delete or for assigning a group or a color

Distant future:
- Metrics for inner and external api calls
- Per-user stats for external api usage
- UI localization
- Light theme, theming in general
- Batch import words into wordbook
- Ability to force re-fetches around the cache (if it really needed)
- Implement redis backend for cache, leveraging TTS mechanizm for failed responses. Notice, that there is long text may be participated in the key, so maybe key hashes should be used, with array values instead of scalars, to work around cache collisions
- Switch from mp3 to ogg Opus for tts cache storage in ~1–2 years (starting from 2026) when iOS 16+ reaches >99% adoption (to reduce compatibility issues)
