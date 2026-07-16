const API_BASE = "http://localhost:8000";

// The single source of truth. Replaced wholesale by each fetch, then rendered.
let tasks = [];

// Statuses the board can display, in column order. Anything else is ignored.
const STATUSES = ["ToDo", "InProgress", "Done"];

// Lower rank sorts first: High before Medium before Low.
const PRIORITY_RANK = { High: 0, Medium: 1, Low: 2 };

const template = document.getElementById("card-template");

const boardEl = document.querySelector(".board");
const statusEl = document.getElementById("board-status");

// Pull tasks from the API into the shared `tasks` array, then render.
async function fetchTasks() {
    const response = await fetch(`${API_BASE}/tasks`);
    if (!response.ok) {
        throw new Error(`Failed to load tasks: ${response.status}`);
    }
    tasks = await response.json();
    renderBoard(tasks);
    return tasks;
}

// Placeholder for a column with no tasks. Sits inside the card-list so
// the column keeps its shape and remains a valid drop target later.
function renderEmptyPlaceholder() {
    const el = document.createElement("p");
    el.className = "card-list-empty";
    el.textContent = "No tasks";
    return el;
}

function buildLoadingPanel() {
    const panel = document.createElement("div");
    panel.className = "status-panel";
    panel.setAttribute("role", "status");
    panel.innerHTML =
        '<span class="spinner" aria-hidden="true"></span><span>Loading tasks…</span>';
    return panel;
}

function buildErrorPanel() {
    const panel = document.createElement("div");
    panel.className = "status-panel is-error";
    panel.setAttribute("role", "alert");

    const message = document.createElement("span");
    message.textContent = "Couldn't load tasks. Check your connection and try again.";

    const retry = document.createElement("button");
    retry.type = "button";
    retry.className = "retry-btn";
    retry.textContent = "Retry";
    retry.addEventListener("click", loadTasks);

    panel.append(message, retry);
    return panel;
}

// Board-level state switch. "ready" (used for both populated and empty
// boards) shows the columns; "loading"/"error" show a status panel.
function setBoardState(state) {
    if (state === "ready") {
        statusEl.hidden = true;
        statusEl.innerHTML = "";
        boardEl.hidden = false;
        return;
    }

    boardEl.hidden = true;
    statusEl.innerHTML = "";
    statusEl.appendChild(
        state === "error" ? buildErrorPanel() : buildLoadingPanel()
    );
    statusEl.hidden = false;
}

// Orchestrates the four UI states around a single fetch.
async function loadTasks() {
    setBoardState("loading");
    try {
        await fetchTasks(); // sets `tasks` and renders columns (incl. empty)
        setBoardState("ready");
    } catch (err) {
        console.error(err);
        setBoardState("error");
    }
}

function renderCard(task) {
    const card = template.content.firstElementChild.cloneNode(true);
    card.dataset.id = task.id;
    card.dataset.priority = task.priority;

    card.querySelector(".card-title").textContent = task.title;

    // Description is optional — drop the element entirely when absent.
    const description = card.querySelector(".card-description");
    if (task.description) {
        description.textContent = task.description;
    } else {
        description.remove();
    }

    const pill = card.querySelector(".priority-pill");
    pill.dataset.priority = task.priority;
    pill.textContent = task.priority;

    const assignee = card.querySelector(".assignee");
    if (task.assignee) {
        assignee.textContent = task.assignee;
    } else {
        assignee.textContent = "Unassigned";
        assignee.classList.add("is-unassigned");
    }

    return card;
}

// Group tasks by status, ordering each column by priority (High → Low),
// breaking ties by id ascending.
function groupByStatus(taskList) {
    const groups = Object.fromEntries(STATUSES.map((status) => [status, []]));

    for (const task of taskList) {
        if (groups[task.status]) groups[task.status].push(task);
    }

    for (const status of STATUSES) {
        groups[status].sort((a, b) => {
            const byPriority = PRIORITY_RANK[a.priority] - PRIORITY_RANK[b.priority];
            return byPriority !== 0 ? byPriority : a.id - b.id;
        });
    }

    return groups;
}

