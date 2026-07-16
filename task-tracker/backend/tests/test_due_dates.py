"""
Tests for Feature 1 — Due Dates & Overdue Filter (DD-1 … DD-5).

The feature is implemented: models.py carries the due_date field and
business_rules.validate_due_date_change holds the update-path date rule.
These tests run against that implementation, one story at a time.

DD-3 (overdue) and DD-4 (overdue filter) are derived and filtered client-side
per the ADR, so they have no backend assertions beyond the response-shape
test here.

See docs/mini-adr.md ("Feature 1") and docs/user-stories.md.
"""
from datetime import date, timedelta

import pytest

from app import storage


def _iso(days_from_today: int) -> str:
    """An ISO date-only string offset from today, for readable test data."""
    return (date.today() + timedelta(days=days_from_today)).isoformat()


# ---------------------------------------------------------------------------
# DD-1 — a task can carry a date-only due date
# ---------------------------------------------------------------------------
def test_create_task_accepts_a_future_due_date(client):
    response = client.post(
        "/tasks",
        json={"title": "ship the thing", "due_date": _iso(7)},
    )
    assert response.status_code == 201
    assert response.json()["due_date"] == _iso(7)


def test_create_task_accepts_today_as_due_date(client):
    response = client.post(
        "/tasks",
        json={"title": "due today", "due_date": _iso(0)},
    )
    assert response.status_code == 201
    assert response.json()["due_date"] == _iso(0)


def test_due_date_defaults_to_null_when_omitted(client):
    response = client.post("/tasks", json={"title": "no due date"})
    assert response.status_code == 201
    assert response.json()["due_date"] is None


def test_due_date_is_date_only_and_rejects_a_timestamp(client):
    response = client.post(
        "/tasks",
        json={"title": "no time of day", "due_date": "2099-01-01T13:30:00"},
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# DD-2 — editing and clearing a due date
# ---------------------------------------------------------------------------
def test_patch_changes_the_due_date(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"due_date": _iso(3)},
    )
    assert response.status_code == 200
    assert response.json()["due_date"] == _iso(3)


