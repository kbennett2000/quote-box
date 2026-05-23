// Display-mode rotation engine.
//
// Reads URL params for filters + duration + show_tags + nocontrols, fetches a
// shuffled id queue from /api/quotes/shuffle (with tag_mode=or), then walks
// it one ID at a time. CSS opacity transition between quotes. Wake lock
// keeps the screen alive; controls fade after 3s of mouse idle.

const TRANSITION_MS = 800;
const FADE_HALF_MS = TRANSITION_MS / 2;
const DEFAULT_DURATION_SEC = 20;
const MIN_DURATION_SEC = 5;
const MAX_DURATION_SEC = 600;
const IDLE_HIDE_MS = 3000;

const stage = document.getElementById('display-stage');
const quoteEl = document.getElementById('display-quote');
const textEl = document.getElementById('display-text');
const authorEl = document.getElementById('display-author');
const sourceEl = document.getElementById('display-source');
const tagsEl = document.getElementById('display-tags');
const emptyEl = document.getElementById('display-empty');
const controls = document.getElementById('display-controls');
const toggleBtn = document.getElementById('ctrl-toggle');
const prevBtn = document.getElementById('ctrl-prev');
const nextBtn = document.getElementById('ctrl-next');
const fullscreenBtn = document.getElementById('ctrl-fullscreen');
const durationInput = document.getElementById('ctrl-duration');
const durationLabel = document.getElementById('ctrl-duration-label');

const state = {
  queue: [],
  index: 0,
  paused: false,
  durationMs: DEFAULT_DURATION_SEC * 1000,
  tickTimer: null,
  dwellStartedAt: 0,
  pauseRemainingMs: null,
  wakeLock: null,
  filterParams: new URLSearchParams(),
  showTags: false,
  noControls: false,
  current: null,
};

function readUrlState() {
  const url = new URLSearchParams(window.location.search);
  const rawTags = (url.get('tags') || '').trim();
  if (rawTags) state.filterParams.set('tags', rawTags);
  const author = (url.get('author') || '').trim();
  if (author) state.filterParams.set('author', author);
  const rawDuration = parseInt(url.get('duration') || '', 10);
  if (Number.isFinite(rawDuration)) {
    const clamped = Math.max(MIN_DURATION_SEC, Math.min(MAX_DURATION_SEC, rawDuration));
    state.durationMs = clamped * 1000;
    durationInput.value = String(clamped);
    durationLabel.textContent = clamped + 's';
  }
  state.showTags = url.get('show_tags') === '1';
  state.noControls = url.get('nocontrols') === '1';
  if (state.noControls) controls.hidden = true;
}

async function fetchQueue() {
  const params = new URLSearchParams(state.filterParams);
  params.set('tag_mode', 'or');
  try {
    const resp = await fetch('/api/quotes/shuffle?' + params.toString());
    if (!resp.ok) return [];
    const body = await resp.json();
    return Array.isArray(body.ids) ? body.ids : [];
  } catch (err) {
    console.error('shuffle fetch failed:', err);
    return [];
  }
}

async function fetchQuote(id) {
  try {
    const resp = await fetch('/api/quotes/' + encodeURIComponent(id));
    return resp.ok ? await resp.json() : null;
  } catch (err) {
    console.error('quote fetch failed:', err);
    return null;
  }
}

