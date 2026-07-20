# Mini ADR- Storage architecture for Due Dates & Tags

## Context

The Task Tracker currently stores tasks in a module-level dictionary in
`app/storage.py`. State lives in the Uvicorn process and is cleared between tests
via `storage._reset()`. There is no database, ORM, or file persistence.

Two new feature sets were specified in [user-stories.md](user-stories.md):

- **Feature 1 - Due Dates & Overdue Filter** (DD-1 … DD-5)
- **Feature 2 - Tags / Labels** (TG-1 … TG-5)

Neither feature is inherently blocked by the current storage layer, but tags in
particular raise the question of whether a task's labels should stay as a list of
strings on the task or become a modelled entity. That question is really "should
this project adopt a database?", so it was worth deciding deliberately rather
than by default.

Project constraints that bound the decision:

- Learning project, not production software.
- Python + FastAPI + Pydantic for validation; REST API with a separate simple frontend.
- Tech stack must stay simple, well-documented, and easy to run locally.
- No authentication, no multi-tenancy.
- Explicitly out of scope: microservices, Docker, cloud deployment, production database setup.

The user stories also state the scope directly: *"none of these introduce … a
persistent DB - all features operate on the shared in-memory task list."*

## Decision

**Adopt Option A: keep the in-memory dictionary and extend it.**

Due dates and tags are implemented as new fields on the existing Pydantic models.
`storage.py` keeps its dictionary. No database, no ORM, no new dependency. The
only structural change is lifting the five task endpoints out of `main.py` into
`app/routers/tasks.py`, mirroring the existing `routers/health.py`.

Rationale: the decision is **more aligned with the project's stated requirements**
than the alternative. The constraint list rules out a production database setup and
asks for the simplest thing that runs locally; the user stories were written on the
explicit assumption of an in-memory list. Both features live almost entirely in
Pydantic validation and the frontend, so adding a persistence layer would spend the
project's complexity budget somewhere the features don't actually need it.

### Consequences

**Accepted costs:**

- **No persistence.** Restarting the backend clears the board. This will be mildly
  annoying when manually testing due-date scenarios, and is accepted.
- **Tags are duplicated strings.** The same label is stored on every task carrying
  it. Renaming a tag across the board would be an N-task rewrite with no transaction
  around it. Acceptable at this scale; would be wrong at any other.
- **No tag entity.** Case-insensitive uniqueness (TG-4) is enforced by a Python
  `casefold()` loop rather than a database constraint.

**Retained benefits:**

- No new concepts or dependencies; the diff for both features is field additions
  plus validators.
- Tests stay fast and isolated - `storage._reset()` remains a `dict.clear()`.
- The API wire format is unchanged in shape, so this decision can be revisited
  later without touching `frontend/app.js` or `Contract.md`. See *Revisiting* below.

**If persistence is later wanted without a database**, the smallest honest addition
is dumping `_tasks` to a `tasks.json` file on write and loading it at startup -
roughly ten lines, no new dependency. This is *not* being done now, because it
means owning the "corrupt or partial write" problem for no current benefit.

## Alternative considered - Option B: SQLite + SQLModel

### What it was

A lightweight local database, chosen for realism rather than for scale:

