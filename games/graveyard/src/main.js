import * as Dialog from './dialog.js';
import { projects } from './projects.js';

const canvas = document.getElementById('canvas');
const ctx = canvas.getContext('2d');
const loaderEl = document.getElementById('loader');
const hudCountEl = document.getElementById('hud-count');

// --- maze ----------------------------------------------------------------
const MAZE = [
  '###############',
  '#.............#',
  '#.###.#####.#.#',
  '#.#.....#.....#',
  '#.#.###.#.###.#',
  '#.....#.#.....#',
  '#.###.#.#.###.#',
  '#.....#.#...#.#',
  '#.###.###.#.#.#',
  '#.............#',
  '###############',
];
const COLS = MAZE[0].length;
const ROWS = MAZE.length;
const TILE = 16;
const MAZE_W = COLS * TILE;
const MAZE_H = ROWS * TILE;

let SCALE = 3;
let offsetX = 0, offsetY = 0;

function resize() {
  canvas.width = window.innerWidth;
  canvas.height = window.innerHeight;
  const sx = (canvas.width - 32) / MAZE_W;
  const sy = (canvas.height - 100) / MAZE_H;
  SCALE = Math.max(2, Math.floor(Math.min(sx, sy)));
  offsetX = Math.floor((canvas.width - MAZE_W * SCALE) / 2);
  offsetY = Math.floor((canvas.height - MAZE_H * SCALE) / 2);
  ctx.imageSmoothingEnabled = false;
}
window.addEventListener('resize', resize);
resize();

function isWall(c, r) {
  if (r < 0 || r >= ROWS || c < 0 || c >= COLS) return true;
  return MAZE[r][c] === '#';
}

// --- assets --------------------------------------------------------------
const sheets = {};
function loadImage(name, src) {
  return new Promise((res, rej) => {
    const img = new Image();
    img.onload = () => { sheets[name] = img; res(); };
    img.onerror = rej;
    img.src = src;
  });
}
const SPRITES = {
  brick:    ['tileset', 144,  96, 16, 16],
  tomb:     ['tileset',  96,   0, 16, 32],
  deadTree: ['tileset', 192, 752, 80, 80],
  obelisk:  ['tileset', 208, 144, 16, 64],
};
function drawSprite(key, dx, dy) {
  const s = SPRITES[key];
  if (!s) return;
  const [sheet, sx, sy, w, h] = s;
  const img = sheets[sheet];
  if (!img) return;
  ctx.drawImage(img, sx, sy, w, h, Math.floor(dx), Math.floor(dy), w, h);
}

// --- entities ------------------------------------------------------------
function makeEntity(col, row, kind, facing = 'right') {
  return {
    col, row,
    fromCol: col, fromRow: row,
    toCol: col, toRow: row,
    px: col * TILE + TILE / 2,
    py: row * TILE + TILE / 2,
    tweenT: 1,
    dir: null,
    facing,
    queueDir: null,
    kind,
  };
}

const PLAYER_TPS = 4.5;
const GHOST_TPS = 3.0;
const SCARED_TPS = 1.9;
const POWERUP_DURATION_MS = 12000;
const POWERUP_WARN_MS = 3000;

const player = makeEntity(7, 5, 'player');

const ghosts = [
  Object.assign(makeEntity(13, 9, 'ghost'), {
    project: projects.find((p) => p.slug === 'kapiko'),
    color: '#10b981',
    alive: true,
  }),
];

const powerups = [
  { col: 1,  row: 1, sprite: 'puChatgpt', consumed: false, label: 'ChatGPT' },
  { col: 13, row: 1, sprite: 'puGemini',  consumed: false, label: 'Gemini'  },
  { col: 1,  row: 9, sprite: 'puClaude',  consumed: false, label: 'Claude'  },
];

let powerUntil = 0;
const tombMarkers = [];
let gameOver = false;

function isPoweredUp(now) { return now < powerUntil; }
function powerTimeLeft(now) { return Math.max(0, powerUntil - now); }

