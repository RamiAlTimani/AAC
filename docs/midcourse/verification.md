# Task Tracker - Behavior Contract (pre-refactor)

Records what the board does **today**, before any refactor. Board logic is in
`task-tracker/frontend/app.js` (loaded by `frontend/index.html:159`). Backend rules are in
`backend/app/models.py`, `backend/app/business_rules.py`, and the checks called from
`backend/app/routers/tasks.py`. The backend runs on `http://localhost:8000`.

Setup for every check: start the backend
(`cd task-tracker/backend && venv/bin/uvicorn app.main:app --port 8000`), open
`frontend/index.html`, keep DevTools → Network open.

Some rows describe behavior that looks wrong (B7, B9, B13). That is deliberate. A refactor
is correct if it keeps these observations; changing one is a behavior change and needs its
own decision.

| ID            | Behavior                                              | How to check                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  | Notes                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **B1**  | Three columns render with correct counts              | Clear both filters ("Overdue only" off, Tag = "All tags") and load the page. Confirm three columns left to right:**To Do**, **In Progress**, **Done**. Count the cards in each and compare to the header pill (`[data-count]`). Cross-check against `GET /tasks` grouped by `status`.                                                                                                                                                                                                                                                                 | Counts always come from the**filtered** set (`render()` → `renderBoard(applyFilters())`). With filters off they match the full totals; with a filter on they count only visible cards. That is correct. Any status other than the three is dropped silently.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **B2**  | Cards sort by priority in each column                 | In a column with 2+ cards, read top to bottom:**High → Medium → Low**.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                | Rank is High=0, Medium=1, Low=2. The`a.id - b.id` tie-break does nothing: ids are UUID strings, so the subtraction is `NaN` and same-priority cards keep the order `GET /tasks` returned. Lock the priority order only; do not assert an order within a priority.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| **B3**  | Loading state shows before tasks load                 | Throttle Network to Slow 3G and reload. Before cards appear: a spinner panel reading "Loading tasks…", columns hidden.                                                                                                                                                                                                                                                                                                                                                                                                                                                       | Panel has`role="status"`. `loadTasks()` sets `loading`, then `ready`. Too fast to see without throttling.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| **B4**  | Empty columns stay visible                            | Make a status empty (e.g. no Done tasks). The column still shows a header, count**0**, and a dashed **"No tasks"** placeholder. It must not collapse.                                                                                                                                                                                                                                                                                                                                                                                                             | `.card-list-empty` sits inside `.card-list`, so the column keeps its drop area. All three can be empty independently. A filter can empty a column too - same placeholder.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **B5**  | Error state shows when the backend is down            | Stop the backend and reload. Expect an error panel reading "Couldn't load tasks. Check your connection and try again." with a**Retry** button. Retry while still down → error stays. Restart the backend, Retry → board loads.                                                                                                                                                                                                                                                                                                                                        | Panel has`role="alert"`. Fires on a fetch throw **or** any non-`ok` response from `GET /tasks`. Columns stay hidden while it shows.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **B6**  | Valid drag sends PATCH and updates the board          | Drag a**ToDo** card to **In Progress**. The card moves before the response arrives. `PATCH /tasks/{id}` fires with `{"status":"InProgress"}` → 200. Reload - the card is still there. Both counts update.                                                                                                                                                                                                                                                                                                                                                    | The move is optimistic:`task.status` set, `render()`, then fetch. Only three transitions are allowed: `ToDo→InProgress`, `InProgress→Done`, `Done→InProgress`. Dropping a card on its own column does nothing - assert **no request** fires.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| **B7**  | Rejected drag reverts and shows the server message    | **Rejected transition:** drag **ToDo** onto **Done**. `PATCH` → **422**, the card snaps back, counts revert, and a red toast reads `Invalid status transition from ToDo to Done. Allowed transitions: ['Done->InProgress', 'InProgress->Done', 'ToDo->InProgress']`. **Offline:** stop the backend, then drag → the card reverts and the toast reads "Couldn't reach the server - your change wasn't saved."                                                                                                                              | Two paths: a non-`ok` response shows the server's `detail` verbatim via `extractServerError()`; a thrown fetch shows the fixed offline message. The toast clears after 5s. `ToDo→Done`, `Done→ToDo`, and `InProgress→ToDo` are all rejected.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
| **B8**  | Due date renders; overdue styling is derived          | Create four tasks and read`.due-date` on each: (a) due **yesterday**, ToDo → `Overdue · <date>` with overdue styling on the element and the card; (b) same past date but **Done** → `Due <date>`, not overdue; (c) due **today** → `Due <date>`, not overdue; (d) **no due date** → the `.due-date` element is **gone from the DOM**, not blank or hidden.                                                                                                                                                                       | Overdue is computed at render time by`isOverdue()`, never stored. Done is never overdue; no date is never overdue; today is not overdue. Compares strings against a **local** `todayISO()` - not `toISOString()`, which would shift the date across UTC. **Setup problem:** no API call can create an overdue task (see the testability gap in §3).                                                                                                                                                                                                                                                                                                                                                                                                                                                   |
| **B9**  | Due date validation on create and edit                | **Create, past date:** New Task → title + a past date → Save → **422**, modal stays open, error lands on the due-date field slot (`data-error-for="due_date"`), not the banner. **Create, empty date:** the payload sends `"due_date": null` → 201. **Edit, unchanged past date:** resend it unchanged *plus* a valid status change (ToDo → InProgress) → 200. **Edit, date moved into the past:** same status change plus a past date → 422 on the due-date slot.                                                                 | Two rules: create uses a`field_validator` on `TaskCreate`; edit uses `validate_due_date_change()`, which allows `None` and allows resending the same date, so a task stays editable after its date passes. Both raise with `loc: ["body","due_date"]`, which routes the error to the field slot via `fieldFromLoc()`. **Caveat:** the edit rows need a status change because the modal always resends `status` and the transition check runs first (B13).                                                                                                                                                                                                                                                                                                                                            |
| **B10** | Tags render as chips; normalization holds             | Create a task with tags`["Bug", "bug", " ", "x", "Bug "]` → the card shows exactly two chips, **`Bug`** then **`x`**. Then: one tag of **31+ chars** → 422 "each tag must be at most 30 characters"; **11 distinct** tags → 422 "at most 10 tags are allowed"; **11 raw tags that dedupe to 10** → accepted. A task with **no tags** → the `.card-tags` row is **gone from the DOM**.                                                                                                                                  | All server-side in`_normalize_tags()` (`models.py`); the card renders what the server returned. The order matters: trim → drop blanks → length check → casefold-dedupe → count check. Chip colour comes from the casefolded text (`tagHue()`), so `Bug` and `bug` colour the same. Colour is never stored.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| **B11** | The tag chip editor works                             | In the modal's Tags box: type`api` + **Enter** → a chip appears, the box clears, **the form does not submit**. Type `web` + **comma** → same. **Backspace** in an empty box removes the last chip. A chip's **×** removes that chip. **Submission:** add chips, then type a tag and click **Save without pressing Enter** - the staged text is still committed and appears in `tags`. Confirm the raw text box never posts itself.                                                                                         | `#tag-entry` is deliberately **unnamed** so it cannot post. Submit calls `commitTagEntry()` before building the payload, which captures staged text. `addTagChip()` also dedupes case-insensitively and drops blanks client-side, mirroring B10. `tags` is always an array, never `null`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                |
| **B12** | Filters run client-side and never fire a request      | With Network open, toggle**Overdue only** and change **Tag** → **zero** requests; the board re-renders from memory and counts follow the filtered set (B1). **AND:** overdue-on + a tag shows only tasks matching both. **Case-insensitive:** a task tagged `Bug` matches the `bug` option. **Rebuild:** create a task with a new tag → the option appears after the refresh. **Fallback:** select a tag, then edit away the only task carrying it → the select falls back to **"All tags"** and shows the full board. | Filters are pure re-renders, never fetches.`tagFilter` holds a lowercased value; option values are lowercased while labels keep their casing. `rebuildTagOptions()` clears `tagFilter` when the selected tag no longer exists. Filter state survives drags and refreshes, so a card can vanish after a drag - expected.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| **B13** | Modal flows, title validation, dismissal, 422 routing | **Create:** New Task → modal titled "New Task", Title focused. An empty or whitespace-only title → inline "Title is required" and **no request**. A valid title → **201**, modal closes, board refreshes. **Edit:** a card's **Edit** → modal titled "Edit Task", pre-filled from memory including due date and tag chips. **Dismissal:** Cancel, ✕, overlay click, and **Escape** each close without saving. **Server 422:** errors land in the matching field slot and the modal stays open.                           | A blank assignee sends`null`; an empty description stays `""`; an empty due date sends `null`. Errors with a `loc` list route to field slots (`fieldFromLoc()` skips a trailing index, so a per-tag error still lands on the tags slot); a string `detail` or an unmapped field goes to the form banner, appended so errors don't overwrite each other. **Known defect - lock as-is:** the modal always resends `status`, and `update_task` runs `validate_status_transition()` whenever `status` is present. Same → same is invalid, so **saving an edit without changing status returns 422** (`Invalid status transition from ToDo to ToDo…`) in the **form banner**. An edit only succeeds alongside one of the three permitted transitions. Verified by direct `PATCH`. |

