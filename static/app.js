const noteForm = document.querySelector("#noteForm");
const titleInput = document.querySelector("#title");
const contentInput = document.querySelector("#content");
const notesList = document.querySelector("#notesList");
const formMessage = document.querySelector("#formMessage");
const saveButton = document.querySelector("#saveButton");
const cancelEdit = document.querySelector("#cancelEdit");
const searchInput = document.querySelector("#searchInput");
const csrfToken = document.querySelector('meta[name="csrf-token"]').content;
let editingId = null;
let searchTimer = null;

document.querySelector("#todayDate").textContent = new Intl.DateTimeFormat("en-IN", {
  weekday: "short", day: "numeric", month: "short", year: "numeric"
}).format(new Date());

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}
function formatDate(value) {
  return new Intl.DateTimeFormat("en-IN", { day: "numeric", month: "short", year: "numeric" }).format(new Date(value));
}
function showToast(message) {
  const toast = document.querySelector("#toast");
  toast.textContent = message; toast.classList.add("show");
  window.setTimeout(() => toast.classList.remove("show"), 2500);
}
async function apiRequest(url, options = {}) {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrfToken, ...(options.headers || {}) }
  });
  const data = await response.json().catch(() => ({}));
  if (response.status === 401) { window.location.href = "/login"; throw new Error("Please sign in again."); }
  if (!response.ok) throw new Error(data.error || "Something went wrong. Please try again.");
  return data;
}
async function loadNotes(query = "") {
  notesList.innerHTML = '<div class="loading-state">Loading your notes...</div>';
  try { renderNotes(await apiRequest(`/api/notes?q=${encodeURIComponent(query)}`)); }
  catch (error) { notesList.innerHTML = `<div class="empty-state"><strong>Could not load notes</strong><p>${escapeHTML(error.message)}</p></div>`; }
}
function renderNotes(notes) {
  document.querySelector("#noteCount").textContent = notes.length;
  document.querySelector("#visibleCount").textContent = notes.length;
  if (!notes.length) {
    notesList.innerHTML = '<div class="empty-state"><div class="empty-icon">✧</div><strong>No notes yet</strong><p>Create your first note using the editor.</p></div>'; return;
  }
  notesList.innerHTML = notes.map(note => `
    <article class="note-card ${note.pinned ? "pinned" : ""}">
      <div class="note-card-top"><h3>${escapeHTML(note.title)}</h3>${note.pinned ? '<span class="pin-badge">★ Pinned</span>' : ""}</div>
      <p class="note-content">${escapeHTML(note.content)}</p>
      <div class="note-meta"><span>${formatDate(note.updated_at)}</span><div class="note-actions">
        <button data-action="pin" data-id="${note.id}">${note.pinned ? "Unpin" : "Pin"}</button>
        <button data-action="edit" data-id="${note.id}">Edit</button>
        <button data-action="delete" data-id="${note.id}">Delete</button>
      </div></div>
    </article>`).join("");
}
function resetForm() {
  editingId = null; noteForm.reset();
  document.querySelector("#formHeading").textContent = "Create a note";
  saveButton.innerHTML = "<span>＋</span> Save note";
  cancelEdit.classList.add("hidden");
  document.querySelector("#charCount").textContent = "0 characters";
  formMessage.textContent = "";
}
contentInput.addEventListener("input", () => {
  const count = contentInput.value.length;
  document.querySelector("#charCount").textContent = `${count} character${count === 1 ? "" : "s"}`;
});
noteForm.addEventListener("submit", async event => {
  event.preventDefault(); formMessage.textContent = "";
  saveButton.disabled = true; saveButton.textContent = editingId ? "Updating..." : "Saving...";
  try {
    await apiRequest(editingId ? `/api/notes/${editingId}` : "/api/notes", {
      method: editingId ? "PUT" : "POST",
      body: JSON.stringify({ title: titleInput.value, content: contentInput.value })
    });
    const wasEditing = editingId !== null;
    resetForm(); await loadNotes(searchInput.value.trim());
    showToast(wasEditing ? "Note updated" : "Note saved");
  } catch (error) { formMessage.textContent = error.message; }
  finally { saveButton.disabled = false; if (!editingId) saveButton.innerHTML = "<span>＋</span> Save note"; }
});
cancelEdit.addEventListener("click", resetForm);
notesList.addEventListener("click", async event => {
  const button = event.target.closest("button[data-action]"); if (!button) return;
  const id = Number(button.dataset.id), action = button.dataset.action;
  try {
    if (action === "delete") {
      if (!window.confirm("Delete this note permanently?")) return;
      await apiRequest(`/api/notes/${id}`, { method: "DELETE" });
      if (editingId === id) resetForm();
      showToast("Note deleted");
    } else if (action === "pin") {
      await apiRequest(`/api/notes/${id}/pin`, { method: "PATCH" }); showToast("Pin status updated");
    } else if (action === "edit") {
      const note = (await apiRequest("/api/notes")).find(item => item.id === id);
      if (!note) return;
      editingId = id; titleInput.value = note.title; contentInput.value = note.content;
      document.querySelector("#charCount").textContent = `${note.content.length} characters`;
      document.querySelector("#formHeading").textContent = "Edit your note";
      saveButton.textContent = "Update note"; cancelEdit.classList.remove("hidden");
      titleInput.focus(); window.scrollTo({ top: 0, behavior: "smooth" });
    }
    await loadNotes(searchInput.value.trim());
  } catch (error) { showToast(error.message); }
});
searchInput.addEventListener("input", () => {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => loadNotes(searchInput.value.trim()), 250);
});
document.addEventListener("keydown", event => {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") noteForm.requestSubmit();
});
loadNotes();
