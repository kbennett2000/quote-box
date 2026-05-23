// Add/edit/delete a quote.
//
// Tag input is the shared chip widget from tag_chips.js. Author
// autocomplete uses the native HTML <datalist> populated server-side,
// so no JS is needed for that field.

import { qs } from './util.js';
import { initTagChips } from './tag_chips.js';

const form = qs('#quote-form');
const scriptTag = qs('#quote-form-script');
const errorBox = qs('#form-error');
const MODE = form.dataset.mode;                       // "new" | "edit"
const QUOTE_ID = form.dataset.quoteId || '';
const ALL_TAGS = JSON.parse(scriptTag.dataset.allTags || '[]');

const tagInputRoot = qs('.tag-input', form);
const chips = initTagChips({
  root: tagInputRoot,
  initialTags: JSON.parse(tagInputRoot.dataset.initialTags || '[]'),
  allTags: ALL_TAGS,
});

function showError(message) {
  errorBox.textContent = message;
  errorBox.hidden = false;
  errorBox.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function clearError() {
  errorBox.textContent = '';
  errorBox.hidden = true;
}

function gatherPayload() {
  const data = new FormData(form);
  // Commit any pending tag text the user hasn't pressed Enter on.
  chips.commitPending();
  const author = (data.get('author') || '').trim();
  const source = (data.get('source') || '').trim();
  const payload = { text: (data.get('text') || '').trim(), tags: chips.tags };
  if (author) payload.author = author;
  if (source) payload.source = source;
  return payload;
}

async function submitForm(event) {
  event.preventDefault();
  clearError();
  const payload = gatherPayload();
  if (!payload.text) {
    showError('Text is required.');
    return;
  }
  const url = MODE === 'edit' ? `/api/quotes/${QUOTE_ID}` : '/api/quotes';
  const method = MODE === 'edit' ? 'PUT' : 'POST';
  let resp;
  try {
    resp = await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
  } catch {
    showError('Network error. Please try again.');
    return;
  }
  if (resp.status === 201 || resp.status === 200) {
    const body = await resp.json();
    window.location = '/quotes/' + encodeURIComponent(body.id);
    return;
  }
  if (resp.status === 400) {
    const body = await resp.json().catch(() => ({}));
    showError(body.error || 'Validation failed.');
    return;
  }
  if (resp.status === 404) {
    showError('Quote not found. It may have been deleted.');
    return;
  }
  showError('Save failed. Please try again.');
}

form.addEventListener('submit', submitForm);

const deleteButton = qs('#delete-quote');
if (deleteButton) {
  deleteButton.addEventListener('click', async () => {
    if (!window.confirm('Delete this quote? This cannot be undone.')) return;
    const resp = await fetch(`/api/quotes/${QUOTE_ID}`, { method: 'DELETE' });
    if (resp.status === 204) {
      window.location = '/';
    } else {
      showError('Delete failed. Please try again.');
    }
  });
}