## Notes on scope

- **13 rows, not 12.** The listed behaviors add up to thirteen (5 rendering + 2 drag/drop
  + 2 due dates + 2 tags + 1 filters + 1 modals). None were merged, so nothing is lost.
- **B13 records a live defect.** Saving an edit without touching status is broken. It is
  written down because that is what a contract is for; fixing it is a separate decision.
  While it stands, B9's edit rows can only be exercised alongside a valid status change.
- **B2's tie-break is recorded as inert**, not as what the comments claim. Asserting an id
  order would lock in a rule the code never applies.

---

# Verification - Due Dates & Tags

Verifies the two features from [user-stories.md](user-stories.md) (DD-1…DD-5, TG-1…TG-5),
decided in [mini-adr.md](mini-adr.md). Covers contract rows **B8, B9** (due dates),
**B10, B11** (tags), and **B12** (filters over both).

**Everything in §1, §2, §3 and §5 passes as of 2026-07-17.** **No refactor is needed for
now** - both features work as specified, so none is planned. §4 is there for whenever one
happens, and its "After" column stays an empty template until then.

The evidence is not all the same kind:

- **§1, §2, §5** - command output pasted verbatim. Re-run the commands to reproduce.
- **§3** - manual browser checks, attested by the tester (Rami Al Timani, 2026-07-17).
  Nothing automated backs these up.