// --- movement primitives -------------------------------------------------
function dirDelta(d) {
  return { up: [0, -1], down: [0, 1], left: [-1, 0], right: [1, 0] }[d] || [0, 0];
}
function oppDir(d) {
  return { up: 'down', down: 'up', left: 'right', right: 'left' }[d];
}
function canStep(col, row, dir) {
  const [dc, dr] = dirDelta(dir);
  return !isWall(col + dc, row + dr);
}
function startStep(e, dir) {
  if (!canStep(e.col, e.row, dir)) return false;
  const [dc, dr] = dirDelta(dir);
  e.fromCol = e.col;
  e.fromRow = e.row;
  e.toCol = e.col + dc;
  e.toRow = e.row + dr;
  e.tweenT = 0;
  e.dir = dir;
  e.facing = dir;
  return true;
}
function updateEntity(e, tps, dt, decideDir) {
  if (e.tweenT < 1) {
    e.tweenT = Math.min(1, e.tweenT + tps * dt);
    const t = e.tweenT;
    e.px = (e.fromCol + (e.toCol - e.fromCol) * t) * TILE + TILE / 2;
    e.py = (e.fromRow + (e.toRow - e.fromRow) * t) * TILE + TILE / 2;
    if (e.tweenT < 1) return;
    e.col = e.toCol;
    e.row = e.toRow;
    e.px = e.col * TILE + TILE / 2;
    e.py = e.row * TILE + TILE / 2;
  }
  const nextDir = decideDir(e);
  if (nextDir) startStep(e, nextDir);
  else e.dir = null;
}

// --- input + AI ----------------------------------------------------------
const DIR_KEYS = {
  'arrowup': 'up', 'w': 'up',
  'arrowdown': 'down', 's': 'down',
  'arrowleft': 'left', 'a': 'left',
  'arrowright': 'right', 'd': 'right',
};
window.addEventListener('keydown', (e) => {
  const k = e.key.toLowerCase();
  if (k === 'r' && gameOver) {
    e.preventDefault();
    resetGame();
    return;
  }
  if (k === 'e' || k === ' ' || k === 'enter') {
    e.preventDefault();
    if (Dialog.isOpen()) Dialog.advance();
    return;
  }
  if (Dialog.isOpen() || gameOver) return;
  if (DIR_KEYS[k]) {
    player.queueDir = DIR_KEYS[k];
    e.preventDefault();
  }
});

function decidePlayerDir(p) {
  if (p.queueDir && canStep(p.col, p.row, p.queueDir)) {
    const d = p.queueDir;
    p.queueDir = null;
    return d;
  }
  if (p.dir && canStep(p.col, p.row, p.dir)) return p.dir;
  return null;
}

function decideGhostDir(g) {
  const opts = ['up', 'down', 'left', 'right']
    .filter((d) => d !== oppDir(g.dir) && canStep(g.col, g.row, d));
  if (opts.length === 0) {
    return g.dir && canStep(g.col, g.row, oppDir(g.dir)) ? oppDir(g.dir) : null;
  }
  if (opts.length === 1) return opts[0];
  return opts[Math.floor(Math.random() * opts.length)];
}

// --- catch + powerup pickup ---------------------------------------------
function checkPowerupPickup() {
  for (const pu of powerups) {
    if (pu.consumed) continue;
    if (pu.col === player.col && pu.row === player.row) {
      pu.consumed = true;
      powerUntil = performance.now() + POWERUP_DURATION_MS;
    }
  }
}

function checkGhostCollision(now) {
  if (Dialog.isOpen() || gameOver) return;
  const powered = isPoweredUp(now);
  for (const g of ghosts) {
    if (!g.alive) continue;
    const dx = g.px - player.px;
    const dy = g.py - player.py;
    if (dx * dx + dy * dy >= 70) continue;
    if (powered) {
      g.alive = false;
      tombMarkers.push({ col: g.col, row: g.row });
      Dialog.openDialog({
        name: `${g.project.name} · ${g.project.born} ☩ ${g.project.died}`,
        pages: g.project.pages,
      });
      updateHud();
    } else {
      gameOver = true;
    }
    return;
  }
}