| Layer      | Choice                                                                               |
| ---------- | ------------------------------------------------------------------------------------ |
| ORM        | SQLModel (SQLAlchemy 2.0 + Pydantic, by FastAPI's author)                            |
| Storage    | SQLite via the stdlib`sqlite3` driver - a single `tasks.db` file, no server      |
| Migrations | None -`SQLModel.metadata.create_all()` at startup                                  |
| Tests      | In-memory SQLite (`sqlite://`) per test, via a `get_session` dependency override |

It added one dependency (`sqlmodel`); SQLite itself ships with Python.
`app/storage.py` would be replaced by `app/repositories/tasks.py` (filling the
package that already exists but is empty), `models.py` would split into
`schemas.py` (Pydantic API contract) and `db/models.py` (SQLModel tables), and
`db/session.py` would own the engine and the `get_session` dependency.

The substantive part of Option B was **modelling tags relationally**: a `Tag` table
with a `UNIQUE` constraint on a casefolded `slug`, plus a `TaskTag` link table for
the many-to-many. Tag uniqueness would be enforced by the database, TG-3's tag
filter would become a join, and a future "rename a tag everywhere" would be a
single `UPDATE` in a transaction.

A lighter variant (tags in a SQLite JSON column) was also considered and dismissed
as the worst of both: it is Option A's data model with a file and a dependency
behind it, so it pays Option B's costs without buying its realism.

### Why it was rejected

1. **It contradicts the stated constraints and the user stories.** The constraints
   rule out a production database setup and ask for the simplest local stack; the
   user stories' scope check explicitly assumes no persistent DB. Option B is
   defensible engineering, but it is not what this project asked for.
2. **It spends the learning budget in the wrong place.** Due dates and tags are
   exercises in Pydantic validation and frontend rendering. Option B would mean
   learning session lifecycle, dependency-injected sessions, the schema-vs-table
   distinction, and SQLAlchemy's identity map *at the same time as* the features -
   and none of that is what these two features are about.
3. **Test isolation becomes a real design problem.** `storage._reset()` is a
   `dict.clear()`. Option B needs a per-test in-memory engine plus a dependency
   override - a fixture that is easy to get subtly wrong, producing tests that pass
   individually and fail in a suite. That is a poor trade for a project whose
   existing test setup already works.
4. **Its main benefit is partly self-defeating here.** Persistence is the reason to
   adopt Option B, but with no Alembic, any table change means deleting `tasks.db`
   and losing the data anyway.

### Revisiting this decision

Option B remains open. `TaskResponse` flattens tags to `list[str]` in both designs,
so **both options produce identical JSON**. Migrating later means replacing
`storage.py` with `repositories/tasks.py` behind the same function names
(`add_task`, `get_all_tasks`, `update_task`, …) - the routers barely change and the
frontend does not change at all.

Reconsider if any of these become true:

- Losing the board on restart stops being an annoyance and starts costing real time.
- A feature needs to query across tasks in a way that is awkward in Python (e.g.
  tag renaming, tag usage counts, or server-side filtering at scale).
- The project's goal shifts from "learn these features" to "learn a backend
  persistence layer" - at which point Option B becomes the *point*, not a cost.

## Implementation

### Folder structure

```
task-tracker/
├── Contract.md
├── backend/
│   ├── requirements.txt          # unchanged - no new dependency
│   ├── .env.example
│   ├── app/
│   │   ├── main.py               # app instance, CORS, router registration only
│   │   ├── models.py             # all Pydantic schemas (+ due_date, tags)
│   │   ├── business_rules.py     # status transitions + due-date-vs-today
│   │   ├── storage.py            # in-memory dict (unchanged shape)
│   │   ├── core/
│   │   │   └── config.py
│   │   └── routers/
│   │       ├── health.py
│   │       └── tasks.py          # NEW - the 5 task endpoints, moved from main.py
│   └── tests/
│       ├── conftest.py
│       ├── test_tasks.py
│       ├── test_due_dates.py     # NEW - DD-1 … DD-5
│       └── test_tags.py          # NEW - TG-1 … TG-5
└── frontend/
    ├── index.html
    ├── style.css
    └── app.js
```

Changes from the current tree:

- **Add** `app/routers/tasks.py` and move the five task endpoints there. `main.py`
  keeps only the app instance, CORS middleware, and router registration.
- **Add** `tests/test_due_dates.py` and `tests/test_tags.py`.
- **Delete** the empty `app/repositories/` and `app/services/` packages. Under
  Option A they would stay empty permanently, and an empty package is a promise the
  code never keeps. (`repositories/` returns only if Option B is ever adopted.)

### Feature 1 - Due Dates & Overdue Filter

**Model (`app/models.py`).** A new optional, nullable field on all three schemas:

```python
due_date: Optional[date] = None      # DD-1: date-only, no time-of-day
```

`date` gives DD-5's malformed-input rejection (`2026-13-40`, `"soon"`) for free -
Pydantic returns 422 with `loc = ("body", "due_date")`, which routes to the field
slot per contract B8. Nullable keeps existing tasks unaffected.

**Backdating (DD-5).** A `field_validator` on `TaskCreate.due_date` rejects any date
earlier than `date.today()`; today or later is accepted.

**Overdue (DD-3).** *Not* a stored field and not on `TaskResponse`. Derived at render
time in the frontend: `status != "Done"` and `due_date < today`. A task due today is
not overdue; a task with no due date is never overdue.

**Filtering (DD-4).** Client-side over the already-fetched task list. No new query
parameter; the existing `status`/`priority` params on `GET /tasks` are unchanged.

**Two wrinkles this feature must handle:**

1. **DD-5's backdating rule conflicts with DD-2's edit flow.** A task created on
   2026-07-16 with `due_date: 2026-07-20` would become uneditable on 2026-07-21 if a
   naive `due_date < today` validator ran on `TaskUpdate` and the modal resent the
   unchanged date. The past-date check must therefore apply **only when `due_date` is
   actually being changed**, which requires the existing task - so on the update path
   it is a business rule in `business_rules.py`, not a field validator. Same shape as
   the existing `validate_status_transition`.
2. **That business rule still needs a `loc`.** `validate_status_transition` raises
   `HTTPException(422, detail=...)`, which the frontend can only show in the form
   banner - but DD-5 requires the error on the due-date input. The update-path date
   rule must therefore raise `RequestValidationError` with `loc = ("body", "due_date")`
   (or hand-build a 422 body in Pydantic's shape) instead of `HTTPException`. Build
   this helper once; TG-5 needs the same thing.

**Clearing a due date (DD-2).** `Optional[date] = None` on `TaskUpdate` cannot itself
distinguish "clear the date" from "leave it alone". `storage.update_task` already uses
`model_dump(exclude_unset=True)`, which handles this correctly: an explicit
`"due_date": null` in the body counts as *set*, an absent key does not. **This
behaviour is load-bearing for DD-2 and must be pinned by a test.**

### Feature 2 - Tags / Labels

**Model (`app/models.py`).** Tags are free-text strings on the task - no tag entity:

```python
tags: Annotated[list[str], Field(max_length=MAX_TAGS)] = []
```

with `MAX_TAGS = 10` and `MAX_TAG_LEN = 30`.

**Normalization (TG-1, TG-5).** A `field_validator` on `tags` runs a
`_normalize_tags` helper in a fixed order:

1. Strip each tag.
2. Drop empty/whitespace-only tags **silently** (TG-5: dropped, *not* a 422).
3. Reject any tag over 30 characters → 422 with `loc = ("body", "tags")`.
4. Dedupe case-insensitively via `casefold()`, first casing wins (TG-1, TG-4).
5. Reject more than 10 tags → 422 with `loc = ("body", "tags")`.

A task with no tags saves as `tags: []`. Removing the last tag (TG-2) is just a
`PATCH` with `tags: []` through the existing edit flow.

**Filtering (TG-3).** Client-side, matching case-insensitively, and combinable with
the DD-4 overdue filter (a task must match both). Column `[data-count]` pills recount
over the filtered set; empty columns still render the "No tasks" placeholder,
preserving contract B4.

**Styling (TG-4).** Chip colour is derived deterministically from the casefolded tag
text (e.g. a hash → hue). No colour is stored, so `Bug` and `bug` render as one
category. Chip styling must not affect card sort order - priority sort per B2 is
unchanged.

### Contract impact

`Contract.md` behaviours **B1–B8 are unaffected** and must continue to pass. The two
features add fields to the existing request/response bodies and reuse the existing
modal and 422 → field-slot error routing (B8); no endpoint is added or removed.