## 1. Baseline

The starting point every later result is measured against.

| Item         | Value                                                                                |
| ------------ | ------------------------------------------------------------------------------------ |
| Date of run  | 2026-07-17                                                                           |
| Commit       | `ed4d739` (*create prompt log*)                                                  |
| Branch       | `mid-course-project`                                                               |
| Working tree | Clean - only`docs/midcourse/verification.md` untracked (this file)                 |
| Python       | 3.12.3                                                                               |
| Key deps     | fastapi 0.139.0 · pydantic 2.13.4 · uvicorn 0.49.0 · httpx 0.28.1 · pytest 9.1.1 |
| Storage      | In-memory dict per ADR-001 Option A -**the board is empty on every restart**   |

The backend boots and both features round-trip through the API:

```console
$ venv/bin/uvicorn app.main:app --port 8000

$ curl -s localhost:8000/health
{"status":"ok","timestamp":"2026-07-17T11:52:39.447576+00:00"}      [HTTP 200]

$ curl -s localhost:8000/tasks
[]                                                                  [HTTP 200]

$ curl -s -X POST localhost:8000/tasks -H 'Content-Type: application/json' \
    -d '{"title":"Baseline","due_date":"2026-08-01","tags":["Bug","bug","  ","API","Bug "]}'
{"id":"b4762a77-3885-4351-a019-acc2e2ffbd13","title":"Baseline","description":"",
 "status":"ToDo","priority":"Medium","assignee":null,
 "due_date":"2026-08-01","tags":["Bug","API"],
 "created_at":"2026-07-17T11:52:39.469634Z","updated_at":"2026-07-17T11:52:39.469634Z"}
                                                                    [HTTP 201]
```

**Baseline: PASS.** One request covers both features at the API boundary: the future due
date stores date-only (B8/B9), and the five raw tags normalize to `["Bug","API"]` -
casefold-dedupe with the first casing kept, blank dropped, order preserved (B10). The
fresh process returns `[]`, so no leftover state affects any result below.

## 2. Backend tests

```console
$ venv/bin/python -m pytest tests/ -q
59 passed in 0.31s

$ venv/bin/python -m pytest tests/test_due_dates.py tests/test_tags.py -q
41 passed in 0.22s
```

**Full suite: 59 passed, 0 failed.** **41 of those cover the two features** - 21 in
`test_due_dates.py`, 20 in `test_tags.py`. Mapped to the stories:

