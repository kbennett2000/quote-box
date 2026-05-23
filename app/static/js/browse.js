// Browse page interactivity.
//
// The server renders the initial page from the same URL params this script
// reads on load — no initial fetch needed. The card markup produced by
// `renderQuote()` below must stay aligned with browse.html so dynamic updates
// look identical to the server render.

import { qs, qsa, el, debounce, readState, writeState } from './util.js';

const LIMIT = 50;

function buildParams(state) {
  const params = new URLSearchParams();
  if (state.q) params.set('q', state.q);
  if (state.tags.length) params.set('tags', state.tags.join(','));
  if (state.author) params.set('author', state.author);
  params.set('limit', String(LIMIT));
  params.set('offset', String((state.page - 1) * LIMIT));
  return params;
}

function renderQuote(quote) {
  const children = [
    el('p', { class: 'quote-card-text' }, '“' + quote.text + '”'),
  ];
  if (quote.author || quote.source) {
    const meta = el('p', { class: 'quote-card-meta' });
    if (quote.author) {
      meta.append(el('span', { class: 'quote-card-author' }, quote.author));
    }
    if (quote.source) {
      meta.append(el('span', { class: 'quote-card-source' }, quote.source));
    }
    children.push(meta);
  }
  if (quote.tags && quote.tags.length) {
    const tagList = el('ul', { class: 'quote-card-tags' });
    for (const tag of quote.tags) {
      tagList.append(el('li', {}, el('span', { class: 'tag-chip' }, tag)));
    }
    children.push(tagList);
  }
  return el('a', { class: 'quote-card', href: '/quotes/' + encodeURIComponent(quote.id) }, ...children);
}

function renderQuotesInto(container, quotes) {
  container.replaceChildren(...quotes.map(renderQuote));
}

function renderEmptyState() {
  return el('div', { class: 'empty-state' }, 'No quotes match these filters.');
}

function updatePagination(state, total) {
  const totalPages = Math.max(1, Math.ceil(total / LIMIT));
  qs('#pagination-position').textContent = `Page ${state.page} of ${totalPages}`;
  qs('#prev-page').disabled = state.page <= 1;
  qs('#next-page').disabled = state.page >= totalPages;
  qs('#result-count').textContent =
    total === 1 ? '1 quote' : `${total} quotes`;
}

function updateClearFilters(state) {
  const anyFilter = Boolean(state.q || state.tags.length || state.author);
  const button = qs('#clear-filters');
  if (button) button.hidden = !anyFilter;
}

function updateSearchClearButton(state) {
  const btn = qs('#search-clear');
  if (btn) btn.hidden = !state.q;
}

function updateTagChipStates(state) {
  const selected = new Set(state.tags);
  for (const chip of qsa('.tag-cloud .tag-chip')) {
    const tag = chip.dataset.tag;
    chip.setAttribute('aria-pressed', selected.has(tag) ? 'true' : 'false');
  }
}

async function refresh(state) {
  updateClearFilters(state);
  updateSearchClearButton(state);
  updateTagChipStates(state);

  const grid = qs('#quotes-grid');
  const emptyHolder = qs('#empty-holder');
  const resp = await fetch('/api/quotes?' + buildParams(state).toString());
  if (!resp.ok) {
    grid.replaceChildren(el('div', { class: 'empty-state' }, 'Failed to load quotes.'));
    return;
  }
  const data = await resp.json();
  if (data.quotes.length === 0) {
    grid.replaceChildren();
    emptyHolder.replaceChildren(renderEmptyState());
  } else {
    emptyHolder.replaceChildren();
    renderQuotesInto(grid, data.quotes);
  }
  updatePagination(state, data.total);
}

function init() {
  const searchInput = qs('#q');
  const authorSelect = qs('#author');
  const searchClear = qs('#search-clear');
  const clearFilters = qs('#clear-filters');
  const prev = qs('#prev-page');
  const next = qs('#next-page');

  const triggerRefresh = (state) => {
    writeState(state);
    refresh(state);
  };

  const onSearch = debounce(() => {
    const state = readState();
    state.q = searchInput.value.trim();
    state.page = 1;
    triggerRefresh(state);
  }, 200);

  searchInput.addEventListener('input', onSearch);

  searchClear.addEventListener('click', () => {
    searchInput.value = '';
    const state = readState();
    state.q = '';
    state.page = 1;
    triggerRefresh(state);
  });

  authorSelect.addEventListener('change', () => {
    const state = readState();
    state.author = authorSelect.value;
    state.page = 1;
    triggerRefresh(state);
  });

  for (const chip of qsa('.tag-cloud .tag-chip')) {
    chip.addEventListener('click', () => {
      const state = readState();
      const tag = chip.dataset.tag;
      const idx = state.tags.indexOf(tag);
      if (idx >= 0) state.tags.splice(idx, 1);
      else state.tags.push(tag);
      state.page = 1;
      triggerRefresh(state);
    });
  }

  clearFilters.addEventListener('click', () => {
    searchInput.value = '';
    authorSelect.value = '';
    triggerRefresh({ q: '', tags: [], author: '', page: 1 });
  });

  prev.addEventListener('click', () => {
    const state = readState();
    state.page = Math.max(1, state.page - 1);
    triggerRefresh(state);
  });

  next.addEventListener('click', () => {
    const state = readState();
    state.page += 1;
    triggerRefresh(state);
  });

  window.addEventListener('popstate', () => {
    const state = readState();
    searchInput.value = state.q;
    authorSelect.value = state.author;
    refresh(state);
  });

  // Initial sync of UI affordances (server already rendered the grid).
  const state = readState();
  updateClearFilters(state);
  updateSearchClearButton(state);
}

init();
