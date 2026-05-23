// Reusable tag-chip input widget.
//
// Wires up a `.tag-input` root that contains:
//   <ul class="tag-input-chips"></ul>
//   <input class="tag-input-field">
//   <ul class="tag-input-suggestions" hidden></ul>
//
// State is the `initialTags` array, mutated in place. The factory
// returns that same reference so callers can read current state on
// submit. Behavior: type a tag and press Enter, comma, or Tab to commit;
// Backspace on an empty field removes the last chip; Escape closes the
// suggestion popover; clicking a suggestion commits it. New tags are
// lowercased + length-validated (1–50 chars) at commit time, matching
// the server's normalizeTagName rule.

import { qs, el } from './util.js';

const MAX_TAG_LEN = 50;

function normalizeTagName(raw) {
  const v = (raw || '').trim().toLowerCase();
  if (!v) return null;
  if (v.length > MAX_TAG_LEN) return null;
  return v;
}

export function initTagChips({ root, initialTags, allTags, onChange }) {
  const tags = initialTags;
  const field = qs('.tag-input-field', root);
  const chipsList = qs('.tag-input-chips', root);
  const suggestions = qs('.tag-input-suggestions', root);
  const pool = allTags || [];
  const notify = () => { if (typeof onChange === 'function') onChange(tags); };

  function commit(raw) {
    const v = normalizeTagName(raw);
    if (!v) return false;
    if (tags.includes(v)) return false;
    tags.push(v);
    renderChips();
    notify();
    return true;
  }

  function remove(value) {
    const idx = tags.indexOf(value);
    if (idx < 0) return;
    tags.splice(idx, 1);
    renderChips();
    notify();
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
    if (!lowered) { suggestions.hidden = true; return; }
    const matches = pool
      .filter(t => t.startsWith(lowered) && !tags.includes(t))
      .slice(0, 8);
    if (!matches.length) { suggestions.hidden = true; return; }
    suggestions.replaceChildren(
      ...matches.map(t =>
        el('li', { class: 'tag-input-suggestion', dataset: { tag: t } }, t),
      ),
    );
    suggestions.hidden = false;
  }

  field.addEventListener('input', () => renderSuggestions(field.value));

  field.addEventListener('keydown', (event) => {
    if (event.key === 'Enter' || event.key === ',' || event.key === 'Tab') {
      const raw = field.value;
      if (raw.trim()) {
        event.preventDefault();
        if (commit(raw)) {
          field.value = '';
          suggestions.hidden = true;
        }
      }
    } else if (event.key === 'Backspace' && !field.value && tags.length) {
      event.preventDefault();
      tags.pop();
      renderChips();
      notify();
    } else if (event.key === 'Escape') {
      suggestions.hidden = true;
    }
  });

  field.addEventListener('blur', () => {
    // Hide suggestions on a small delay so suggestion clicks still register.
    setTimeout(() => { suggestions.hidden = true; }, 120);
  });

  suggestions.addEventListener('mousedown', (event) => {
    // mousedown (not click) so it fires before the field's blur.
    const target = event.target.closest('.tag-input-suggestion');
    if (!target) return;
    event.preventDefault();
    if (commit(target.dataset.tag)) {
      field.value = '';
      suggestions.hidden = true;
      field.focus();
    }
  });

  chipsList.addEventListener('click', (event) => {
    const target = event.target.closest('.tag-input-chip-remove');
    if (target) remove(target.dataset.tag);
  });

  // Helper for callers to commit any text the user typed but didn't
  // press Enter on (typical "user clicked Submit without pressing Enter
  // on the last chip" case).
  function commitPending() {
    if (field.value.trim()) commit(field.value);
  }

  renderChips();
  return { tags, commitPending };
}