| Story                                           | Tests                                                                                                                                                                                                                                                                                                                                                                                                            | Result    |
| ----------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| **DD-1** date-only, no time-of-day        | `test_due_date_is_date_only_and_rejects_a_timestamp`, `test_create_task_accepts_a_future_due_date`, `test_due_date_defaults_to_null_when_omitted`                                                                                                                                                                                                                                                          | 3 passed  |
| **DD-2** clearing a due date              | `test_patch_with_explicit_null_clears_the_due_date`, `test_patch_without_the_due_date_key_leaves_it_untouched`, `test_patch_can_clear_a_due_date_that_is_already_in_the_past`, `test_patch_changes_the_due_date`                                                                                                                                                                                         | 4 passed  |
| **DD-3** overdue is derived, never stored | `test_overdue_is_not_a_response_field`, `test_a_past_due_task_still_returns_its_due_date_and_status_for_the_client_to_derive_from`                                                                                                                                                                                                                                                                           | 2 passed  |
| **DD-4** filtering is client-side         | `test_list_tasks_ignores_an_overdue_query_param_and_returns_every_task`, `test_list_tasks_returns_due_date_on_every_task_so_the_client_can_filter`                                                                                                                                                                                                                                                           | 2 passed  |
| **DD-5** no backdating                    | `test_create_rejects_a_past_due_date`, `test_patch_rejects_moving_a_due_date_into_the_past`, `test_patch_allows_resending_an_unchanged_due_date_that_is_now_past`, `test_create_task_accepts_today_as_due_date`, `test_create_rejects_malformed_due_date_on_the_due_date_field` (5 params), `test_patch_with_a_past_due_date_on_a_missing_task_returns_404_not_422`                                  | 10 passed |
| **TG-1** tags on a task                   | `test_create_task_accepts_tags`, `test_tags_default_to_an_empty_list_when_omitted`, `test_surrounding_whitespace_is_stripped_from_each_tag`, `test_a_non_string_tag_is_rejected`                                                                                                                                                                                                                         | 4 passed  |
| **TG-2** removing tags                    | `test_patch_with_an_empty_list_removes_every_tag`, `test_patch_replaces_the_tag_list_rather_than_appending`, `test_patch_without_the_tags_key_leaves_them_untouched`, `test_patch_with_explicit_null_tags_returns_422`, `test_a_status_transition_preserves_tags`                                                                                                                                      | 5 passed  |
| **TG-3** filtering is client-side         | `test_list_tasks_ignores_a_tag_query_param_and_returns_every_task`, `test_list_tasks_returns_tags_on_every_task_so_the_client_can_filter`                                                                                                                                                                                                                                                                    | 2 passed  |
| **TG-4** case-insensitive uniqueness      | `test_tags_are_deduped_case_insensitively_keeping_the_first_casing`, `test_dedupe_preserves_the_order_of_the_surviving_tags`                                                                                                                                                                                                                                                                                 | 2 passed  |
| **TG-5** blanks dropped, limits enforced  | `test_blank_and_whitespace_only_tags_are_dropped_without_an_error`, `test_a_list_of_only_blank_tags_saves_as_an_empty_list`, `test_a_tag_over_the_length_limit_returns_422_on_the_tags_field`, `test_a_tag_at_the_length_limit_is_accepted`, `test_too_many_tags_returns_422_on_the_tags_field`, `test_the_maximum_number_of_tags_is_accepted`, `test_the_tag_count_limit_is_applied_after_dedupe` | 7 passed  |

## 3. Manual browser checks

**Status: 28/28 PASS.** Run by Rami Al Timani on 2026-07-17 against commit `ed4d739`.
Rows 1–2 needed the system clock moved forward a day, reloaded, then moved back - see the
gap below.

> **Provenance:** unlike §1, §2 and §5, this section is the tester's attestation, not
> captured output. The agent that wrote this file has no browser. Recorded as reported.

Setup:

```console
$ cd task-tracker/backend && venv/bin/uvicorn app.main:app --port 8000
# then open task-tracker/frontend/index.html with DevTools → Network open
```

Storage is in-memory (ADR-001), so the board starts empty on every restart - seed each
scenario first.

