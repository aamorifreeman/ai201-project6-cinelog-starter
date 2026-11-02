# PR Response Doc — CineLog Watchlist Feature

## AI Usage
I used Codex to review the assignment requirements and reviewer comments, explore the existing collection service and tests, and assist with implementing the watchlist changes. It helped rename the service function, prevent duplicate entries, add tests, resolve the UUID rebase conflict, and clean up commit messages.

I also used Codex to help draft and refine my review responses based on my design decisions. For verification, I ran the full test suite, which passed all 12 tests, and checked for remaining references to the old function name and unresolved conflict markers.

## Comment 1 — Rename
**What I did:** Renamed `save_to_watchlist()` to `add_to_watchlist()` to match `add_to_collection()` and the project's verb-to-noun naming convention. The definition is in `services/watchlist_service.py`; its import and invocation are in `routes/watchlist/watchlist.py`.

**How I verified:** Searched the Python files for the old and new names, inspected the route call site, and ran the full test suite after the rename. The old name has no remaining Python references. The endpoint integration test exercises the renamed function through the HTTP route.

## Comment 2 — Deduplication
**What I did:** Followed the existing `add_to_collection()` pattern: first look up the film and raise `FilmNotFoundError` if absent, then query for an entry matching both `user_id` and `film_id`. If an entry exists, raise `AlreadyInWatchlistError` before creating or committing another row. The add endpoint translates that error into HTTP 409, matching the collection endpoint's duplicate behavior. A different user can still save the same film.

**How I verified:** The duplicate service test adds the same film twice, expects the named exception on the second attempt, and confirms the database contains exactly one matching row. The endpoint test confirms the first request returns 201 and the repeat returns 409. Collection tests still pass.

## Comment 3 — Missing test
**What I did:** Added `test_add_to_watchlist_nonexistent_film_raises` in `tests/test_watchlist.py`, modeled on `test_add_to_collection_nonexistent_film_raises`. It uses the same isolated in-memory app fixture and sample user fixture, opens an app context, and passes the nonexistent UUID `00000000-0000-0000-0000-000000000000` inside `pytest.raises(FilmNotFoundError)`.

**How I verified:** The test passes and also confirms that no watchlist entry was created. The endpoint integration test independently verifies a nonexistent film returns HTTP 404.

## Comment 4 — Default visibility

**Position:** I chose to make new watchlist entries private by default (`public=False`), with the option to explicitly make them public.

**Reasoning:** I made this decision because CineLog distinguishes between films users have already watched and films they may want to watch later. I don't think saving a film should automatically mean a user wants to share that interest publicly. Defaulting to private gives users control over what they share.

**Tradeoff:** I considered that public watchlists could help friends discover films and plan shared viewing. However, I decided that giving users control over visibility was more important than automatic discovery. Users can still opt into sharing by setting `public=true`.

**Implementation:** I set the model and service defaults to `False` and added a boolean `public` parameter to the API. The API rejects non-boolean values. Since the starter doesn't include authentication or access controls, this flag only stores visibility preferences and does not enforce privacy. The GET endpoint remains unfiltered.

## Comment 5 — Sort order

**Position:** I chose to display the most recently added films first.

**Reasoning:** I agreed with the reviewer's point that users generally want to see their recent additions. Since the watchlist is meant for saving films to watch later, I decided that users should be able to quickly find what they recently saved without searching through the entire list. This also keeps the behavior consistent with `get_collection()`, which already uses newest-first ordering.

**Tradeoff:** I also considered alphabetical sorting, which would make finding a specific film easier, especially as the watchlist grows. However, I decided that quickly accessing recently saved films was more important for the default behavior. I recognize that this is a product assumption rather than something verified through user research. Search functionality or optional sorting could address this limitation later.

**Verification:** I tested my decision by adding Alien with an older timestamp and Zodiac with a newer timestamp. I confirmed that Zodiac appeared first, even though Alien comes first alphabetically. I also used entry ID as a secondary sort to ensure consistent ordering when timestamps match.

## Comment 6 — Rebase
**What conflicted:** Rebasing `feature/watchlist` onto `origin/main` stopped in `models.py` while replaying the starter watchlist commit. Main's film foreign key used `db.String(36)` after the UUID refactor; the feature branch used `db.Integer` with an index.

**How I resolved it:** Kept main's UUID-compatible `String(36)` type and retained the feature's index. Continued the rebase without merging main. Then committed the remaining service and request-body documentation updates in a dedicated UUID fix commit. The actual model conflict resolution is part of the replayed feature commit; the later fix records the remaining UUID updates.

**How I verified no conflict remains:** The complete test suite passes using freshly generated UUID film IDs. A test verifies the watchlist film foreign key is `VARCHAR(36)`. Checked that main is an ancestor, there are no merge commits on the feature branch, and there are no unresolved files or conflict markers in Python sources.

## Additional tests and visibility toggle
Added duplicate and HTTP regression tests beyond the required missing-film test. Duplicate prevention matters because the original feature silently created multiple entries. Tests also verify explicit public opt-in, invalid visibility input, the private default, recent-first ordering, and UUID schema compatibility. The visibility parameter is optional: omit it for false, or send `{"film_id": "<uuid>", "public": true}` to opt in.

## PR Description
CineLog's watchlist lets a user save films for later and retrieve them with saved-date and visibility metadata. This update follows the project's service naming, rejects duplicate saves with HTTP 409, returns HTTP 404 for missing films, and adapts watchlist references to main's UUID film IDs.

New entries default to private metadata so saving a film does not automatically express an intent to share; callers can explicitly set `public=true`. Lists show the most recently added films first to make recent recommendations easy to retrieve. The starter does not enforce visibility through authentication.

### Manual testing
1. Create and activate a virtual environment, then run `python -m pip install -r requirements.txt`.
2. For a fresh local sample database, run `python seed.py`, then `python app.py`. The root URL returns 404 because the starter has no frontend.
3. Run `curl http://127.0.0.1:5000/films` and copy a film UUID. Use a user UUID printed by the seed script.
4. Send `curl -i -X POST http://127.0.0.1:5000/watchlist/USER_UUID/add -H 'Content-Type: application/json' -d '{"film_id":"FILM_UUID"}'`. Replace both UUID placeholders. Expect 201 and `public: false`.
5. Repeat the same request. Expect 409, then GET `/watchlist/USER_UUID` and confirm there is only one entry for that film.
6. Add a different valid film with `"public": true`. Expect 201 and true in the response. GET the watchlist and verify the more recent addition appears first.
7. Send the all-zero nonexistent film UUID. Expect 404. Send an empty JSON object or a string-valued `public` field and expect 400.
8. Run `python -m pytest tests/ -v`: all nine tests should pass.

## Local verification
- Nine tests passed after the code changes and UUID rebase.
- Interactive rebase reworded the starter's nonconventional feature commit.
- Final commit-log screenshot remains to be added before publishing.
- AI Usage is intentionally blank for the student to complete.
- No GitHub fork, push, pull request, or course submission has been made.