function wait(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

function renderEmpty() {
  emptyEl.hidden = false;
  quoteEl.hidden = true;
  controls.hidden = true;
}

function renderQuote(q) {
  state.current = q;
  textEl.textContent = q.text || '';

  if (q.author) {
    authorEl.textContent = q.author;
    authorEl.hidden = false;
  } else {
    authorEl.hidden = true;
  }

  if (q.source) {
    sourceEl.textContent = q.source;
    sourceEl.hidden = false;
  } else {
    sourceEl.hidden = true;
  }

  if (state.showTags && Array.isArray(q.tags) && q.tags.length) {
    tagsEl.replaceChildren(
      ...q.tags.map((t) => {
        const li = document.createElement('li');
        li.className = 'display-tag';
        li.textContent = t;
        return li;
      }),
    );
    tagsEl.hidden = false;
  } else {
    tagsEl.hidden = true;
  }
}

async function showCurrent() {
  if (state.queue.length === 0) {
    renderEmpty();
    return;
  }
  const id = state.queue[state.index];
  const quote = await fetchQuote(id);
  if (!quote) {
    // skip the unfetchable id without breaking the loop
    scheduleNext(state.durationMs);
    return;
  }
  stage.dataset.state = 'transitioning';
  await wait(FADE_HALF_MS);
  renderQuote(quote);
  stage.dataset.state = 'visible';
  state.dwellStartedAt = Date.now();
  if (!state.paused) scheduleNext(state.durationMs);
}

function scheduleNext(ms) {
  clearTimeout(state.tickTimer);
  state.tickTimer = window.setTimeout(() => advance(1), ms);
}

async function advance(delta) {
  clearTimeout(state.tickTimer);
  state.pauseRemainingMs = null;
  if (state.queue.length === 0) return;
  const len = state.queue.length;
  const next = state.index + delta;
  if (delta > 0 && next >= len) {
    // Wrapped past the end — refetch for a fresh shuffle, no repeats.
    state.queue = await fetchQueue();
    state.index = 0;
  } else {
    state.index = ((next % len) + len) % len;
  }
  showCurrent();
}

function togglePause() {
  if (state.paused) {
    state.paused = false;
    const remaining = state.pauseRemainingMs ?? state.durationMs;
    state.pauseRemainingMs = null;
    scheduleNext(remaining);
    toggleBtn.textContent = '||';
    toggleBtn.setAttribute('aria-label', 'Pause');
  } else {
    state.paused = true;
    clearTimeout(state.tickTimer);
    state.pauseRemainingMs = Math.max(
      0,
      state.durationMs - (Date.now() - state.dwellStartedAt),
    );
    toggleBtn.textContent = '▶';
    toggleBtn.setAttribute('aria-label', 'Play');
  }
}

function toggleFullscreen() {
  if (document.fullscreenElement) {
    document.exitFullscreen();
  } else {
    document.documentElement.requestFullscreen?.();
  }
}

async function requestWakeLock() {
  if (!('wakeLock' in navigator)) {
    console.warn(
      'Screen Wake Lock API unavailable. Disable screen sleep in OS settings for kiosk use.',
    );
    return;
  }
  try {
    state.wakeLock = await navigator.wakeLock.request('screen');
  } catch (err) {
    console.warn('wake lock request failed:', err);
  }
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') requestWakeLock();
});

// Idle / mouse handling.
let idleTimer = null;
function showControls() {
  if (state.noControls) return;
  controls.classList.add('visible');
  document.body.classList.remove('cursor-hidden');
  clearTimeout(idleTimer);
  idleTimer = window.setTimeout(() => {
    controls.classList.remove('visible');
    document.body.classList.add('cursor-hidden');
  }, IDLE_HIDE_MS);
}
document.addEventListener('mousemove', showControls);

// Keyboard shortcuts.
document.addEventListener('keydown', (event) => {
  const target = event.target;
  if (target instanceof HTMLElement && ['INPUT', 'TEXTAREA'].includes(target.tagName)) {
    return;
  }
  if (event.key === ' ') {
    event.preventDefault();
    togglePause();
  } else if (event.key === 'ArrowLeft') {
    event.preventDefault();
    advance(-1);
  } else if (event.key === 'ArrowRight') {
    event.preventDefault();
    advance(1);
  } else if (event.key === 'f' || event.key === 'F') {
    event.preventDefault();
    toggleFullscreen();
  }
});

// Controls wiring.
toggleBtn.addEventListener('click', togglePause);
prevBtn.addEventListener('click', () => advance(-1));
nextBtn.addEventListener('click', () => advance(1));
fullscreenBtn.addEventListener('click', toggleFullscreen);
durationInput.addEventListener('input', () => {
  const seconds = parseInt(durationInput.value, 10);
  if (!Number.isFinite(seconds)) return;
  state.durationMs = seconds * 1000;
  durationLabel.textContent = seconds + 's';
});

async function init() {
  readUrlState();
  requestWakeLock();
  state.queue = await fetchQueue();
  state.index = 0;
  showControls();
  showCurrent();
}

init();