> **Testability gap - read before rows 1–2.** An overdue task **cannot be created on
> demand**. `POST` rejects a past `due_date` (`TaskCreate._check_due_date`) and `PATCH`
> rejects moving one into the past (`validate_due_date_change`), and ADR-001's in-memory
> dict is only reachable from inside the Uvicorn process. There is no back door.
>
> DD-5 (no backdating) and DD-3 (overdue styling) pull against each other: the rule that
> blocks backdating also makes the overdue state unreachable except by waiting.
> **Overdue rendering is the least-verified behavior in the feature** - no backend test
> covers it, and it cannot be reproduced by hand. Three options, none free:
>
> 1. **Move the system clock** forward a day, reload, move it back. Fastest, but
>    `isOverdue()` reads local time, so the clock is the input under test.
> 2. **Create a task due today, check tomorrow.** Honest, but needs the server up
>    overnight - unlikely with in-memory storage.
> 3. **Stub it in DevTools:** override `todayISO()` in the console and call `render()`.
>    Tests the rule, not the wiring.
>
> **Used on 2026-07-17: option 1.** Recorded because these are not equal evidence. Under a
> clock change the clock is both the fixture and the input, so this confirms the rule
> fires but not that it fires **on the right day** in normal use. Re-confirm with option 2
> whenever a task ages past its date naturally.

### 3a. Due dates (B8, B9)

| #  | Step                                                                | Expected                                                                                                                                                    | Result                                   |
| -- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 1  | Get a ToDo task into the overdue state by one of the routes above   | Card reads`Overdue · <date>`, overdue styling on `.due-date` and `.card`                                                                             | **PASS** - via system-clock change |
| 2  | Same task: drag ToDo → InProgress → Done                          | Once**Done** the card is no longer overdue - text returns to `Due <date>`, styling drops, no reload needed                                          | **PASS**                           |
| 3  | Create a task due**today**                                    | `Due <date>`, **not** overdue                                                                                                                       | **PASS**                           |
| 4  | Create a task with**no** due date, inspect the card           | `.due-date` is **absent from the DOM**, not blank or hidden                                                                                         | **PASS**                           |
| 5  | New Task → title + a**past** date → Save                    | **422**; modal stays open; the error sits in the due-date slot (`data-error-for="due_date"`), not the banner                                        | **PASS**                           |
| 6  | New Task → title, Due Date left**empty** → Save             | Body contains`"due_date": null`; **201**; card renders with no date                                                                                 | **PASS**                           |
| 7  | Edit a task, clear the date, change status ToDo → InProgress, Save | `"due_date": null` sent; **200**; the date disappears from the card                                                                                 | **PASS**                           |
| 8  | Edit a task with a past date: leave it, change status, Save         | **200** - resending an unchanged past date is allowed                                                                                                 | **PASS**                           |
| 9  | Edit a task: set a**past** date *and* change status, Save   | **422** on the **due-date slot**; modal stays open                                                                                              | **PASS**                           |
| 10 | Edit any task and Save**without touching status**             | **422** in the **form banner**: `Invalid status transition from ToDo to ToDo…` - the B13 defect. Steps 7–9 change status to route around it | **PASS**                           |

### 3b. Tags (B10, B11)

| #  | Step                                                                                        | Expected                                                                                | Result         |
| -- | ------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | -------------- |
| 11 | In the Tags box type`Bug` **Enter**, `bug` **Enter**, `x` **Enter** | The second is**rejected client-side** - only `Bug` and `x` appear             | **PASS** |
| 12 | Commit a tag with**Enter**; commit another with **comma**                       | Each adds a chip, clears the box, and**does not submit the form**                 | **PASS** |
| 13 | **Backspace** in an empty tag box                                                     | Removes the**last** chip                                                          | **PASS** |
| 14 | Click a chip's**×**                                                                        | Removes**that** chip only                                                         | **PASS** |
| 15 | Add two chips, type a third, click**Save without pressing Enter**                     | `tags` contains **all three** - staged text is committed on submit              | **PASS** |
| 16 | Inspect that request body                                                                   | `tags` is an **array of the chips**; `#tag-entry` never posts (it is unnamed) | **PASS** |
| 17 | `curl` a task with `["Bug","bug"," ","x","Bug "]`, reload                               | Card shows exactly**two** chips, `Bug` then `x` - matches §1                 | **PASS** |
| 18 | Create a task with a tag of**31+ chars**                                              | **422** "each tag must be at most 30 characters", on the **tags** slot      | **PASS** |
| 19 | Create a task with**11 distinct** tags                                                | **422** "at most 10 tags are allowed"                                             | **PASS** |
| 20 | Create a task with**11 raw tags that dedupe to 10**                                   | **Accepted** - the count runs *after* deduping                                  | **PASS** |
| 21 | Create a task with**no** tags, inspect the card                                       | `.card-tags` is **absent from the DOM**, not an empty div                       | **PASS** |
| 22 | Compare chips`Bug` and `bug` across two cards                                           | Same colour - the hue comes from the casefolded text; colour is never stored            | **PASS** |

