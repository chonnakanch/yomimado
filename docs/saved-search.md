# Saved search and dictionary layout

Status: **approved by the owner and complete in development source — 2026-10-20**.
The owner reviewed and approved the working dictionary-style Saved preview.
Installer publication and exact-installer acceptance remain separate.

## Search

Words match their saved surface, dictionary form, reading, meanings and source
sentence. Sentences match Japanese text and any already-saved translation.
Every whitespace-separated term must occur in at least one of those fields.
Matching ignores letter case, full/half width and hiragana/katakana differences.
There is no romaji conversion or inferred translation.

Search filters the complete existing local collection without changing stored
text, dictionary identities, dates or ordering. It makes no lookup/translation
request and does not create or update saved records. The list API already
returns all records; there is no API or database migration.

Each collection remembers its last query in local storage, up to 200 characters.
Queries remain independent when switching tabs and persist across reopening.
Storage failures leave search usable for the current session. Clear search or
Escape clears a query; Escape does not consume an active IME composition.

Result counts update as the query changes. A no-matches message is distinct from
an empty library and offers Clear search. Refresh keeps the query; a failed
refresh retains the existing rows and error feedback. Remove still requires
confirmation and acts on the selected saved ID, even in a filtered list.

## Approved design

Only Saved changes. It uses the existing dark palette and installed font stacks:
a prominent search field, underlined Words/Sentences tabs, larger Japanese
headwords, readings, JLPT badges and numbered senses. Wider windows place
headwords beside definitions; narrow windows stack them without shrinking text.
Source sentences, saved dates and JMdict attribution remain in an accessible
disclosure. Existing tab navigation, removal focus recovery and errors remain.
No new font, library, model or dataset is added.

The reviewed browser preview uses synthetic sample entries and blocks changes to them.
It does not connect to the real saved database. Its temporary server/harness is
outside the repository. It is a working rendering of the app components rather
than a separate static mockup.

## Verification

All 288 frontend tests, TypeScript, Prettier and the frontend production build
pass. Twenty-three new search cases cover field matching, Unicode normalization,
query persistence, no results, clearing/focus, failed refresh, filtered removal,
storage failures and IME Escape. Existing library lifecycle tests still pass.
Browser checks cover actual search/clear, sentence translation search and source
disclosure, plus a 320 px viewport without horizontal overflow. Native Windows
interaction and exact-installer acceptance remain unverified.
