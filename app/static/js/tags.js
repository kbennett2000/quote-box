// Tags-management page interactivity.
//
// Rename is inline: click → input → Enter or blur commits via
// PUT /api/tags/<id>. Escape cancels. Delete prompts a confirm that
// names the cascade consequence, then DELETE removes the row from
// the DOM on a 204.

import { qs, el } from './util.js';

const list = qs('#tags-list');

function inlineError(row, message) {
  let err = qs('.tag-row-error', row);
  if (!err) {
    err = el('p', { class: 'tag-row-error' });
    row.append(err);
  }
  err.textContent = message;
}

function clearInlineError(row) {
  const err = qs('.tag-row-error', row);
  if (err) err.remove();
}

function startRename(row) {
  const nameSpan = qs('.tag-row-name', row);
  if (!nameSpan) return;
  const original = row.dataset.tagName;
  const input = el('input', {
    type: 'text',
    class: 'tag-row-edit',
    value: original,
    maxlength: 50,
  });
  nameSpan.replaceWith(input);
  input.focus();
  input.select();

  let settled = false;

  const cancel = () => {
    if (settled) return;
    settled = true;
    input.replaceWith(el('span', { class: 'tag-row-name' }, original));
    clearInlineError(row);
  };

  const commit = async () => {
    if (settled) return;
    const newName = input.value.trim().toLowerCase();
    if (!newName) {
      cancel();
      return;
    }
    if (newName === original) {
      cancel();
      return;
    }
    settled = true;
    const resp = await fetch(`/api/tags/${row.dataset.tagId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: newName }),
    });
    if (resp.status === 200) {
      const body = await resp.json();
      row.dataset.tagName = body.name;
      input.replaceWith(el('span', { class: 'tag-row-name' }, body.name));
      clearInlineError(row);
    } else if (resp.status === 409) {
      const body = await resp.json().catch(() => ({}));
      input.replaceWith(el('span', { class: 'tag-row-name' }, original));
      inlineError(row, body.error || 'A tag with that name already exists.');
    } else {
      input.replaceWith(el('span', { class: 'tag-row-name' }, original));
      inlineError(row, 'Rename failed. Please try again.');
    }
  };

  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      commit();
    } else if (event.key === 'Escape') {
      event.preventDefault();
      cancel();
    }
  });
  input.addEventListener('blur', commit);
}

async function handleDelete(row) {
  const name = row.dataset.tagName;
  const count = parseInt(row.dataset.tagCount, 10) || 0;
  const usage = count === 1 ? '1 quote' : `${count} quotes`;
  const ok = window.confirm(
    `Delete tag '${name}'? Used by ${usage}. Quote text is unchanged.`,
  );
  if (!ok) return;
  const resp = await fetch(`/api/tags/${row.dataset.tagId}`, { method: 'DELETE' });
  if (resp.status === 204) {
    row.remove();
  } else {
    inlineError(row, 'Delete failed. Please try again.');
  }
}

list.addEventListener('click', (event) => {
  const target = event.target;
  if (!(target instanceof HTMLElement)) return;
  const row = target.closest('.tag-row');
  if (!row) return;
  if (target.classList.contains('tag-rename')) {
    startRename(row);
  } else if (target.classList.contains('tag-delete')) {
    handleDelete(row);
  }
});