function renderBoard(taskList) {
    const groups = groupByStatus(taskList);

    // Render each column independently — empty columns stay visible.
    document.querySelectorAll(".column").forEach((column) => {
        const status = column.dataset.status;
        const list = column.querySelector(".card-list");
        const columnTasks = groups[status] || [];

        list.innerHTML = "";
        if (columnTasks.length === 0) {
            // Empty columns stay visible and keep their drop area.
            list.appendChild(renderEmptyPlaceholder());
        } else {
            for (const task of columnTasks) {
                list.appendChild(renderCard(task));
            }
        }

        column.querySelector("[data-count]").textContent = columnTasks.length;
    });
}

// ---- Drag & drop -------------------------------------------------

// The card currently being dragged, kept alongside dataTransfer since
// dataTransfer's data is not readable during dragover in every browser.
let draggedId = null;
let toastTimer = null;

function clearDropTargets() {
    document
        .querySelectorAll(".card-list.is-drop-target")
        .forEach((list) => list.classList.remove("is-drop-target"));
}

// Brief, self-dismissing message — used for drag revert notices.
function showToast(message, isError = false) {
    let toast = document.getElementById("toast");
    if (!toast) {
        toast = document.createElement("div");
        toast.id = "toast";
        toast.className = "toast";
        toast.setAttribute("role", "alert");
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.toggle("is-error", isError);
    toast.classList.add("is-visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove("is-visible"), 5000);
}

// Pull a readable message out of a 4xx response. FastAPI validation
// errors arrive as { detail: [{ msg, ... }] }; simpler errors as a
// { detail: "..." } string. Fall back to the status code.
async function extractServerError(response) {
    try {
        const data = await response.json();
        if (typeof data.detail === "string") return data.detail;
        if (Array.isArray(data.detail)) {
            const msg = data.detail
                .map((d) => d && d.msg)
                .filter(Boolean)
                .join("; ");
            if (msg) return msg;
        }
    } catch (_) {
        /* body wasn't JSON — fall through to the generic message */
    }
    return `Couldn't update task (${response.status}).`;
}

// Move a card to a new status: optimistic update first, then PATCH.
// Reverts and re-renders if the server rejects it or is unreachable.
async function moveTask(id, targetStatus) {
    const task = tasks.find((t) => String(t.id) === String(id));
    if (!task) return;

    const previousStatus = task.status;
    // No-op when dropped back on its own column.
    if (previousStatus === targetStatus) return;

    // Optimistic: reflect the move locally before the request resolves.
    task.status = targetStatus;
    renderBoard(tasks);

    try {
        const response = await fetch(`${API_BASE}/tasks/${id}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ status: targetStatus }),
        });

        if (!response.ok) {
            task.status = previousStatus;
            renderBoard(tasks);
            showToast(await extractServerError(response), true);
        }
        // 200: nothing to do — the optimistic state already stands.
    } catch (err) {
        console.error(err);
        task.status = previousStatus;
        renderBoard(tasks);
        showToast("Couldn't reach the server — your change wasn't saved.", true);
    }
}

// Delegated on the board so handlers survive re-renders.
boardEl.addEventListener("dragstart", (event) => {
    const card = event.target.closest(".card");
    if (!card) return;
    draggedId = card.dataset.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.id);
    card.classList.add("is-dragging");
});

boardEl.addEventListener("dragend", (event) => {
    const card = event.target.closest(".card");
    if (card) card.classList.remove("is-dragging");
    clearDropTargets();
    draggedId = null;
});

boardEl.addEventListener("dragover", (event) => {
    const list = event.target.closest(".card-list");
    if (!list) return;
    event.preventDefault(); // required to allow a drop
    event.dataTransfer.dropEffect = "move";
    if (!list.classList.contains("is-drop-target")) {
        clearDropTargets();
        list.classList.add("is-drop-target");
    }
});

boardEl.addEventListener("drop", (event) => {
    const list = event.target.closest(".card-list");
    if (!list) return;
    event.preventDefault();
    clearDropTargets();
    const id = event.dataTransfer.getData("text/plain") || draggedId;
    if (id == null || id === "") return;
    moveTask(id, list.dataset.status);
});

// ---- Create / edit modal ----------------------------------------

const modal = document.getElementById("task-modal");
const form = document.getElementById("task-form");
const modalTitle = document.getElementById("modal-title");
const formBanner = document.getElementById("form-banner");

// Wipe both the form-level banner and every per-field error slot.
function clearModalErrors() {
    formBanner.hidden = true;
    formBanner.textContent = "";
    form.querySelectorAll(".field-error").forEach((slot) => {
        slot.hidden = true;
        slot.textContent = "";
    });
}

// Show a field-level error, falling back to the banner if there's no
// matching slot for the field name.
function showFieldError(field, message) {
    const slot = form.querySelector(`.field-error[data-error-for="${field}"]`);
    if (slot) {
        slot.textContent = message;
        slot.hidden = false;
    } else {
        showBannerError(message);
    }
}

function showBannerError(message) {
    // Append so multiple unmapped errors don't clobber each other.
    formBanner.textContent = formBanner.textContent
        ? `${formBanner.textContent}; ${message}`
        : message;
    formBanner.hidden = false;
}

// Route a 422 body onto field slots. FastAPI sends
// { detail: [{ loc: ["body", "title"], msg }] }; a plain string detail
// (or anything else) goes to the banner.
function showValidationErrors(detail) {
    if (Array.isArray(detail)) {
        for (const item of detail) {
            const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : null;
            showFieldError(field, item.msg || "Invalid value");
        }
        return;
    }
    showBannerError(typeof detail === "string" ? detail : "Couldn't save the task.");
}

// Open in create mode (no task) or edit mode (task from the board data).
function openModal(task) {
    clearModalErrors();
    form.reset();

    // form.elements.<name> avoids the HTMLFormElement named-getter
    // collision with inherited props (e.g. form.title === the attribute).
    const f = form.elements;
    if (task) {
        modalTitle.textContent = "Edit Task";
        f.taskId.value = task.id;
        f.title.value = task.title || "";
        f.description.value = task.description || "";
        f.status.value = task.status || "ToDo";
        f.priority.value = task.priority || "Medium";
        f.assignee.value = task.assignee || "";
    } else {
        modalTitle.textContent = "New Task";
        f.taskId.value = "";
        f.status.value = "ToDo";
        f.priority.value = "Medium";
    }

    modal.hidden = false;
    f.title.focus();
}

function closeModal() {
    modal.hidden = true;
    clearModalErrors();
}

form.addEventListener("submit", async (event) => {
    event.preventDefault();
    clearModalErrors();

    const f = form.elements;
    const title = f.title.value.trim();
    if (!title) {
        showFieldError("title", "Title is required");
        f.title.focus();
        return; // client validation failed — no request
    }

    const assignee = f.assignee.value.trim();
    const payload = {
        title,
        description: f.description.value, // empty stays "" per spec
        status: f.status.value,
        priority: f.priority.value,
        assignee: assignee === "" ? null : assignee,
    };

    const id = f.taskId.value;
    const isEdit = id !== "";
    const url = isEdit ? `${API_BASE}/tasks/${id}` : `${API_BASE}/tasks`;
    const method = isEdit ? "PATCH" : "POST";

    try {
        const response = await fetch(url, {
            method,
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        if (response.ok) {
            closeModal();
            await fetchTasks(); // refresh the board with server truth
            return;
        }

        if (response.status === 422) {
            let detail = null;
            try {
                detail = (await response.json()).detail;
            } catch (_) {
                /* non-JSON body — showValidationErrors falls back to banner */
            }
            showValidationErrors(detail); // keep modal open
            return;
        }

        showBannerError(await extractServerError(response));
    } catch (err) {
        console.error(err);
        showBannerError("Couldn't reach the server — your change wasn't saved.");
    }
});

// Open triggers.
document.getElementById("new-task-btn").addEventListener("click", () => openModal());

// Edit is delegated on the board so it survives re-renders; look the task
// up in the shared `tasks` array by the card's id.
boardEl.addEventListener("click", (event) => {
    const btn = event.target.closest(".edit-btn");
    if (!btn) return;
    const card = btn.closest(".card");
    if (!card) return;
    const task = tasks.find((t) => String(t.id) === String(card.dataset.id));
    if (task) openModal(task);
});

// Close triggers: Cancel, close button, overlay click, Escape.
document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("modal-close").addEventListener("click", closeModal);
modal.addEventListener("click", (event) => {
    if (event.target === modal) closeModal(); // click on overlay, not the dialog
});
document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !modal.hidden) closeModal();
});

// Kick things off: loading → ready (or error, with Retry).
loadTasks();
