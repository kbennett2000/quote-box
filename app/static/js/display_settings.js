// Display-mode settings page.
//
// Builds a /display URL from form state, live-previews it, and
// navigates on Submit. No persistence — the bookmark IS the
// persistence. Only emits parameters that differ from defaults so
// the bookmarked URL stays human-readable.

import { qs, qsa } from './util.js';
import { initTagChips } from './tag_chips.js';

const form = qs('#display-settings-form');
const scriptTag = qs('#ds-script');
const DEFAULT_DURATION = parseInt(form.dataset.defaultDuration, 10);
const ALL_TAGS = JSON.parse(scriptTag.dataset.allTags || '[]');

const durationInput = qs('#ds-duration');
const durationValue = qs('#ds-duration-value');
const authorSelect = qs('#ds-author');
const tagInputRoot = qs('.tag-input', form);
const tagModeGroup = qs('#ds-tag-mode-group');
const showTagsCb = qs('#ds-show-tags');
const noControlsCb = qs('#ds-nocontrols');
const urlPreview = qs('#ds-url-preview');

const chips = initTagChips({
  root: tagInputRoot,
  initialTags: [],
  allTags: ALL_TAGS,
  onChange: () => {
    updateTagModeAvailability();
    rebuildUrl();
  },
});

function updateTagModeAvailability() {
  tagModeGroup.disabled = chips.tags.length === 0;
}

function currentTagMode() {
  const checked = qs('input[name="tag_mode"]:checked', tagModeGroup);
  return checked ? checked.value : 'or';
}

function buildUrl() {
  const params = new URLSearchParams();
  const dur = parseInt(durationInput.value, 10);
  if (Number.isFinite(dur) && dur !== DEFAULT_DURATION) {
    params.set('duration', String(dur));
  }
  if (authorSelect.value) {
    params.set('author', authorSelect.value);
  }
  if (chips.tags.length) {
    params.set('tags', chips.tags.join(','));
    // display.js defaults to OR, so only emit tag_mode for AND.
    if (currentTagMode() === 'and') {
      params.set('tag_mode', 'and');
    }
  }
  if (showTagsCb.checked) params.set('show_tags', '1');
  if (noControlsCb.checked) params.set('nocontrols', '1');
  const qs2 = params.toString();
  return '/display' + (qs2 ? '?' + qs2 : '');
}

function rebuildUrl() {
  urlPreview.value = window.location.origin + buildUrl();
}

durationInput.addEventListener('input', () => {
  durationValue.textContent = durationInput.value + 's';
  rebuildUrl();
});
authorSelect.addEventListener('change', rebuildUrl);
showTagsCb.addEventListener('change', rebuildUrl);
noControlsCb.addEventListener('change', rebuildUrl);
for (const r of qsa('input[name="tag_mode"]', tagModeGroup)) {
  r.addEventListener('change', rebuildUrl);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  window.location = buildUrl();
});

urlPreview.addEventListener('click', () => urlPreview.select());
urlPreview.addEventListener('focus', () => urlPreview.select());

updateTagModeAvailability();
rebuildUrl();