### 3c. Filters over both features (B12)

| #  | Step                                                                     | Expected                                                          | Result         |
| -- | ------------------------------------------------------------------------ | ----------------------------------------------------------------- | -------------- |
| 23 | With Network open, toggle**Overdue only** and change **Tag** | **Zero requests** - a pure re-render from memory            | **PASS** |
| 24 | Overdue-on**+** a tag selected                                           | Only tasks matching**both** show (AND, not OR)              | **PASS** |
| 25 | Task tagged`Bug`, select the `bug` option                            | It**matches** - the comparison is case-insensitive          | **PASS** |
| 26 | Apply a filter, then read the count pills                                | Counts reflect the**filtered** set, not the full board (B1) | **PASS** |
| 27 | Create a task with a brand-new tag                                       | The option**appears** after the refresh                     | **PASS** |
| 28 | Select a tag, then edit away the only task carrying it                   | The select falls back to**"All tags"** and shows the full board   | **PASS** |

## 4. Before / after the refactor

**No refactor is needed for now**, so this table is a baseline held in reserve rather than
a task. "Before" is the observed state at `ed4d739`, from §1, §2, and the direct `PATCH`
probes in the contract above. "After" is left **empty on purpose** - filling it now would
be a prediction, not evidence.

**How to use this if a refactor happens:** re-run §1 and §2, re-run the §3 checklist, and fill "After"
with what you actually see. The refactor is correct only if every After cell reads
*identical*. Anything else is a behavior change and needs a deliberate decision - not a
quiet edit to this table.

| Contract row                                     | Before (observed at`ed4d739`)                                                                                                                                                                                                                                                                 | After (fill in post-refactor) |
| ------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- |
| **B8** - due date renders; overdue derived | Derived at render time by`isOverdue()`; not a response field (`test_overdue_is_not_a_response_field` passes). Done never overdue, no date never overdue, today not overdue. `.due-date` removed from the DOM when there is no date. Uses local `todayISO()`, not `toISOString()`.     | `[ ]`                       |
| **B9** - due date validation               | Create: past date → 422 on`loc: ["body","due_date"]`. Edit: `None` allowed; an unchanged date allowed even when past; moving a date into the past → 422 on the same slot. Two rules (`TaskCreate` field_validator vs `validate_due_date_change`). Verified live and by 10 DD-5 tests. | `[ ]`                       |
| **B10** - tags render; normalization       | `["Bug","bug","  ","API","Bug "]` → `["Bug","API"]` (§1). Fixed order: trim → drop blanks → length check → casefold-dedupe → count check. Caps: 30 chars per tag, 10 tags, counted **after** dedupe. `.card-tags` removed from the DOM when empty.                            | `[ ]`                       |
| **B11** - tag chip editor                  | Chips are what gets submitted;`#tag-entry` is unnamed so it never posts. Enter/comma commit without submitting; Backspace-on-empty pops the last chip; × removes one; `commitTagEntry()` captures staged text on submit. `tags` is never `null`.                                       | `[ ]`                       |
| **B12** - filters (tag + overdue)          | Client-side only, zero requests. AND-combined. Tag match lowercased on both sides. Options rebuilt on every fetch; a vanished selected tag falls back to "All tags".                                                                                                                            | `[ ]`                       |
| **B13** - edit-modal defect                | Editing without changing status →**422** `Invalid status transition from ToDo to ToDo…` in the **form banner**. Verified by live `PATCH` and pinned by `test_patch_same_status_returns_422`.                                                                                | `[ ]`                       |
| Full suite                                       | 59 passed / 0 failed (41 of them due-date + tag)                                                                                                                                                                                                                                                | `[ ]`                       |
| API wire format                                  | `due_date: "YYYY-MM-DD" \| null`; `tags: list[str]`; no `overdue` field                                                                                                                                                                                                                    | `[ ]`                       |

## 5. Break tests

Each break test answers one question: **would these tests notice if the rule were wrong?**
A test that passes against broken code proves nothing. Method: mutate the rule, run the
suite, confirm the *expected* test fails, restore, confirm green. Three below; all three
caught their mutation.