function resetGame() {
  player.col = 7; player.row = 5;
  player.fromCol = 7; player.fromRow = 5;
  player.toCol = 7;  player.toRow = 5;
  player.px = 7 * TILE + TILE / 2;
  player.py = 5 * TILE + TILE / 2;
  player.tweenT = 1;
  player.dir = null;
  player.facing = 'right';
  player.queueDir = null;

  for (const g of ghosts) {
    const spawn = g.kind === 'ghost' ? { c: 13, r: 9 } : { c: g.col, r: g.row };
    g.col = spawn.c; g.row = spawn.r;
    g.fromCol = spawn.c; g.fromRow = spawn.r;
    g.toCol = spawn.c;   g.toRow = spawn.r;
    g.px = spawn.c * TILE + TILE / 2;
    g.py = spawn.r * TILE + TILE / 2;
    g.tweenT = 1;
    g.dir = null;
    g.facing = 'left';
    g.queueDir = null;
    g.alive = true;
    startStep(g, 'left');
  }
  for (const pu of powerups) pu.consumed = false;
  tombMarkers.length = 0;
  powerUntil = 0;
  gameOver = false;
  updateHud();
}

function updateHud() {
  const dead = ghosts.filter((g) => !g.alive).length;
  hudCountEl.textContent = `${dead} / ${ghosts.length}`;
}

// --- pixel sprites -------------------------------------------------------
// Project ghosts — classic Pacman ghost silhouette
const GHOST_BODY = [
  '..####..',
  '.######.',
  '########',
  '##X##X##',
  '########',
  '########',
  '########',
];
const GHOST_FRINGE_A = '#.##.##.';
const GHOST_FRINGE_B = '.##.##.#';

function drawGhostEntity(g, now, scared) {
  const frame = Math.floor(now / 220) % 2;
  const fringe = frame === 0 ? GHOST_FRINGE_A : GHOST_FRINGE_B;
  const body = scared ? 'rgba(70, 90, 220, 0.95)' : g.color;
  const eyeColor = scared ? '#ffffff' : '#0a0410';
  const xx = g.px - 4;
  const yy = g.py - 4;
  for (let py = 0; py < 7; py++) {
    for (let px = 0; px < 8; px++) {
      const ch = GHOST_BODY[py][px];
      if (ch === '.') continue;
      ctx.fillStyle = ch === 'X' ? eyeColor : body;
      ctx.fillRect(xx + px, yy + py, 1, 1);
    }
  }
  // wavy fringe row
  for (let px = 0; px < 8; px++) {
    if (fringe[px] === '#') {
      ctx.fillStyle = body;
      ctx.fillRect(xx + px, yy + 7, 1, 1);
    }
  }
  // tiny pupil inside the eyes pointing toward facing
  if (!scared) {
    const [dx, dy] = dirDelta(g.facing);
    ctx.fillStyle = '#0a0410';
    ctx.fillRect(xx + 2 + dx, yy + 3 + dy, 1, 1);
    ctx.fillRect(xx + 5 + dx, yy + 3 + dy, 1, 1);
  }
}

