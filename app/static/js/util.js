// Tiny DOM + URL helpers shared across page scripts.

export const qs = (sel, root = document) => root.querySelector(sel);
export const qsa = (sel, root = document) => Array.from(root.querySelectorAll(sel));

// Element factory. attrs is a flat object; children may be strings or Nodes.
// className supported via { class: 'foo bar' }. dataset via { dataset: { tag: 'x' } }.
export function el(tag, attrs = {}, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs)) {
    if (value == null || value === false) continue;
    if (key === 'class') node.className = value;
    else if (key === 'dataset') Object.assign(node.dataset, value);
    else if (key in node) node[key] = value;
    else node.setAttribute(key, value);
  }
  for (const child of children.flat()) {
    if (child == null || child === false) continue;
    node.append(typeof child === 'string' ? document.createTextNode(child) : child);
  }
  return node;
}

export function debounce(fn, ms) {
  let handle = null;
  return function debounced(...args) {
    clearTimeout(handle);
    handle = setTimeout(() => fn.apply(this, args), ms);
  };
}

// Read filter state from window.location.search.
// Returns plain object: { q, tags (array), author, page (int) }.
export function readState() {
  const params = new URLSearchParams(window.location.search);
  const tags = (params.get('tags') || '')
    .split(',')
    .map(t => t.trim())
    .filter(Boolean);
  let page = parseInt(params.get('page'), 10);
  if (!Number.isFinite(page) || page < 1) page = 1;
  return {
    q: (params.get('q') || '').trim(),
    tags,
    author: (params.get('author') || '').trim(),
    page,
  };
}

// Push a new history entry encoding the given state.
export function writeState(state) {
  const params = new URLSearchParams();
  if (state.q) params.set('q', state.q);
  if (state.tags && state.tags.length) params.set('tags', state.tags.join(','));
  if (state.author) params.set('author', state.author);
  if (state.page && state.page > 1) params.set('page', String(state.page));
  const qstr = params.toString();
  const url = window.location.pathname + (qstr ? '?' + qstr : '');
  window.history.pushState(state, '', url);
}

// Accepts ISO 'YYYY-MM-DDTHH:MM:SSZ' or SQLite 'YYYY-MM-DD HH:MM:SS'.
// SQLite emits UTC without a timezone marker, so we tag it as Z explicitly.
export function parseTimestamp(s) {
  if (!s) return null;
  if (s.includes('T')) return new Date(s.endsWith('Z') ? s : s + 'Z');
  return new Date(s.replace(' ', 'T') + 'Z');
}

const _plural = (n, singular) => `${n} ${singular}${n === 1 ? '' : 's'} ago`;

// Returns a human-friendly relative time. 'just now' under one minute.
// Resolution stops at years — anything older just reads 'N years ago'.
export function formatRelativeTime(s) {
  const t = parseTimestamp(s);
  if (!t || isNaN(t.getTime())) return '';
  const seconds = Math.max(0, (Date.now() - t.getTime()) / 1000);
  if (seconds < 60) return 'just now';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return _plural(minutes, 'minute');
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return _plural(hours, 'hour');
  const days = Math.floor(hours / 24);
  if (days === 1) return 'yesterday';
  if (days < 7) return _plural(days, 'day');
  if (days < 30) return _plural(Math.floor(days / 7), 'week');
  if (days < 365) return _plural(Math.floor(days / 30), 'month');
  return _plural(Math.floor(days / 365), 'year');
}
