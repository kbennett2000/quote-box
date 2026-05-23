// Notes section on the quote detail page.
//
// The server renders existing notes for progressive enhancement. This module
// hydrates relative timestamps, wires the add form, and handles inline
// edit + delete. After every successful mutation it refetches the notes list
// from the API and re-renders. The DOM produced by `renderNote()` here MUST
// stay aligned with quote_detail.html so dynamic re-renders look identical
// to the server render.

import { qs, qsa, el, formatRelativeTime } from './util.js';

const section = qs('.notes-section');
const QUOTE_ID = section.dataset.quoteId;
const PROFILE_ID = parseInt(section.dataset.currentProfileId, 10);

function renderNote(note) {
  const meta = el(
    'div',
    { class: 'note-meta' },
    el('span', { class: 'note-author' }, note.profile_name),
    el(
      'time',
      {
        class: 'note-time',
        datetime: note.created_at.endsWith('Z')
          ? note.created_at
          : note.created_at.replace(' ', 'T') + 'Z',
        title: note.created_at + ' UTC',
      },
      formatRelativeTime(note.created_at),
    ),
  );
  const body = el('div', { class: 'note-body' }, note.body);
  const children = [meta, body];
  if (note.profile_id === PROFILE_ID) {
    children.push(
      el(
        'div',
        { class: 'note-actions' },
        el('button', { type: 'button', class: 'note-edit' }, 'Edit'),
        el('button', { type: 'button', class: 'note-delete' }, 'Delete'),
      ),
    );
  }
  const li = el(
    'li',
    {
      class: 'note' + (note.profile_id === PROFILE_ID ? ' note--mine' : ''),
      dataset: { noteId: String(note.id), profileId: String(note.profile_id) },
    },
    ...children,
  );
  return li;
}

function hydrateTimes(root = document) {
  for (const t of qsa('.note-time', root)) {
    const raw = t.getAttribute('datetime') || t.textContent;
    t.textContent = formatRelativeTime(raw);
  }
}

async function fetchNotes() {
  const resp = await fetch(`/api/quotes/${encodeURIComponent(QUOTE_ID)}/notes`);
  if (!resp.ok) throw new Error('Failed to load notes');
  return (await resp.json()).notes;
}

async function refreshNotes() {
  const list = qs('#notes-list');
  const empty = qs('#notes-empty');
  const notes = await fetchNotes();
  list.replaceChildren(...notes.map(renderNote));
  if (empty) empty.hidden = notes.length > 0;
}

function attachNoteHandlers() {
  // Delegated handler on the list — survives re-renders.
  qs('#notes-list').addEventListener('click', onNoteClick);
}

async function onNoteClick(event) {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const li = target.closest('.note');
  if (!li) return;
  const noteId = parseInt(li.dataset.noteId, 10);

  if (target.classList.contains('note-edit')) {
    startEdit(li);
  } else if (target.classList.contains('note-delete')) {
    if (!window.confirm('Delete this note?')) return;
    const resp = await fetch(
      `/api/notes/${noteId}?profile_id=${PROFILE_ID}`,
      { method: 'DELETE' },
    );
    if (!resp.ok) {
      window.alert('Delete failed.');
      return;
    }
    await refreshNotes();
  } else if (target.classList.contains('note-save')) {
    const textarea = qs('textarea', li);
    const body = textarea.value.trim();
    if (!body) return;
    const resp = await fetch(`/api/notes/${noteId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ profile_id: PROFILE_ID, body }),
    });
    if (!resp.ok) {
      window.alert('Save failed.');
      return;
    }
    await refreshNotes();
  } else if (target.classList.contains('note-cancel')) {
    cancelEdit(li);
  }
}

function startEdit(li) {
  const bodyDiv = qs('.note-body', li);
  const original = bodyDiv.textContent;
  li.dataset.originalBody = original;

  const textarea = el('textarea', {
    class: 'note-editor',
    rows: 4,
    maxlength: 10000,
  });
  textarea.value = original;

  const actions = qs('.note-actions', li);
  bodyDiv.replaceWith(textarea);
  actions.replaceWith(
    el(
      'div',
      { class: 'note-actions' },
      el('button', { type: 'button', class: 'note-save' }, 'Save'),
      el('button', { type: 'button', class: 'note-cancel' }, 'Cancel'),
    ),
  );
  textarea.focus();
}

function cancelEdit(li) {
  const original = li.dataset.originalBody || '';
  const textarea = qs('textarea', li);
  textarea.replaceWith(el('div', { class: 'note-body' }, original));
  qs('.note-actions', li).replaceWith(
    el(
      'div',
      { class: 'note-actions' },
      el('button', { type: 'button', class: 'note-edit' }, 'Edit'),
      el('button', { type: 'button', class: 'note-delete' }, 'Delete'),
    ),
  );
}

function wireAddForm() {
  const form = qs('#add-note-form');
  const textarea = qs('textarea', form);
  const submit = qs('button[type=submit]', form);

  const updateDisabled = () => {
    submit.disabled = textarea.value.trim().length === 0;
  };
  textarea.addEventListener('input', updateDisabled);
  updateDisabled();

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    const body = textarea.value.trim();
    if (!body) return;
    submit.disabled = true;
    try {
      const resp = await fetch(
        `/api/quotes/${encodeURIComponent(QUOTE_ID)}/notes`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ profile_id: PROFILE_ID, body }),
        },
      );
      if (!resp.ok) {
        window.alert('Failed to add note.');
        return;
      }
      textarea.value = '';
      await refreshNotes();
    } finally {
      updateDisabled();
    }
  });
}

hydrateTimes();
attachNoteHandlers();
wireAddForm();