// Player Pacman
function drawPacman(p, now) {
  const r = 5;
  const open = (Math.sin(now * 0.012) + 1) / 2 * 0.55 + 0.06;
  const dirAng = { right: 0, down: Math.PI / 2, left: Math.PI, up: -Math.PI / 2 }[p.facing];
  ctx.fillStyle = '#fbbf24';
  ctx.beginPath();
  ctx.moveTo(p.px, p.py);
  ctx.arc(p.px, p.py, r, dirAng + open, dirAng - open + Math.PI * 2);
  ctx.closePath();
  ctx.fill();
  // Eye — always on the upper half of the head, biased away from the mouth
  let eyeDx = 0, eyeDy = -2;
  if (p.facing === 'right') { eyeDx = -1; eyeDy = -2; }
  if (p.facing === 'left')  { eyeDx =  1; eyeDy = -2; }
  if (p.facing === 'up')    { eyeDx = -1; eyeDy = -1; }
  if (p.facing === 'down')  { eyeDx = -1; eyeDy = -2; }
  ctx.fillStyle = '#1a0a25';
  ctx.fillRect(Math.floor(p.px + eyeDx), Math.floor(p.py + eyeDy), 1, 1);

  // Power-up glow ring
  if (isPoweredUp(now)) {
    const left = powerTimeLeft(now);
    const flashing = left < POWERUP_WARN_MS;
    const flash = flashing ? (Math.sin(now * 0.025) + 1) / 2 : 1;
    ctx.save();
    ctx.globalAlpha = 0.55 * flash;
    ctx.strokeStyle = '#fff9c4';
    ctx.lineWidth = 0.6;
    ctx.beginPath();
    ctx.arc(p.px, p.py, r + 2 + Math.sin(now * 0.01) * 0.5, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

// Labels rendered in screen space for crisp text
function drawGhostLabel(g) {
  const sx = offsetX + g.px * SCALE;
  const sy = offsetY + g.py * SCALE - SCALE * 7;
  ctx.save();
  ctx.font = `700 ${Math.max(10, Math.floor(SCALE * 4.0))}px "Special Elite", ui-monospace, monospace`;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'bottom';
  ctx.shadowColor = 'rgba(0, 0, 0, 0.85)';
  ctx.shadowBlur = Math.max(2, SCALE);
  ctx.fillStyle = g.color;
  ctx.fillText(g.project.name, sx, sy);
  ctx.restore();
}

function drawPowerup(pu, now) {
  const img = sheets[pu.sprite];
  if (!img) return;
  const cx = pu.col * TILE + TILE / 2;
  const cy = pu.row * TILE + TILE / 2;
  const bob = Math.sin(now * 0.004 + pu.col + pu.row) * 0.7;
  const size = 11;
  ctx.save();
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = 'high';
  // soft glow underneath
  const glow = ctx.createRadialGradient(cx, cy + bob, 1, cx, cy + bob, size);
  glow.addColorStop(0, 'rgba(255, 220, 140, 0.35)');
  glow.addColorStop(1, 'rgba(255, 220, 140, 0)');
  ctx.fillStyle = glow;
  ctx.fillRect(cx - size, cy + bob - size, size * 2, size * 2);
  ctx.drawImage(img, cx - size / 2, cy + bob - size / 2, size, size);
  ctx.restore();
}

// --- background layers ---------------------------------------------------
const STARS = Array.from({ length: 180 }, () => ({
  rx: Math.random(),
  ry: Math.random() * 0.62,
  twinkle: Math.random() * Math.PI * 2,
  size: Math.random() < 0.82 ? 1 : 2,
  warm: Math.random() < 0.12,
}));
const MIST = Array.from({ length: 6 }, (_, i) => ({
  rx0: Math.random(),
  ry: 0.62 + Math.random() * 0.20,
  w: 0.18 + Math.random() * 0.30,
  h: 0.05 + Math.random() * 0.06,
  speed: 0.00006 + Math.random() * 0.00010,
  alpha: 0.05 + Math.random() * 0.08,
}));

function drawCastle(x, baseY, s) {
  ctx.fillStyle = 'rgba(8, 5, 18, 0.92)';
  // main keep
  ctx.fillRect(x, baseY - 24 * s, 70 * s, 24 * s);
  // left tower
  ctx.fillRect(x - 6 * s,  baseY - 40 * s, 14 * s, 40 * s);
  // right tower
  ctx.fillRect(x + 62 * s, baseY - 40 * s, 14 * s, 40 * s);
  // central spire
  ctx.fillRect(x + 30 * s, baseY - 52 * s, 10 * s, 52 * s);
  // pointed roofs
  for (const tx of [x - 6 * s, x + 30 * s, x + 62 * s]) {
    const w = tx === x + 30 * s ? 10 * s : 14 * s;
    const peakH = tx === x + 30 * s ? 14 * s : 10 * s;
    const top = tx === x + 30 * s ? baseY - 52 * s : baseY - 40 * s;
    ctx.beginPath();
    ctx.moveTo(tx, top);
    ctx.lineTo(tx + w / 2, top - peakH);
    ctx.lineTo(tx + w, top);
    ctx.closePath();
    ctx.fill();
  }
  // a tiny lit window
  ctx.fillStyle = 'rgba(255, 220, 140, 0.45)';
  ctx.fillRect(x + 33 * s, baseY - 30 * s, 4 * s, 5 * s);
}

function renderBackground(now) {
  // Sky gradient
  const grad = ctx.createLinearGradient(0, 0, 0, canvas.height);
  grad.addColorStop(0,    '#05030c');
  grad.addColorStop(0.4,  '#100623');
  grad.addColorStop(0.78, '#0a061a');
  grad.addColorStop(1,    '#020106');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  // Stars
  for (const s of STARS) {
    const x = Math.floor(s.rx * canvas.width);
    const y = Math.floor(s.ry * canvas.height);
    const tw = 0.5 + 0.5 * Math.sin(now * 0.002 + s.twinkle);
    ctx.globalAlpha = 0.25 + tw * 0.7;
    ctx.fillStyle = s.warm ? '#fde6a5' : '#dcd2ff';
    ctx.fillRect(x, y, s.size, s.size);
  }
  ctx.globalAlpha = 1;

  // Moon with halo
  const moonR = Math.min(canvas.width, canvas.height) * 0.045;
  const moonX = canvas.width * 0.84;
  const moonY = canvas.height * 0.15;
  const halo = ctx.createRadialGradient(moonX, moonY, moonR, moonX, moonY, moonR * 5);
  halo.addColorStop(0, 'rgba(255, 235, 180, 0.32)');
  halo.addColorStop(1, 'rgba(255, 235, 180, 0)');
  ctx.fillStyle = halo;
  ctx.fillRect(moonX - moonR * 5, moonY - moonR * 5, moonR * 10, moonR * 10);
  ctx.fillStyle = '#f5ebcc';
  ctx.beginPath(); ctx.arc(moonX, moonY, moonR, 0, Math.PI * 2); ctx.fill();
  ctx.fillStyle = 'rgba(140, 120, 80, 0.4)';
  ctx.beginPath(); ctx.arc(moonX + moonR * 0.35, moonY - moonR * 0.15, moonR * 0.28, 0, Math.PI * 2); ctx.fill();

  // Layer 1 (deep): castle silhouette far behind, very faded
  const castleScale = Math.max(1.3, SCALE * 0.7);
  drawCastle(canvas.width * 0.16, canvas.height * 0.62, castleScale);

  // Layer 2 (mid-far): distant tombstone field, very faded
  ctx.save();
  ctx.globalAlpha = 0.22;
  const farTombScale = Math.max(1.1, SCALE * 0.32);
  const farTombY = canvas.height * 0.66;
  for (let i = 0; i < 12; i++) {
    const x = (i / 11) * canvas.width;
    const kind = i % 3 === 0 ? 'obelisk' : 'tomb';
    const s = SPRITES[kind];
    const [, sx, sy, w, h] = s;
    if (sheets.tileset) {
      ctx.drawImage(sheets.tileset, sx, sy, w, h,
        Math.floor(x - w * farTombScale / 2),
        Math.floor(farTombY - h * farTombScale),
        w * farTombScale, h * farTombScale);
    }
  }
  ctx.restore();

  // Layer 3: nearer tombstone silhouettes along the bottom, less faded
  if (sheets.tileset) {
    const nearTombScale = Math.max(1.6, SCALE * 0.5);
    const nearTombY = canvas.height - 4;
    ctx.save();
    ctx.globalAlpha = 0.42;
    const tombs = [
      { x: canvas.width * 0.04, k: 'obelisk' },
      { x: canvas.width * 0.14, k: 'tomb'    },
      { x: canvas.width * 0.27, k: 'obelisk' },
      { x: canvas.width * 0.40, k: 'tomb'    },
      { x: canvas.width * 0.55, k: 'obelisk' },
      { x: canvas.width * 0.66, k: 'tomb'    },
      { x: canvas.width * 0.80, k: 'obelisk' },
      { x: canvas.width * 0.94, k: 'tomb'    },
    ];
    for (const t of tombs) {
      const s = SPRITES[t.k];
      const [, sx, sy, w, h] = s;
      ctx.drawImage(sheets.tileset, sx, sy, w, h,
        Math.floor(t.x - w * nearTombScale / 2),
        Math.floor(nearTombY - h * nearTombScale),
        w * nearTombScale, h * nearTombScale);
    }
    ctx.restore();
  }

  // Layer 4 (front): big dead trees flanking
  if (sheets.tileset) {
    const treeScale = Math.max(2, SCALE * 0.85);
    const treeW = 80 * treeScale;
    const treeH = 80 * treeScale;
    const mazeBottomY = offsetY + MAZE_H * SCALE;
    const treeY = mazeBottomY - treeH * 0.92;
    ctx.drawImage(sheets.tileset, 192, 752, 80, 80,
      Math.floor(offsetX - treeW * 0.55), Math.floor(treeY), treeW, treeH);
    ctx.save();
    ctx.translate(offsetX + MAZE_W * SCALE + treeW * 0.55, treeY);
    ctx.scale(-1, 1);
    ctx.drawImage(sheets.tileset, 192, 752, 80, 80, 0, 0, treeW, treeH);
    ctx.restore();
  }

  // Drifting mist clouds
  for (const m of MIST) {
    const x = (((m.rx0 + now * m.speed) % 1.4) - 0.2) * canvas.width;
    const y = m.ry * canvas.height;
    const w = m.w * canvas.width;
    const h = m.h * canvas.height;
    ctx.fillStyle = `rgba(190, 190, 230, ${m.alpha})`;
    ctx.beginPath();
    ctx.ellipse(x, y, w / 2, h / 2, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  // Ground fog gradient
  const fog = ctx.createLinearGradient(0, canvas.height * 0.7, 0, canvas.height);
  fog.addColorStop(0, 'rgba(30, 16, 50, 0)');
  fog.addColorStop(1, 'rgba(60, 30, 80, 0.55)');
  ctx.fillStyle = fog;
  ctx.fillRect(0, canvas.height * 0.7, canvas.width, canvas.height * 0.3);
}

// --- main loop -----------------------------------------------------------
let lastT = 0;
function tick(now) {
  const dt = Math.min(0.05, (now - lastT) / 1000);
  lastT = now;

  if (!Dialog.isOpen() && !gameOver) {
    updateEntity(player, PLAYER_TPS, dt, decidePlayerDir);
    const ghostSpeed = isPoweredUp(now) ? SCARED_TPS : GHOST_TPS;
    for (const g of ghosts) if (g.alive) updateEntity(g, ghostSpeed, dt, decideGhostDir);
    checkPowerupPickup();
    checkGhostCollision(now);
  }
  Dialog.tick(now);

  render(now);
  requestAnimationFrame(tick);
}

function render(now) {
  renderBackground(now);

  ctx.save();
  ctx.translate(offsetX, offsetY);
  ctx.scale(SCALE, SCALE);

  // Maze floor
  ctx.fillStyle = '#15101e';
  ctx.fillRect(0, 0, MAZE_W, MAZE_H);
  ctx.fillStyle = 'rgba(255, 255, 255, 0.015)';
  for (let r = 1; r < ROWS - 1; r++) {
    for (let c = 1; c < COLS - 1; c++) {
      if (MAZE[r][c] === '.' && (c + r) % 2 === 0) {
        ctx.fillRect(c * TILE, r * TILE, TILE, TILE);
      }
    }
  }

  // Maze walls
  for (let r = 0; r < ROWS; r++) {
    for (let c = 0; c < COLS; c++) {
      if (MAZE[r][c] === '#') drawSprite('brick', c * TILE, r * TILE);
    }
  }

  // Tomb markers (caught projects)
  for (const m of tombMarkers) drawSprite('tomb', m.col * TILE, m.row * TILE - 16);

  // Power-ups (above floor, below entities)
  for (const pu of powerups) if (!pu.consumed) drawPowerup(pu, now);

  // Ghosts (scared if powered up)
  const scared = isPoweredUp(now);
  for (const g of ghosts) if (g.alive) drawGhostEntity(g, now, scared);

  // Player pacman
  drawPacman(player, now);

  ctx.restore();

  // Screen-space text overlays
  for (const g of ghosts) if (g.alive) drawGhostLabel(g);

  // Power-up timer indicator
  if (isPoweredUp(now)) {
    const left = powerTimeLeft(now) / 1000;
    ctx.save();
    ctx.font = `700 14px "Special Elite", ui-monospace, monospace`;
    ctx.textAlign = 'center';
    ctx.fillStyle = '#fde6a5';
    ctx.shadowColor = 'rgba(0,0,0,0.85)';
    ctx.shadowBlur = 4;
    ctx.fillText(`POWER · ${left.toFixed(1)}s`, canvas.width / 2, canvas.height - 18);
    ctx.restore();
  }

  // Vignette
  const vg = ctx.createRadialGradient(
    canvas.width / 2, canvas.height / 2, Math.min(canvas.width, canvas.height) * 0.4,
    canvas.width / 2, canvas.height / 2, Math.max(canvas.width, canvas.height) * 0.7
  );
  vg.addColorStop(0, 'rgba(0,0,0,0)');
  vg.addColorStop(1, 'rgba(0,0,0,0.6)');
  ctx.fillStyle = vg;
  ctx.fillRect(0, 0, canvas.width, canvas.height);

  if (gameOver) drawGameOver(now);
}

function drawGameOver(now) {
  ctx.fillStyle = 'rgba(8, 4, 20, 0.78)';
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.save();
  ctx.textAlign = 'center';
  ctx.shadowColor = 'rgba(0,0,0,0.85)';
  ctx.shadowBlur = 6;
  ctx.font = `700 ${Math.floor(Math.min(canvas.width, canvas.height) * 0.075)}px "Creepster", "Special Elite", monospace`;
  ctx.fillStyle = '#e74c3c';
  ctx.fillText('GAME OVER', canvas.width / 2, canvas.height / 2 - 24);
  ctx.font = `700 ${Math.floor(Math.min(canvas.width, canvas.height) * 0.022)}px "Special Elite", monospace`;
  ctx.fillStyle = '#ece2c4';
  ctx.fillText('An unlaid soul caught you.', canvas.width / 2, canvas.height / 2 + 14);
  ctx.fillStyle = '#c9b87a';
  const blink = 0.5 + 0.5 * Math.sin(now * 0.005);
  ctx.globalAlpha = 0.5 + blink * 0.5;
  ctx.fillText('Press R to try again', canvas.width / 2, canvas.height / 2 + 48);
  ctx.restore();
}

window.__gv = { player, ghosts, powerups, tombMarkers, isPoweredUp, MAZE, isGameOver: () => gameOver };

(async () => {
  try {
    await Promise.all([
      loadImage('tileset',    './assets/sprites/tileset.png'),
      loadImage('puChatgpt',  './assets/sprites/powerup-chatgpt.png'),
      loadImage('puGemini',   './assets/sprites/powerup-gemini.png'),
      loadImage('puClaude',   './assets/sprites/powerup-claude.png'),
    ]);
    updateHud();
    loaderEl.classList.add('hidden');
    for (const g of ghosts) startStep(g, 'left');
    requestAnimationFrame(tick);
  } catch (err) {
    console.error('asset load failed', err);
    loaderEl.querySelector('.glow').textContent = 'failed to load — check console';
  }
})();
