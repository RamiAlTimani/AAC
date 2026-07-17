# Prompt Log — Due Dates & Tags

Chronological record of the prompts used to add the two mid-course features
(**Due Dates & Overdue Filter**, **Tags / Labels**) to the Task Tracker.

Each entry keeps the prompt **exactly as it was sent**, followed by a summary of
what the AI produced and where it landed in the repo.

| #                                    | Prompt                    | Output                                                          | Commit               |
| ------------------------------------ | ------------------------- | --------------------------------------------------------------- | -------------------- |
| [1](#1--user-stories)                | User stories              | `docs/midcourse/user-stories.md`                                 | `9c39a94`            |
| [2](#2--architecture-options)        | Two lightweight architectures | Option A / Option B proposal (input to the ADR)              | —                    |
| [3](#3--architecture-decision-record) | ADR                      | `docs/midcourse/mini-adr.md`                                     | `628f05a`            |
| [4](#4--backend--due-date-field)     | Due date field            | `app/models.py`, `app/storage.py`                                | `7b9fd5c`, `328e91e` |
| [5](#5--backend--tags-field)         | Tags field                | `app/models.py`, `app/storage.py`                                | `7b9fd5c`, `328e91e` |
| [6](#6--backend--update-path-rule)   | Update-path due-date rule | `app/business_rules.py`, `app/routers/tasks.py`                  | `9882eca`, `2de2f36` |
| [7](#7--tests)                       | Pytest coverage           | `tests/test_due_dates.py`, `tests/test_tags.py`                  | `573d68d`            |
| [8](#8--frontend--modal-and-cards)   | Modal + card rendering    | `frontend/index.html`, `frontend/app.js`, `frontend/style.css`   | `0a6635a`            |
| [9](#9--frontend--filter-bar)        | Overdue + tag filter bar  | `frontend/index.html`, `frontend/app.js`, `frontend/style.css`   | `0a6635a`            |

---

## 1 — User stories

**Goal:** turn the two chosen features into reviewable, testable user stories.

### Prompt

```text
You are a product owner writing user stories for a small development team.

Context:
I am building a Task Tracker web application with a Python/FastAPI backend and a simple web frontend.
@task-tracker/

I want to include thses new features:

- Due dates + overdue filter
- Tags / labels

Explicitly out of scope:

- authentication
- user accounts
- multi-tenancy or per-user task lists
- real-time updates
- mobile app
- notifications
- production database or deployment

Target user:
A solo developer or small team managing work in a single shared task list.
Task:
Generate 3-5 user stories in the format: As a [role], I want [feature] so that [benefit].

Constraints:

- Use "team member" as the main role unless another role is clearly needed.
- For each story, include 2-3 acceptance criteria that are specific and testable.
- Cover happy paths and at least one failure case across the set.
- Do not add features outside the scope above.

Output format:
Return a table with columns: ID, Story, Acceptance Criteria, Notes / Assumptions.
```

### What AI delivered

- `docs/midcourse/user-stories.md` (47 lines) — two tables of stories with the
  requested columns, grounded in the existing `Task` schema.
- **DD-1 … DD-5** for due dates and **TG-1 … TG-5** for tags. These IDs became the
  shared vocabulary for every later prompt, the ADR, and the test names.
- Failure cases were covered as asked: DD-5 (malformed or backdated date → 422) and
  TG-5 (over-length or over-count tags → 422, blank tags dropped).
- Two decisions were recorded as assumptions rather than code: overdue is *derived at
  render time*, never stored; due dates are date-only, with no time-of-day.

---

## 2 — Architecture options

**Goal:** see two genuinely different storage approaches before committing to one.

### Prompt

```text
You are a senior backend developer helping me evaluate lightweight architectures for a learning project.

Context:
I am building a Task Tracker application with a Python/FastAPI backend and a simple web frontend.

@task-tracker/

New reviewed requirements:
@docs/user-stories.md

Constraints:

- This is a learning project, not production software.
- The backend must use Python, FastAPI, and Pydantic for validation.
- I want a REST API backend and a separate simple web frontend.
- Keep the tech stack simple, well-documented, and easy to run locally.
- No authentication or multi-tenancy.
- Do not suggest microservices, Docker, cloud deployment, or production database setup.

Task:
Propose two different lightweight architectures for the new reviewed requirements:

- Option A should be the simplest local-storage approach appropriate for a first learning project.
- Option B may use a lightweight local database approach if it improves realism without overcomplicating the project.

For each option, provide:

1. Tech stack and data storage choice
2. Folder structure
3. Data model sketch with Pydantic fields and constraints
4. Three trade-offs compared to the other option

Output format:
Return Option A and Option B in clearly separated sections. Do not choose for me.
```

### What AI delivered

- Two separated proposals and no recommendation, as instructed:
  - **Option A** — keep the in-memory module-level dict; `due_date` as an optional
    `date` and `tags` as a plain `list[str]` on the task.
  - **Option B** — SQLite via SQLModel, with tags modelled as a related entity.
- Each option came with a folder structure, a Pydantic model sketch, and three
  trade-offs against the other.
- No files were written — this was a decision input only. The comparison carried into
  prompt 3 and became the "Alternatives considered" section of the ADR.

---

## 3 — Architecture Decision Record

**Goal:** record the choice, the rejected alternative, and the reasoning behind both.

### Prompt

```text
Write an Architecture Decision Record (ADR) for this project in **@docs/mini-adr.md**

Decision: Option A
Reasoning:  More aligned with project requirements

Make sure to explain how we are implementing the two new features including the folder structure, what was Option B about  (the alternative) and why it was rejected.
```

### What AI delivered

- `docs/midcourse/mini-adr.md` (269 lines) — **ADR-001, status Accepted**: keep the
  in-memory dict, with no database, no ORM, and no new dependency.
- A per-file implementation plan and folder structure for both features.
- An explanation of Option B (SQLite + SQLModel, tags as an entity) and why it was
  rejected for a learning project at this scope.
- The scope call the rest of the work depends on: overdue detection (DD-3), the
  overdue filter (DD-4), and the tag filter (TG-3) are all **client-side**, and
  `GET /tasks` gains no new query params.
- The "two wrinkles" section that later forced the update-path rule in prompt 6 —
  the reason a `due_date` field validator on `TaskUpdate` would be wrong.

---

## 4 — Backend — due date field

**Goal:** add `due_date` to the models and storage, one feature at a time.

### Prompt

```text
You are a senior Python backend engineer. UPDATE TWO EXISTING files in a FastAPI Task Tracker REST API.

Context:

- This project already has a working /health endpoint (app/routers/health.py) and full
  CRUD /tasks endpoints (app/routers/tasks.py). Both are passing tests. DO NOT touch them.
- @task-tracker/backend/app/models.py and @task-tracker/backend/app/storage.py ALREADY EXIST
  and work. You are MODIFYING them in place, not writing them from scratch. Preserve all
  existing fields, validators, function signatures, and behavior exactly as-is unless this
  spec explicitly changes them.
- This module uses in-memory storage only. ADR-001 is accepted: keep the module-level dict,
  no database, no ORM, no new dependency. @docs/mini-adr.md
- You are adding ONE feature, per user stories DD-1..DD-5:

  - Feature 1: Due Dates & Overdue Filter
- A separate feature (Tags / Labels, TG-1..TG-5) is handled in its own step. DO NOT add
  tags, MAX_TAGS, MAX_TAG_LEN, or any tag normalization in this step.
- Relevant user stories (context only; the spec below is authoritative):

  - DD-1: POST/PATCH accept an optional `due_date` (ISO 8601 date-only, e.g. 2026-07-20).
    Blank saves as `due_date: null`; existing tasks without a due date are unaffected.
  - DD-2: An explicit `"due_date": null` on PATCH clears the date; an absent key leaves it
    alone.
  - DD-5: A malformed date (2026-13-40, "soon") returns 422. A well-formed date EARLIER
    THAN TODAY also returns 422 — backdating is not allowed. Today or later is accepted.

============================================================
FILE 1 - @task-tracker/backend/app/models.py   (UPDATE — do not rewrite from scratch)
======================================================================================

Use Pydantic v2 syntax only.

KEEP UNCHANGED: TaskStatus, TaskPriority, the existing _validate_title helper and its
title validators, HealthResponse, and every existing field on all three task models.

ADD to TaskCreate:

- due_date: Optional[date] = None      # date-only, no time-of-day
- A field_validator for due_date that raises ValueError if the date is earlier than
  date.today(). Today or later is accepted. None is accepted (no due date).

ADD to TaskUpdate:

- due_date: Optional[date] = None
- DO NOT add a past-date field_validator to TaskUpdate.due_date. This is deliberate: a task
  validly created with a future due date must stay editable after that date passes, and the
  edit modal resends the unchanged due_date. Rejecting a past date here would make such
  tasks permanently uneditable. The "past date on update" rule needs the EXISTING task to
  tell "changing the date" from "resending the same date", so it belongs in
  app/business_rules.py in a later step. Not in this file.

ADD to TaskResponse:

- due_date: Optional[date]
- DO NOT add an `overdue` field. Overdue is derived at render time from
  (status != "Done" and due_date < today) and is never stored or returned.

DO NOT include id, created_at, or updated_at in TaskCreate or TaskUpdate.

============================================================
FILE 2 - @task-tracker/backend/app/storage.py   (UPDATE — do not rewrite from scratch)
=======================================================================================

Keep the in-memory module-level dictionary:
_tasks: dict[str, TaskResponse] = {}

Keep these functions with their EXACT existing signatures:

- add_task(payload: TaskCreate) -> TaskResponse
- get_all_tasks(status=None, priority=None) -> list[TaskResponse]
- get_task_by_id(task_id: str) -> Optional[TaskResponse]
- update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]
- delete_task(task_id: str) -> bool
- _reset() -> None

The ONLY change to this file is in add_task, which must now also pass through:

- due_date=payload.due_date

DO NOT change update_task. It already uses payload.model_dump(exclude_unset=True), which is
what makes an explicit `"due_date": null` ("clear it") distinguishable from an absent key
("leave it alone"). This behavior is load-bearing for DD-2 — preserve it exactly.

DO NOT add a due_date filter parameter to get_all_tasks. Overdue filtering (DD-4) is
client-side over the already-fetched list.

HARD CONSTRAINTS:

- DO NOT use SQLAlchemy, SQLModel, Alembic, a database, or an ORM.
- DO NOT use Pydantic v1 syntax: no @validator, no class Config, no .dict().
- DO NOT include id, created_at, or updated_at in TaskCreate or TaskUpdate.
- DO NOT add print or logging statements.
- DO NOT create or modify API routes in this step.
- DO NOT modify app/main.py, app/routers/*, or app/business_rules.py.
- DO NOT add an `overdue` stored field.
- DO NOT add tags or any tag-related code in this step.
- DO NOT remove or weaken any existing field, validator, or function.
- DO NOT wrap the answer in long explanation.

Output only two code blocks, each preceded by:

# FILE: @task-tracker/backend/app/models.py

# FILE: @task-tracker/backend/app/storage.py
```

### What AI delivered

- `app/models.py` — `due_date: Optional[date]` on `TaskCreate`, `TaskUpdate`, and
  `TaskResponse`, with a Pydantic v2 `field_validator` on **`TaskCreate` only**
  (`_check_due_date`) rejecting dates earlier than `date.today()`.
- `TaskUpdate` deliberately got **no** past-date validator, and `TaskResponse` got
  **no** `overdue` field — both as specified.
- `app/storage.py` — a single added line in `add_task` passing `due_date` through.
  `update_task`'s `exclude_unset=True` was left untouched, preserving DD-2.
- Both files were edited in place; no existing field, validator, or signature changed.

---

## 5 — Backend — tags field

**Goal:** add `tags` to the models and storage, isolated from the due-date work.

### Prompt

```text
You are a senior Python backend engineer. UPDATE TWO EXISTING files in a FastAPI Task Tracker REST API.

Context:

- This project already has a working /health endpoint (app/routers/health.py) and full
  CRUD /tasks endpoints (app/routers/tasks.py). Both are passing tests. DO NOT touch them.
- @task-tracker/backend/app/models.py and @task-tracker/backend/app/storage.py ALREADY EXIST
  and work. You are MODIFYING them in place, not writing them from scratch. Preserve all
  existing fields, validators, function signatures, and behavior exactly as-is unless this
  spec explicitly changes them.
- This module uses in-memory storage only. ADR-001 is accepted: keep the module-level dict,
  no database, no ORM, no new dependency. @docs/mini-adr.md
- You are adding ONE feature, per user stories TG-1..TG-5:

  - Feature 2: Tags / Labels
- A separate feature (Due Dates & Overdue Filter, DD-1..DD-5) is handled in its own step.
  DO NOT add due_date or any due-date validation in this step.
- Relevant user stories (context only; the spec below is authoritative):

  - TG-1: POST/PATCH accept a `tags` array of strings. Tags are trimmed and de-duplicated
    case-insensitively before saving. A task with no tags saves with `tags: []`.
  - TG-2: Tags are cleared with `"tags": []`, not with `"tags": null`.
  - TG-4: Case-insensitive uniqueness — `Bug` and `bug` are one tag; the first casing seen
    wins.
  - TG-5: An empty/whitespace-only tag is DROPPED, not an error. A tag over the length
    limit, or more than the count limit, returns 422 with a field-level error.

============================================================
FILE 1 - @task-tracker/backend/app/models.py   (UPDATE — do not rewrite from scratch)
======================================================================================

Use Pydantic v2 syntax only.

KEEP UNCHANGED: TaskStatus, TaskPriority, the existing _validate_title helper and its
title validators, HealthResponse, and every existing field on all three task models.

ADD these module-level constants:

- MAX_TAGS = 10
- MAX_TAG_LEN = 30

ADD a module-level helper `_normalize_tags(value: list[str]) -> list[str]` that runs in
EXACTLY this order:

1. Strip whitespace from each tag.
2. Drop empty/whitespace-only tags SILENTLY (TG-5: dropped, NOT a 422).
3. Raise ValueError if any remaining tag is longer than MAX_TAG_LEN.
4. De-duplicate case-insensitively using casefold(); the FIRST casing seen wins, and the
   order of surviving tags is preserved.
5. Raise ValueError if more than MAX_TAGS tags remain.

The count check MUST happen AFTER de-duplication (step 5 after step 4), so 11 raw tags that
collapse to 10 distinct tags is VALID and must be accepted.
=> Therefore DO NOT use Annotated[list[str], Field(max_length=MAX_TAGS)]. A Field constraint
   is applied during core validation, BEFORE the field_validator runs, so it would reject the
   raw list before de-duplication and break this rule. Enforce the count inside
   _normalize_tags only.

ADD to TaskCreate:

- tags: list[str] = []
- A field_validator for tags that returns _normalize_tags(value).

ADD to TaskUpdate:

- tags: Optional[list[str]] = None
- A field_validator for tags that returns _normalize_tags(value) ONLY when a list is
  provided, and raises ValueError if the value is explicitly None. (`"tags": null` is not a
  valid way to clear tags — TG-2 clears them with `"tags": []`. This matters because the
  storage layer applies updates via model_copy, which does NOT re-validate, so an
  unguarded None would silently corrupt the stored task.)

ADD to TaskResponse:

- tags: list[str]

DO NOT include id, created_at, or updated_at in TaskCreate or TaskUpdate.

============================================================
FILE 2 - @task-tracker/backend/app/storage.py   (UPDATE — do not rewrite from scratch)
=======================================================================================

Keep the in-memory module-level dictionary:
_tasks: dict[str, TaskResponse] = {}

Keep these functions with their EXACT existing signatures:

- add_task(payload: TaskCreate) -> TaskResponse
- get_all_tasks(status=None, priority=None) -> list[TaskResponse]
- get_task_by_id(task_id: str) -> Optional[TaskResponse]
- update_task(task_id: str, payload: TaskUpdate) -> Optional[TaskResponse]
- delete_task(task_id: str) -> bool
- _reset() -> None

The ONLY change to this file is in add_task, which must now also pass through:

- tags=list(payload.tags)   # copy the list — never share the payload's list object with# the stored TaskResponse, or later mutation of one aliases the other

DO NOT change update_task. It already uses payload.model_dump(exclude_unset=True), which is
what makes an explicit `"tags": []` ("clear them", TG-2) distinguishable from an absent key
("leave them alone"). This behavior is load-bearing — preserve it exactly.

DO NOT add a tag filter parameter to get_all_tasks. Tag filtering (TG-3) is client-side over
the already-fetched list.

HARD CONSTRAINTS:

- DO NOT use SQLAlchemy, SQLModel, Alembic, a database, or an ORM.
- DO NOT use Pydantic v1 syntax: no @validator, no class Config, no .dict().
- DO NOT include id, created_at, or updated_at in TaskCreate or TaskUpdate.
- DO NOT add print or logging statements.
- DO NOT create or modify API routes in this step.
- DO NOT modify app/main.py, app/routers/*, or app/business_rules.py.
- DO NOT model tags as a separate entity — they are plain strings on the task.
- DO NOT add due_date or any due-date code in this step.
- DO NOT remove or weaken any existing field, validator, or function.
- DO NOT wrap the answer in long explanation.

Output only two code blocks, each preceded by:

# FILE: @task-tracker/backend/app/models.py

# FILE: @task-tracker/backend/app/storage.py
```

### What AI delivered

- `app/models.py` — `MAX_TAGS = 10` and `MAX_TAG_LEN = 30` as module-level constants,
  plus `_normalize_tags()` implementing the five steps in the required order. The count
  check runs *after* de-duplication, so 11 raw tags collapsing to 10 is accepted.
- `tags: list[str] = []` on `TaskCreate`, `tags: Optional[list[str]] = None` on
  `TaskUpdate` with the explicit-`None` guard (TG-2), and `tags: list[str]` on
  `TaskResponse`.
- No `Field(max_length=...)` constraint, per the prompt's reasoning — validation order
  would have broken the de-duplication rule.
- `app/storage.py` — `add_task` now passes `tags=list(payload.tags)`, copying the list
  so the payload and the stored task never alias.
- Together with prompt 4, these two prompts account for the whole diff in `7b9fd5c`
  (models, +60/-1) and `328e91e` (storage, +3).

---

## 6 — Backend — update-path rule

**Goal:** enforce DD-5 on PATCH, where a field validator structurally cannot work.

### Prompt

```text
You are a senior Python backend engineer. UPDATE TWO EXISTING files in a FastAPI Task Tracker REST API.

Context:

- @task-tracker/backend/app/business_rules.py  and @task-tracker/backend/app/routers/tasks.pyALREADY EXIST and work. You are MODIFYING them in place, not writing them from scratch.
  Preserve all existing rules, signatures, and behavior exactly as-is unless this spec
  explicitly changes them.
- The due_date and tags FIELDS are already implemented in @task-tracker/backend/app/models.py
  and @task-tracker/backend/app/storage.py. DO NOT touch either file. In particular
  TaskCreate.due_date already rejects backdating on create — that half of DD-5 is DONE.
- ADR-001 is accepted: in-memory dict, no database, no ORM, no new dependency.
  @docs/midcourse/mini-adr.md
- You are adding exactly ONE rule: the DD-5 past-date check on the UPDATE path.
- Why this rule cannot be a field_validator on TaskUpdate.due_date (from ADR-001, "Two
  wrinkles this feature must handle"): a task validly created with a future due date must
  stay editable after that date passes, and the edit modal resends the unchanged due_date.
  A naive `due_date < today` validator would make such tasks permanently uneditable. Telling
  "changing the date" from "resending the same date" requires the EXISTING task, which a
  field validator cannot see. So the rule lives in business_rules.py, same shape as the
  existing validate_status_transition.

============================================================
FILE 1 - @task-tracker/backend/app/business_rules.py   (UPDATE — do not rewrite from scratch)
==============================================================================================

KEEP UNCHANGED: VALID_TRANSITIONS, validate_status_transition, and the module docstring's
existing intent.

ADD a function:

    def validate_due_date_change(current: Optional[date], new: Optional[date]) -> None

Rules, in this order:

1. If `new` is None -> return. Clearing a due date is always allowed (DD-2).
2. If `new == current` -> return. Resending an unchanged date is always allowed, EVEN IF that
   date is now in the past. This is the whole reason the rule lives here — do not skip it.
3. If `new < date.today()` -> raise (see below). Today or later is accepted.

HOW IT MUST RAISE — this is the part that is easy to get wrong:

DO NOT raise HTTPException. validate_status_transition raises HTTPException with a string
`detail`, which the frontend can only render in the form banner. DD-5 requires the error to
land on the due-date INPUT, and contract B8 routes a field-level error to its input slot by
reading the `loc` path. A string detail has no loc.

Instead raise fastapi.exceptions.RequestValidationError with a single error dict shaped like
a Pydantic v2 error, so FastAPI's built-in handler renders the standard 422 body:

    raise RequestValidationError([
        {
            "type": "value_error",
            "loc": ("body", "due_date"),
            "msg": "due_date must not be earlier than today",
            "input": new,
        }
    ])

The `loc` MUST be exactly ("body", "due_date") — the tests assert on it.

Add `from datetime import date` and the RequestValidationError import. Keep HTTPException
imported; validate_status_transition still uses it.

Docstring the function with the "resending an unchanged past date is allowed" carve-out and
the reason it raises RequestValidationError rather than HTTPException. That carve-out looks
like a bug to a future reader, so it must say why.

============================================================
FILE 2 - @task-tracker/backend/app/routers/tasks.py   (UPDATE — do not rewrite from scratch)
=============================================================================================

KEEP UNCHANGED: create_task, list_tasks, get_task, delete_task, the router prefix, and every
existing route path, status code, and response_model.

The ONLY change is inside `update_task`. It currently fetches `existing` ONLY when
`payload.status is not None`. The due-date rule needs `existing` too, so restructure the
lookup to happen once when EITHER rule needs it:

- Fetch `existing` if `payload.status is not None` OR `payload.due_date is not None`.
- If `existing is None` in that case, raise the SAME 404 HTTPException with the SAME detail
  string as today: f"Task with id {task_id} not found".
- If `payload.status is not None`: call validate_status_transition(existing.status,
  payload.status) — unchanged.
- If `payload.due_date is not None`: call validate_due_date_change(existing.due_date,
  payload.due_date).
- Leave the trailing `storage.update_task(...)` / None -> 404 path exactly as it is. Do not
  collapse it, even though it is now unreachable for those two branches — it is what handles
  the plain title-only PATCH of a missing task.

`payload.due_date is not None` is the correct trigger and is NOT a bug: an explicit
`"due_date": null` means "clear it", which rule 1 permits anyway, so it never needs the rule
to run. Do not reach for model_fields_set here.

404 MUST take precedence over 422: a PATCH with a past due_date against a nonexistent id
returns 404, not 422. The lookup-then-validate order above already gives you this — do not
reorder it.

Import validate_due_date_change alongside the existing validate_status_transition import.

HARD CONSTRAINTS:

- DO NOT modify app/models.py, app/storage.py, app/main.py, or app/routers/health.py.
- DO NOT add a past-date field_validator to TaskUpdate. See the Context note above.
- DO NOT use Pydantic v1 syntax: no @validator, no class Config, no .dict().
- DO NOT change validate_status_transition or the shape of its HTTPException.
- DO NOT add an `overdue` field, an overdue query param, or a tag query param — DD-4 and TG-3
  are client-side per ADR-001.
- DO NOT add print or logging statements.
- DO NOT add a new dependency.
- DO NOT wrap the answer in long explanation.

Output only two code blocks, each preceded by:

# FILE: task-tracker/backend/app/business_rules.py

# FILE: task-tracker/backend/app/routers/tasks.py
```

### What AI delivered

- `app/business_rules.py` (+33) — `validate_due_date_change(current, new)` sitting next
  to the existing `validate_status_transition`, implementing the three rules in order,
  including the "resending an unchanged past date is allowed" carve-out.
- It raises `RequestValidationError` with `loc: ("body", "due_date")` rather than
  `HTTPException`, so the frontend can route the message to the date input. The
  docstring explains both the carve-out and the choice of exception.
- `app/routers/tasks.py` (+10/-5) — `update_task` now fetches `existing` once when
  either rule needs it, preserving the 404 detail string and keeping 404 ahead of 422.
  The trailing `storage.update_task(...)` / 404 path was left intact.
- `validate_status_transition` and the other four endpoints were untouched.

---

## 7 — Tests

**Goal:** cover the untested branches without touching passing tests or app code.

### Prompt

```text
You are a senior Python developer writing pytest tests for a FastAPI Task Tracker REST API.

Context:

- @task-tracker/backend/tests/test_due_dates.py and @task-tracker/backend/tests/test_tags.py
  ALREADY EXIST and ALL of their tests PASS against the current implementation. You are
  ADDING tests to them in place, not rewriting them. Every existing test is correct — do not
  rename, reword, reorder, delete, or "improve" any of them.
- The features under test are fully implemented. Read them; do not re-derive the rules:
  @task-tracker/backend/app/models.py          (due_date, tags, _normalize_tags)
  @task-tracker/backend/app/storage.py         (in-memory dict; update_task uses exclude_unset)
  @task-tracker/backend/app/business_rules.py  (status transitions + validate_due_date_change)
  @task-tracker/backend/app/routers/tasks.py   (5 endpoints; router prefix is /tasks)
- @task-tracker/backend/tests/conftest.py ALREADY EXISTS and provides the `_reset_storage`
  autouse fixture, the `client` fixture, and the `created_task` fixture. USE THEM. DO NOT
  rewrite, re-declare, or output conftest.py.
- @task-tracker/backend/tests/test_tasks.py ALREADY EXISTS and covers base CRUD. DO NOT
  duplicate it.
- ADR-001 is authoritative on scope: @docs/midcourse/mini-adr.md

The suite currently passes 50/50. It MUST still pass 50-plus-yours after your change. A diff
that touches an existing test is a failed answer.

============================================================
SCOPE BOUNDARY — read before writing a single test
===================================================

Per ADR-001, three behaviors are CLIENT-SIDE and have NO backend surface:

- DD-3 overdue detection: derived at render time as (status != "Done" and due_date < today).
  There is NO `overdue` field on TaskResponse and none is ever stored.
- DD-4 overdue filter and TG-3 tag filter: applied in the frontend over the already-fetched
  list. GET /tasks accepts ONLY `status` and `priority`.

DO NOT assert server-side overdue or tag filtering, and DO NOT invent query parameters to
make a test pass. Test that the backend returns the DATA those features derive from, and that
the absent surface stays absent.

============================================================
FILE 1 - @task-tracker/backend/tests/test_due_dates.py   (UPDATE — append only)
================================================================================

The file already has an `_iso(days_from_today)` helper. REUSE IT. Never hardcode a calendar
date — a test that passes only in 2026 is a broken test.

The file's module docstring says the feature "is not implemented yet". That is now false —
the skip marker is already gone. Rewrite ONLY that stale paragraph to describe the file as
it is. Leave every other docstring alone.

ADD exactly these tests:

Overdue detection (DD-3 — response shape only, per the scope boundary):

- test_a_past_due_task_still_returns_its_due_date_and_status_for_the_client_to_derive_from
  Seed a past-due task through storage (see the seeding note), GET it, and assert due_date
  and status both come back unmodified — the server neither hides nor rewrites a stale date.

Filter returns only overdue tasks (DD-4 — client-side, so pin the absence):

- test_list_tasks_ignores_an_overdue_query_param_and_returns_every_task
  Create a mix, GET /tasks?overdue=true, assert ALL come back. FastAPI ignores unknown query
  params, and that is the point: no server-side filter exists.
- test_list_tasks_returns_due_date_on_every_task_so_the_client_can_filter

Update-path rule coverage (these branches of validate_due_date_change are currently UNTESTED):

- test_patch_with_a_past_due_date_on_a_missing_task_returns_404_not_422
  404 MUST take precedence over 422. The router looks the task up BEFORE validating, so a
  PATCH of {"due_date": <yesterday></yesterday>} against a nonexistent id is a 404. Docstring this — it
  pins the lookup-then-validate ordering in routers/tasks.py.
- test_patch_can_clear_a_due_date_that_is_already_in_the_past
  Seed a past-due task, PATCH {"due_date": null}, assert 200 and due_date is None. Clearing
  is always allowed even when the existing date is stale (validate_due_date_change rule 1).

Seeding note: the API refuses to CREATE a past-dated task, so any past-due fixture must be
written straight into storage, as the existing
test_patch_allows_resending_an_unchanged_due_date_that_is_now_past already does:
    storage._tasks[tid] = storage._tasks[tid].model_copy(update={"due_date": <a past date></a>})

============================================================
FILE 2 - @task-tracker/backend/tests/test_tags.py   (UPDATE)
============================================================

CHANGE the two module-level constants. The file currently redefines them:
    MAX_TAGS = 10
    MAX_TAG_LEN = 30
Replace both with an import from the implementation:
    from app.models import MAX_TAGS, MAX_TAG_LEN
They already exist in models.py. A local copy silently drifts the day someone raises the
limit, and the tests would keep passing while asserting the wrong number.

The `import pytest` line is now unused — the skip marker was its only consumer. Remove it
UNLESS one of your new tests parametrizes.

Rewrite ONLY the stale "not implemented yet" paragraph in the module docstring, as above.

ADD exactly these tests:

Update tags (TG-2 — this guard exists in models.py and is currently UNTESTED):

- test_patch_with_explicit_null_tags_returns_422
  `"tags": null` is not a valid way to clear tags — TG-2 clears them with `[]`. Docstring
  why the guard matters: storage applies updates via model_copy, which does NOT re-validate,
  so an unguarded None would corrupt the stored task.

Preserve tags after unrelated update:

- test_a_status_transition_preserves_tags
  Create a tagged task, PATCH ToDo -> InProgress, assert tags survive untouched. The file
  already covers a title-only PATCH; this covers the OTHER router branch — the one that runs
  validate_status_transition before storage.update_task.

Filter by tag (TG-3 — client-side, so pin the absence):

- test_list_tasks_ignores_a_tag_query_param_and_returns_every_task
- test_list_tasks_returns_tags_on_every_task_so_the_client_can_filter

============================================================
HARD CONSTRAINTS
================

- DO NOT modify, rename, or delete any existing test. Only the two stale docstring
  paragraphs and the MAX_TAGS/MAX_TAG_LEN constants may change.
- DO NOT modify any application code. If a test you write fails, the test is wrong.
- DO NOT re-add a pytest.mark.skip anywhere.
- Use TestClient only. Do not use AsyncClient.
- Do not mock storage. Use the real in-memory storage via the existing conftest fixtures.
- Do not write, re-declare, or output conftest.py, and do not add fixtures these files
  already get from it.
- Do not assert on 422 message strings — assert status_code and the `loc` path only. Wording
  is Pydantic's and will change under you.
- Compute all dates relative to date.today() via the existing _iso helper.
- Use the exact route paths from app/routers/tasks.py (the router prefix is /tasks).
- Do not add tests outside DD-1..DD-5 and TG-1..TG-5, and do not retest base CRUD.
- Do not add print or logging statements.

Output only two code blocks, each preceded by:

# FILE: task-tracker/backend/tests/test_due_dates.py

# FILE: task-tracker/backend/tests/test_tags.py
```

### What AI delivered

- `tests/test_due_dates.py` — the five requested tests, with all dates computed via the
  existing `_iso()` helper. Past-due fixtures are seeded straight into `storage._tasks`
  through `model_copy`, since the API refuses to create a backdated task.
- `tests/test_tags.py` — the four requested tests, and `MAX_TAGS` / `MAX_TAG_LEN` now
  imported from `app.models` instead of redefined locally, so the limits cannot drift.
- The client-side scope boundary held: the new tests assert that `?overdue=` and `?tag=`
  are **ignored**, pinning the absence of a server-side filter rather than inventing
  query params to satisfy a test.
- No application code and no existing test was modified.
- **Current state: 59 tests pass** — `test_due_dates.py` 17, `test_tags.py` 20,
  `test_tasks.py` 18, plus 4 elsewhere.

---

## 8 — Frontend — modal and cards

**Goal:** surface both features in the create/edit modal and on the task cards.

### Prompt

```text
Extend the existing create/edit task modal in @task-tracker/frontend/
@task-tracker/frontend/index.html  +
@task-tracker/frontend/app.js  + @task-tracker/frontend/style.css  with due date and tags. Here is also the adr for your reference @docs/midcourse/mini-adr.md

Requirements:

- Add two fields to the modal, after Assignee: a due date (`due_date`, native ) and tags (`tags`, chip input). Give each a .field-error slot matching the existing pattern.
- Tags input: typing a tag and pressing Enter or comma adds a chip; each chip has a remove (x) button. The chips, not the raw text input, are the source of truth for the submitted array.
- Create mode: empty date, no chips. Submit with POST http://localhost:8000/tasks including `due_date` and `tags`.
- Edit mode: pre-fill the date input from the task's `due_date` and render one chip per existing tag. Submit with PATCH http://localhost:8000/tasks/{id}.
- Empty due date is sent as null on both create and edit — clearing the field is how a deadline gets removed (DD-2).
- No tags is sent as [], never null. The backend rejects a null `tags`.
- Client validation: keep title-required exactly as-is. Additionally, drop blank or whitespace-only tag entries silently instead of adding a chip (TG-5), and de-duplicate chips case-insensitively keeping the first casing entered (TG-4). Do not client-validate the date value itself — the server owns DD-5.
- On 200/201: unchanged — close the modal, clear errors and chips, call fetchTasks().
- On 422: keep the modal open and route the server message to the right field slot by reading the error's `loc` path, so `due_date` errors land on the date input and `tags` errors on the tags field. The backend already emits loc: ("body", "due_date") for a backdated date and for a malformed one.
- Cancel, close button, Escape, and overlay click all close the modal, clear errors, and reset the tag chips.

Card rendering:

- Render `due_date` on each card, and each tag as a chip.
- Flag a card Overdue when status !== "Done" and `due_date` is earlier than today. Due today is not overdue; a task with no due date is never overdue; a Done task is never flagged (DD-3).
- Derive each tag chip's color deterministically from the casefolded tag text so the same tag looks identical on every card (TG-4). No stored color.

Constraints:

- Reuse existing visual styles as much as possible.
- Do not introduce a framework or new dependency.
- Do not break drag-and-drop, priority sorting, the four UI states, or the existing modal fields (title, description, status, priority, assignee, hidden taskId).
- Out of scope for this prompt: the overdue filter (DD-4) and tag filter (TG-3).
- Return a focused diff.
```

### What AI delivered

- `index.html` — due-date input and tag chip input added after Assignee, each with a
  `.field-error` slot matching the existing pattern.
- `app.js` — chip input (Enter or comma to add, × to remove) with the chips as the
  source of truth for the submitted array. Blank entries are dropped silently (TG-5)
  and chips de-duplicate case-insensitively, keeping the first casing (TG-4).
- An empty date submits as `null` and no tags submits as `[]`. A 422 is routed to the
  right field slot by reading the error's `loc` path.
- Card rendering — `isOverdue()` derives the flag as
  `status !== "Done" && due_date < todayISO()`, never stored; `tagHue()` derives each
  chip's color from the casefolded tag text, so a tag looks identical on every card.
- `style.css` — chip, overdue, and due-date styles built on the existing visual
  language. No framework or new dependency was added.
- Drag-and-drop, priority sorting, the four UI states, and the existing modal fields
  were left working.

---

## 9 — Frontend — filter bar

**Goal:** add the two client-side filters (DD-4, TG-3) the previous prompt scoped out.

### Prompt

```text
Add a board filter bar to @task-tracker/frontend/ — @task-tracker/frontend/index.html +
@task-tracker/frontend/app.js + @task-tracker/frontend/style.css — covering the overdue
filter (DD-4) and the tag filter (TG-3). Here is also the adr for your reference
@docs/midcourse/mini-adr.md

Requirements:

- Add a filter bar between the page header and the board: an "Overdue only" toggle
  (checkbox) and a tag filter. Both are client-side over the already-fetched `tasks`
  array — no new query params on GET /tasks, no new request of any kind.
- Tag filter: a <select></select> whose options are the distinct tags present across the current
  tasks, plus an "All tags" default. Build the option list case-insensitively so `Bug`
  and `bug` are one entry, keeping the first casing seen (TG-4, matching the existing
  chip/dedupe rule). Sort options alphabetically, casefolded.
- Rebuild the tag options after every fetchTasks(). If the selected tag no longer exists
  on any task, fall back to "All tags" rather than leaving a dead selection.
- Overdue filter: reuse the existing isOverdue() helper — do not re-derive the rule.
  Done is never overdue, no due date is never overdue, due today is not overdue (DD-3).
- The two filters combine with AND: with both active, only tasks that are overdue *and*
  carry the selected tag are shown (TG-3).
- Tag matching is case-insensitive (TG-4).
- Filtering happens between the data and the render, not by hiding cards in the DOM:
  renderBoard() must receive only the matching tasks, so grouping, priority sort, and
  the [data-count] pills all recount over the filtered set for free (DD-4, TG-3).
- A column with zero matches still renders its "No tasks" placeholder — B4 must keep
  passing under every filter combination (DD-4, TG-3).
- Clearing both filters restores the full board.

Filter state and drag-and-drop:

- Hold filter state in module-level variables next to `tasks`, and route every render
  through a single applyFilters()/render entry point so optimistic drag updates,
  reverts, and post-save refreshes all respect the active filters.
- A card dragged to a status that filters it out simply disappears on re-render; a
  revert re-renders through the same path. Do not special-case this — just don't render
  from the unfiltered array anywhere.
- moveTask()'s optimistic update, revert, and toast behavior are unchanged.
- Filtering must not touch the four board states: "ready" still covers an empty board,
  so a filter matching nothing is a ready board with three placeholders, never the
  loading or error panel.

Client-side only:

- No client validation to add here, and no server round-trip on filter change — a
  filter change is a pure re-render of data already in memory (per the ADR: DD-4 and
  TG-3 are client-side over the fetched list).

Constraints:

- Reuse existing visual styles as much as possible — the filter bar should read as part
  of the existing header/board surface, and the tag <select></select> should match .field select.
- Do not introduce a framework or new dependency.
- Do not break drag-and-drop, priority sorting, the four UI states, the create/edit
  modal (including due_date and the tag chip input), overdue card flagging, or
  deterministic tag chip colors.
- Do not change the API surface: no endpoint, payload, or query param changes.
- Out of scope for this prompt: persisting filter state across reloads, filtering by
  multiple tags at once, and any server-side filtering.
- Return a focused diff.
```

### What AI delivered

- `index.html` — a `.filter-bar` between the header and the board, holding the
  "Overdue only" checkbox (`#filter-overdue`) and the tag `<select>` (`#filter-tag`).
- `app.js` — `overdueOnly` and `tagFilter` as module-level state next to `tasks`, with
  a single `applyFilters()` entry point feeding `renderBoard()`. Filtering happens
  between the data and the render, so grouping, priority sort, and the `[data-count]`
  pills recount over the filtered set on their own.
- `rebuildTagOptions()` runs after every `fetchTasks()`, builds distinct options
  case-insensitively (first casing wins, sorted casefolded), and falls back to
  "All tags" when the selected tag no longer exists on any task.
- The overdue toggle reuses the existing `isOverdue()` helper rather than re-deriving
  DD-3, and the two filters combine with AND.
- No API change, no new request on filter change, and no new dependency. Drag-and-drop,
  the modal, overdue flagging, and tag chip colors were left intact.