### Break test 1 - DD-5: the "unchanged date" guard

The subtlest rule in the feature, and the wrinkle ADR-001 flagged: a task created with a
valid future date must stay editable after that date passes.

**Mutation** - `app/business_rules.py`, `validate_due_date_change()`, removed:

```python
    if new == current:
        return
```

**Caught:**

```console
$ venv/bin/python -m pytest tests/test_due_dates.py -q
        response = client.patch(
            f"/tasks/{created['id']}",
            json={"title": "still editable", "due_date": stale.isoformat()},
        )
>       assert response.status_code == 200
E       assert 422 == 200
E        +  where 422 = <Response [422 Unprocessable Entity]>.status_code

tests/test_due_dates.py:222: AssertionError
FAILED tests/test_due_dates.py::test_patch_allows_resending_an_unchanged_due_date_that_is_now_past
1 failed, 20 passed in 0.16s
```

**Restored →** `git diff` empty, `21 passed in 0.13s`.

**Verdict: PASS.** Exactly one test failed, and it was the right one. The other 20 staying
green is the point: this mutation is invisible to every test except the one written for it.

### Break test 2 - TG-4: case-insensitive dedupe

**Mutation** - `app/models.py`, `_normalize_tags()`, casefold-dedupe → exact-match dedupe:

```python
-        key = stripped.casefold()
+        key = stripped
```

**Caught:**

```console
$ venv/bin/python -m pytest tests/test_tags.py -q
FAILED tests/test_tags.py::test_tags_are_deduped_case_insensitively_keeping_the_first_casing
FAILED tests/test_tags.py::test_dedupe_preserves_the_order_of_the_surviving_tags
FAILED tests/test_tags.py::test_the_tag_count_limit_is_applied_after_dedupe
3 failed, 17 passed in 0.18s
```

**Restored →** `git diff` empty, `20 passed`.

**Verdict: PASS.** Three failures rather than one, because casefolding also holds up the
order and count rules - both can only be checked on a correctly deduped list. Broad, but
correctly aimed: nothing outside TG-4's blast radius moved.

### Break test 3 - TG-5: count checked *after* dedupe

Break test 2 tripped three tests at once, which leaves a question: does the count-ordering
rule have its **own** test, or was it only collateral? This isolates it.

**Mutation** - `app/models.py`, count check hoisted to the top of `_normalize_tags()` so it
counts **raw input** instead of the deduped list:

```python
 def _normalize_tags(value: list[str]) -> list[str]:
+    if len(value) > MAX_TAGS:
+        raise ValueError(f"at most {MAX_TAGS} tags are allowed")
     ...
-    # Counted after deduping, so 11 raw tags collapsing to 10 distinct ones is valid.
-    if len(normalized) > MAX_TAGS:
-        raise ValueError(f"at most {MAX_TAGS} tags are allowed")
     return normalized
```

**Caught:**

```console
$ venv/bin/python -m pytest tests/test_tags.py -q
FAILED tests/test_tags.py::test_the_tag_count_limit_is_applied_after_dedupe
1 failed, 19 passed in 0.14s
```

**Restored →** `git diff` empty; full suite `59 passed in 0.31s`; working tree clean.

**Verdict: PASS**, and it answers the question. Exactly one test failed, so
"count after dedupe" has its own guard and was not just collateral in break test 2. This is
the mutation most likely to survive a careless refactor: both versions reject 11 distinct
tags and accept 5, and they differ *only* on the input ADR-001 called out - 11 raw tags
collapsing to 10. `test_the_tag_count_limit_is_applied_after_dedupe` is the only thing
standing between that rule and a silent regression.

### Summary

| # | Rule                      | Mutation                             | Expected to fail                                                       | Actually failed   | Verdict        |
| - | ------------------------- | ------------------------------------ | ---------------------------------------------------------------------- | ----------------- | -------------- |
| 1 | DD-5 unchanged-date guard | removed`if new == current: return` | `test_patch_allows_resending_an_unchanged_due_date_that_is_now_past` | that test, alone  | **PASS** |
| 2 | TG-4 casefold dedupe      | `casefold()` → exact match        | the dedupe tests                                                       | 3 TG-4/TG-5 tests | **PASS** |
| 3 | TG-5 count-after-dedupe   | count hoisted above dedupe           | `test_the_tag_count_limit_is_applied_after_dedupe`                   | that test, alone  | **PASS** |
