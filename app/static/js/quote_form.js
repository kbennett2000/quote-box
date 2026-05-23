// Add/edit/delete a quote.
//
// Tag input is a custom chip widget — vanilla DOM, no framework. State is
// a plain array of strings; the chips and suggestion popover render off it.
// Author autocomplete uses the native HTML <datalist> populated server-side
// so no JS is needed for that field.

import { qs, qsa, el } from './util.js';

const form = qs('#quote-form');
const scriptTag = qs('#quote-form-script');
const errorBox = qs('#form-error');
const MODE = form.dataset.mode;                       // "new" | "edit"
const QUOTE_ID = form.dataset.quoteId || '';
const ALL_TAGS = JSON.parse(scriptTag.dataset.allTags || '[]');

const tagInputRoot = qs('.tag-input', form);
const tagField = qs('.tag-input-field', tagInputRoot);
const chipsList = qs('.tag-input-chips', tagInputRoot);
const suggestionsList = qs('.tag-input-suggestions', tagInputRoot);

const tags = JSON.parse(tagInputRoot.dataset.initialTags || '[]');

function normalizeTagName(raw) {
  const v = (raw || '').trim().toLowerCase();
  if (!v) return null;
  if (v.length > 50) return null;
  return v;
}

function commitTag(raw) {
  const v = normalizeTagName(raw);
  if (!v) return false;
  if (tags.includes(v)) return false;
  tags.push(v);
  renderChips();
  return true;
}

function removeTag(value) {
  const idx = tags.indexOf(value);
  if (idx >= 0) {
    tags.splice(idx, 1);
    renderChips();
  }
}

function renderChips() {
  chipsList.replaceChildren(
    ...tags.map(t =>
      el(
        'li',
        { class: 'tag-input-chip' },
        t,
        el(
          'button',
          {
            type: 'button',
            class: 'tag-input-chip-remove',
            'aria-label': 'Remove ' + t,
            dataset: { tag: t },
          },
          '×',
        ),
      ),
    ),
  );
}

function renderSuggestions(prefix) {
  const lowered = prefix.toLowerCase();
  if (!lowered) {
    suggestionsList.hidden = true;
    return;
  }
  const matches = ALL_TAGS
    .filter(t => t.startsWith(lowered) && !tags.includes(t))
    .slice(0, 8);
  if (!matches.length) {
    suggestionsList.hidden = true;
    return;
  }
  suggestionsList.replaceChildren(
    ...matches.map(t =>
      el('li', { class: 'tag-input-suggestion', dataset: { tag: t } }, t),
    ),
  );
  suggestionsList.hidden = false;
}

tagField.addEventListener('input', () => {
  renderSuggestions(tagField.value);
});

tagField.addEventListener('keydown', (event) => {
  if (event.key === 'Enter' || event.key === ',' || event.key === 'Tab') {
    const raw = tagField.value;
    if (raw.trim()) {
      event.preventDefault();
      if (commitTag(raw)) {
        tagField.value = '';
        suggestionsList.hidden = true;
      }
    }
  } else if (event.key === 'Backspace' && !tagField.value && tags.length) {
    event.preventDefault();
    tags.pop();
    renderChips();
  } else if (event.key === 'Escape') {
    suggestionsList.hidden = true;
  }
});

tagField.addEventListener('blur', () => {
  // Hide suggestions on a small delay so clicks register.
  setTimeout(() => { suggestionsList.hidden = true; }, 120);
});

suggestionsList.addEventListener('mousedown', (event) => {
  // mousedown (not click) so it fires before the field's blur.
  const target = event.target.closest('.tag-input-suggestion');
  if (!target) return;
  event.preventDefault();
  if (commitTag(target.dataset.tag)) {
    tagField.value = '';
    suggestionsList.hidden = true;
    tagField.focus();
  }
});

chipsList.addEventListener('click', (event) => {
  const target = event.target.closest('.tag-input-chip-remove');
  if (target) removeTag(target.dataset.tag);
});

renderChips();

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
  if (tagField.value.trim()) commitTag(tagField.value);
  const author = (data.get('author') || '').trim();
  const source = (data.get('source') || '').trim();
  const payload = { text: (data.get('text') || '').trim(), tags };
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
