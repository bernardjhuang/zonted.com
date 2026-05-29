const root = document.getElementById('dialog');
const nameEl = document.getElementById('dialog-name');
const textEl = document.getElementById('dialog-text');
const hintEl = document.getElementById('dialog-hint');

const TYPE_CPS = 50;

let pages = [];
let pageIdx = 0;
let charIdx = 0;
let lastTick = 0;
let typing = false;
let open = false;

export function isOpen() { return open; }

export function openDialog({ name = '', pages: incoming = [] } = {}) {
  pages = Array.isArray(incoming) ? incoming : [String(incoming)];
  if (pages.length === 0) pages = [''];
  pageIdx = 0;
  charIdx = 0;
  typing = true;
  lastTick = performance.now();
  open = true;
  nameEl.textContent = name;
  textEl.textContent = '';
  hintEl.classList.remove('show');
  root.classList.remove('hidden');
}

export function closeDialog() {
  open = false;
  typing = false;
  root.classList.add('hidden');
}

export function advance() {
  if (!open) return;
  if (typing) {
    charIdx = pages[pageIdx].length;
    textEl.textContent = pages[pageIdx];
    typing = false;
    hintEl.classList.add('show');
    return;
  }
  pageIdx++;
  if (pageIdx >= pages.length) {
    closeDialog();
    return;
  }
  charIdx = 0;
  typing = true;
  lastTick = performance.now();
  textEl.textContent = '';
  hintEl.classList.remove('show');
}

export function tick(now) {
  if (!open || !typing) return;
  const dt = Math.max(0, (now - lastTick) / 1000);
  lastTick = now;
  charIdx = Math.min(pages[pageIdx].length, charIdx + dt * TYPE_CPS);
  textEl.textContent = pages[pageIdx].slice(0, Math.floor(charIdx));
  if (charIdx >= pages[pageIdx].length) {
    typing = false;
    hintEl.classList.add('show');
  }
}
