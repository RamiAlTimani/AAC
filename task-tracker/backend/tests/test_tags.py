"""
Tests for Feature 2 — Tags / Labels (TG-1 … TG-5).

The feature is implemented: models.py carries the tags field and the
_normalize_tags helper behind it. These tests run against that
implementation, one story at a time.

TG-3 (tag filter) and TG-4's chip colouring are client-side per the ADR;
what TG-4 asks of the backend is the case-insensitive dedupe covered here.

See docs/mini-adr.md ("Feature 2") and docs/user-stories.md.
"""
# Imported rather than mirrored: a local copy would drift the day the limits
# change, and these tests would keep passing while asserting the wrong number.
from app.models import MAX_TAGS, MAX_TAG_LEN


# ---------------------------------------------------------------------------
# TG-1 — attaching tags to a task
# ---------------------------------------------------------------------------
def test_create_task_accepts_tags(client):
    response = client.post(
        "/tasks",
        json={"title": "tagged", "tags": ["bug", "urgent"]},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["bug", "urgent"]


def test_tags_default_to_an_empty_list_when_omitted(client):
    response = client.post("/tasks", json={"title": "untagged"})
    assert response.status_code == 201
    assert response.json()["tags"] == []


def test_surrounding_whitespace_is_stripped_from_each_tag(client):
    response = client.post(
        "/tasks",
        json={"title": "padded", "tags": ["  bug  ", "\turgent\n"]},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["bug", "urgent"]


def test_a_tag_at_the_length_limit_is_accepted(client):
    tag = "x" * MAX_TAG_LEN
    response = client.post("/tasks", json={"title": "edge", "tags": [tag]})
    assert response.status_code == 201
    assert response.json()["tags"] == [tag]


def test_the_maximum_number_of_tags_is_accepted(client):
    tags = [f"tag{i}" for i in range(MAX_TAGS)]
    response = client.post("/tasks", json={"title": "full", "tags": tags})
    assert response.status_code == 201
    assert response.json()["tags"] == tags


# ---------------------------------------------------------------------------
# TG-4 — case-insensitive uniqueness, first casing wins
# ---------------------------------------------------------------------------
def test_tags_are_deduped_case_insensitively_keeping_the_first_casing(client):
    response = client.post(
        "/tasks",
        json={"title": "dupes", "tags": ["Bug", "bug", "BUG"]},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["Bug"]


def test_dedupe_preserves_the_order_of_the_surviving_tags(client):
    response = client.post(
        "/tasks",
        json={"title": "ordered", "tags": ["Urgent", "bug", "URGENT", "Docs"]},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["Urgent", "bug", "Docs"]


# ---------------------------------------------------------------------------
# TG-2 — removing tags
# ---------------------------------------------------------------------------
def test_patch_with_an_empty_list_removes_every_tag(client):
    created = client.post(
        "/tasks",
        json={"title": "strip me", "tags": ["bug", "urgent"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": []})
    assert response.status_code == 200
    assert response.json()["tags"] == []


def test_patch_replaces_the_tag_list_rather_than_appending(client):
    created = client.post(
        "/tasks",
        json={"title": "replace me", "tags": ["bug"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": ["docs"]})
    assert response.status_code == 200
    assert response.json()["tags"] == ["docs"]


def test_patch_without_the_tags_key_leaves_them_untouched(client):
    created = client.post(
        "/tasks",
        json={"title": "keep my tags", "tags": ["bug"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"title": "renamed"})
    assert response.status_code == 200
    assert response.json()["tags"] == ["bug"]


def test_patch_with_explicit_null_tags_returns_422(client):
    """An explicit null is not a way to clear tags — TG-2 clears them with [].

    The guard matters because storage.update_task applies changes via model_copy,
    which does not re-validate. A None reaching it would be written straight onto
    the stored task, leaving tags at null where every reader expects a list. The
    field validator is the only thing standing between the wire and that state.
    """
    created = client.post(
        "/tasks",
        json={"title": "null my tags", "tags": ["bug"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"tags": None})
    assert response.status_code == 422

    locs = [tuple(err["loc"])[:2] for err in response.json()["detail"]]
    assert ("body", "tags") in locs


def test_a_status_transition_preserves_tags(client):
    """Covers the router's validate-then-update branch, not the plain-update one.

    A status change routes through validate_status_transition before
    storage.update_task; a title-only PATCH (covered above) does not. Tags must
    survive either way.
    """
    created = client.post(
        "/tasks",
        json={"title": "moving along", "tags": ["bug", "urgent"]},
    ).json()

    response = client.patch(f"/tasks/{created['id']}", json={"status": "InProgress"})
    assert response.status_code == 200
    assert response.json()["status"] == "InProgress"
    assert response.json()["tags"] == ["bug", "urgent"]


# ---------------------------------------------------------------------------
# TG-3 — the tag filter is client-side; the backend has no such surface
# ---------------------------------------------------------------------------
def test_list_tasks_ignores_a_tag_query_param_and_returns_every_task(client):
    """GET /tasks takes status and priority only — nothing else.

    FastAPI drops query params the endpoint does not declare, so a tag=bug that a
    future client might send changes nothing. Pinning it stops a server-side
    filter being added behind the ADR's back.
    """
    client.post("/tasks", json={"title": "bugged", "tags": ["bug"]})
    client.post("/tasks", json={"title": "documented", "tags": ["docs"]})
    client.post("/tasks", json={"title": "untagged"})

    response = client.get("/tasks", params={"tag": "bug"})
    assert response.status_code == 200
    assert len(response.json()) == 3


def test_list_tasks_returns_tags_on_every_task_so_the_client_can_filter(client):
    client.post("/tasks", json={"title": "tagged", "tags": ["bug"]})
    client.post("/tasks", json={"title": "untagged"})

    response = client.get("/tasks")
    assert response.status_code == 200

    body = response.json()
    assert all(isinstance(task["tags"], list) for task in body)
    assert sorted(tuple(task["tags"]) for task in body) == [(), ("bug",)]


# ---------------------------------------------------------------------------
# TG-5 — blank tags are dropped silently; limits are 422s
# ---------------------------------------------------------------------------
def test_blank_and_whitespace_only_tags_are_dropped_without_an_error(client):
    response = client.post(
        "/tasks",
        json={"title": "blanks", "tags": ["bug", "", "   ", "\t"]},
    )
    assert response.status_code == 201
    assert response.json()["tags"] == ["bug"]


def test_a_list_of_only_blank_tags_saves_as_an_empty_list(client):
    response = client.post("/tasks", json={"title": "all blank", "tags": ["", "  "]})
    assert response.status_code == 201
    assert response.json()["tags"] == []


def test_a_tag_over_the_length_limit_returns_422_on_the_tags_field(client):
    response = client.post(
        "/tasks",
        json={"title": "too long", "tags": ["x" * (MAX_TAG_LEN + 1)]},
    )
    assert response.status_code == 422

    # Contract B8 routes the error to the field slot, so loc must name tags.
    locs = [tuple(err["loc"])[:2] for err in response.json()["detail"]]
    assert ("body", "tags") in locs


def test_too_many_tags_returns_422_on_the_tags_field(client):
    response = client.post(
        "/tasks",
        json={"title": "too many", "tags": [f"tag{i}" for i in range(MAX_TAGS + 1)]},
    )
    assert response.status_code == 422

    locs = [tuple(err["loc"])[:2] for err in response.json()["detail"]]
    assert ("body", "tags") in locs


def test_the_tag_count_limit_is_applied_after_dedupe(client):
    """Eleven raw tags, ten distinct after casefolding, so this must pass.

    Order matters in _normalize_tags: dedupe (step 4) runs before the count
    check (step 5). Rejecting this would be a bug.
    """
    tags = [f"tag{i}" for i in range(MAX_TAGS)] + ["TAG0"]
    response = client.post("/tasks", json={"title": "dupes then count", "tags": tags})
    assert response.status_code == 201
    assert len(response.json()["tags"]) == MAX_TAGS


def test_a_non_string_tag_is_rejected(client):
    response = client.post("/tasks", json={"title": "wrong type", "tags": [123]})
    assert response.status_code == 422