def test_patch_with_explicit_null_clears_the_due_date(client):
    created = client.post(
        "/tasks",
        json={"title": "clear me", "due_date": _iso(5)},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": None})
    assert response.status_code == 200
    assert response.json()["due_date"] is None


def test_patch_without_the_due_date_key_leaves_it_untouched(client):
    """Pins the exclude_unset behaviour DD-2 depends on.

    storage.update_task uses model_dump(exclude_unset=True), which is what
    makes an explicit null ("clear it") distinguishable from an absent key
    ("leave it alone"). This test exists to stop that being refactored away.
    """
    created = client.post(
        "/tasks",
        json={"title": "keep my date", "due_date": _iso(5)},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": "renamed"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "renamed"
    assert body["due_date"] == _iso(5)


# ---------------------------------------------------------------------------
# DD-3 — overdue is derived at render time, never stored
# ---------------------------------------------------------------------------
def test_overdue_is_not_a_response_field(client, created_task):
    assert "overdue" not in created_task


def test_a_past_due_task_still_returns_its_due_date_and_status_for_the_client_to_derive_from(
    client,
):
    """Overdue is the client's to derive, so the server must hand over the inputs.

    A stale due date is neither hidden nor rewritten on read: the frontend
    computes (status != "Done" and due_date < today) from exactly these two
    fields, so both must survive the round trip untouched.
    """
    created = client.post("/tasks", json={"title": "went stale"}).json()
    stale = date.today() - timedelta(days=3)
    storage._tasks[created["id"]] = storage._tasks[created["id"]].model_copy(
        update={"due_date": stale}
    )

    response = client.get(f"/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["due_date"] == stale.isoformat()
    assert response.json()["status"] == "ToDo"


# ---------------------------------------------------------------------------
# DD-4 — the overdue filter is client-side; the backend has no such surface
# ---------------------------------------------------------------------------
def test_list_tasks_ignores_an_overdue_query_param_and_returns_every_task(client):
    """GET /tasks takes status and priority only — nothing else.

    FastAPI drops query params the endpoint does not declare, so an overdue=true
    that a future client might send changes nothing. That is the point: pinning
    it here stops a server-side filter being added behind the ADR's back.
    """
    client.post("/tasks", json={"title": "due soon", "due_date": _iso(1)})
    client.post("/tasks", json={"title": "due later", "due_date": _iso(30)})
    client.post("/tasks", json={"title": "no due date"})

    response = client.get("/tasks", params={"overdue": "true"})
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_list_tasks_returns_due_date_on_every_task_so_the_client_can_filter(client):
    client.post("/tasks", json={"title": "dated", "due_date": _iso(2)})
    client.post("/tasks", json={"title": "undated"})

    response = client.get("/tasks")
    assert response.status_code == 200

    body = response.json()
    assert all("due_date" in task for task in body)
    assert {task["due_date"] for task in body} == {_iso(2), None}


# ---------------------------------------------------------------------------
# DD-5 — malformed and backdated input
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_value", ["2026-13-40", "soon", "", "01/01/2099", 12345])
def test_create_rejects_malformed_due_date_on_the_due_date_field(client, bad_value):
    response = client.post(
        "/tasks",
        json={"title": "bad date", "due_date": bad_value},
    )
    assert response.status_code == 422

    # Contract B8 routes the error to the field slot, so loc must name due_date.
    locs = [tuple(err["loc"]) for err in response.json()["detail"]]
    assert ("body", "due_date") in locs


def test_create_rejects_a_past_due_date(client):
    response = client.post(
        "/tasks",
        json={"title": "backdated", "due_date": _iso(-1)},
    )
    assert response.status_code == 422

    locs = [tuple(err["loc"]) for err in response.json()["detail"]]
    assert ("body", "due_date") in locs


def test_patch_rejects_moving_a_due_date_into_the_past(client, created_task):
    response = client.patch(
        f"/tasks/{created_task['id']}",
        json={"due_date": _iso(-1)},
    )
    assert response.status_code == 422

    locs = [tuple(err["loc"]) for err in response.json()["detail"]]
    assert ("body", "due_date") in locs


def test_patch_allows_resending_an_unchanged_due_date_that_is_now_past(client):
    """The DD-5-vs-DD-2 wrinkle from the ADR.

    A task whose due date has since passed must stay editable. The modal
    resends the unchanged due_date, so the past-date rule must fire only when
    the date is actually being changed — which is why it lives in
    business_rules.py (it needs the existing task) rather than in a field
    validator on TaskUpdate.

    Seeded through the storage layer directly, because the API refuses to
    create a past-dated task in the first place.
    """
    created = client.post("/tasks", json={"title": "went stale"}).json()
    stale = date.today() - timedelta(days=2)
    storage._tasks[created["id"]] = storage._tasks[created["id"]].model_copy(
        update={"due_date": stale}
    )

    response = client.patch(
        f"/tasks/{created['id']}",
        json={"title": "still editable", "due_date": stale.isoformat()},
    )
    assert response.status_code == 200
    assert response.json()["title"] == "still editable"
    assert response.json()["due_date"] == stale.isoformat()


def test_patch_with_a_past_due_date_on_a_missing_task_returns_404_not_422(client):
    """404 outranks 422: the router looks the task up before it validates.

    update_task fetches the existing task first, because validate_due_date_change
    needs it to tell a changed date from a resent one. A missing id therefore
    fails the lookup and never reaches the date rule — pinning that ordering here
    stops the two being swapped in routers/tasks.py.
    """
    response = client.patch(
        "/tasks/does-not-exist",
        json={"due_date": _iso(-1)},
    )
    assert response.status_code == 404


def test_patch_can_clear_a_due_date_that_is_already_in_the_past(client):
    """Clearing is unconditional (validate_due_date_change rule 1).

    A None new date returns before the past-date check, so a task whose date has
    gone stale can still have it removed rather than being stuck with it.
    """
    created = client.post("/tasks", json={"title": "stale then cleared"}).json()
    stale = date.today() - timedelta(days=4)
    storage._tasks[created["id"]] = storage._tasks[created["id"]].model_copy(
        update={"due_date": stale}
    )

    response = client.patch(f"/tasks/{created['id']}", json={"due_date": None})
    assert response.status_code == 200
    assert response.json()["due_date"] is None
