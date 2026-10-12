// Simulador Krux: page controller (launcher, device, panels).
import { createShared, Ctrl, C, KEY, INBOX_BYTES } from "./shared.js";
import * as storage from "./storage.js";
import { CameraFeed } from "./camera.js";
import { zipSync, unzipSync } from "./vendor/fflate.js";

const $ = (sel) => document.querySelector(sel);
const app = $("#app");

const LANG_NAMES = {
  "en-US": "English", "de-DE": "Deutsch", "es-MX": "Español", "fr-FR": "Français",
  "ja-JP": "日本語", "ko-KR": "한국어", "nl-NL": "Nederlands", "pt-BR": "Português (Brasil)",
  "ru-RU": "Русский", "tr-TR": "Türkçe", "vi-VN": "Tiếng Việt", "zh-CN": "中文",
};
const KEEP_LANG = "";

const state = {
  index: null,
  manifest: null,
  version: null,
  device: null,
  lang: null,
  worker: null,
  shared: null,
  ctrl: null,
  lastFrame: -1,
  lcdW: 320,
  lcdH: 480,
  pendingReboot: false,
  shutdown: false,
  crashed: false,
  running: false,
  folder: null, // FileSystemDirectoryHandle mirroring the SD card
};

const remember = {
  get(k) { try { return localStorage.getItem("krux-web:" + k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem("krux-web:" + k, v); } catch { /* private mode */ } },
};

// ------------------------------------------------------------------ helpers

let toastTimer = 0;
function toast(text, ms = 2600) {
  const t = $("#toast");
  t.textContent = text;
  t.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => (t.hidden = true), ms);
}

function fmtSize(n) {
  if (n < 1024) return n + " B";
  if (n < 1024 * 1024) return (n / 1024).toFixed(n < 10240 ? 1 : 0).replace(".", ",") + " KB";
  return (n / 1024 / 1024).toFixed(1).replace(".", ",") + " MB";
}

function download(name, blob) {
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = name;
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 4000);
}

async function getJSON(url) {
  const r = await fetch(url, { cache: "no-cache" });
  if (!r.ok) throw new Error(`${r.status} ao baixar ${url}`);
  return r.json();
}

// Two-step confirmation for destructive buttons (no blocking dialogs).
function armed(btn, label, action) {
  const original = btn.textContent;
  btn.addEventListener("click", async () => {
    if (!btn.classList.contains("armed")) {
      btn.classList.add("armed");
      btn.textContent = label;
      setTimeout(() => { btn.classList.remove("armed"); btn.textContent = original; }, 3500);
      return;
    }
    btn.classList.remove("armed");
    btn.textContent = original;
    await action();
  });
}

// ----------------------------------------------------------------- launcher

async function loadIndex() {
  state.index = await getJSON("versions/index.json");
  const sel = $("#sel-version");
  sel.innerHTML = "";
  for (const v of state.index.versions) {
    const o = document.createElement("option");
    o.value = v.tag;
    o.textContent = v.tag === state.index.default ? `${v.tag} (mais recente)` : v.tag;
    sel.append(o);
  }
}

async function loadManifest(tag) {
  state.manifest = await getJSON(`versions/${tag}/manifest.json`);
  const dsel = $("#sel-device");
  dsel.innerHTML = "";
  for (const d of state.manifest.devices) {
    const o = document.createElement("option");
    o.value = d.id;
    o.textContent = d.name;
    dsel.append(o);
  }
  const lsel = $("#sel-lang");
  lsel.innerHTML = "";
  const keep = document.createElement("option");
  keep.value = KEEP_LANG;
  keep.textContent = "Manter o que estiver salvo";
  lsel.append(keep);
  for (const code of state.manifest.languages) {
    const o = document.createElement("option");
    o.value = code;
    o.textContent = LANG_NAMES[code] || code;
    lsel.append(o);
  }
}

function deviceInfo(id) {
  return state.manifest.devices.find((d) => d.id === id);
}

async function initLauncher() {
  await loadIndex();
  const params = new URLSearchParams(location.search);
  const wantV = params.get("v");
  const known = (t) => state.index.versions.some((v) => v.tag === t);
  const version = known(wantV) ? wantV : known(remember.get("version")) ? remember.get("version") : state.index.default;
  $("#sel-version").value = version;
  await loadManifest(version);

  const wantD = params.get("device");
  const devId = (id) => (id && !id.startsWith("maixpy_") ? "maixpy_" + id : id);
  const device = deviceInfo(devId(wantD)) ? devId(wantD)
    : deviceInfo(remember.get("device")) ? remember.get("device") : state.manifest.default_device;
  $("#sel-device").value = device;

  const wantL = params.get("lang");
  const langs = state.manifest.languages;
  const matchLang = (l) => l && langs.find((x) => x.toLowerCase() === l.toLowerCase() || x.slice(0, 2) === l.toLowerCase());
  const saved = remember.get("lang");
  $("#sel-lang").value = matchLang(wantL) || (saved !== null ? saved : "pt-BR");

  $("#sel-version").addEventListener("change", async (e) => {
    const dev = $("#sel-device").value, lang = $("#sel-lang").value;
    await loadManifest(e.target.value);
    if (deviceInfo(dev)) $("#sel-device").value = dev;
    $("#sel-lang").value = langs.includes(lang) || lang === KEEP_LANG ? lang : "pt-BR";
  });
  $("#launcher").addEventListener("submit", (e) => {
    e.preventDefault();
    start($("#sel-version").value, $("#sel-device").value, $("#sel-lang").value);
  });

  if (wantV || wantD) start($("#sel-version").value, $("#sel-device").value, $("#sel-lang").value);
}

function configURL() {
  const u = new URL(location.href);
  u.search = "";
  u.searchParams.set("v", state.version);
  u.searchParams.set("device", state.device.replace("maixpy_", ""));
  if (state.lang) u.searchParams.set("lang", state.lang);
  return u.toString();
}

async function start(version, device, lang) {
  if (version !== state.manifest.version) await loadManifest(version);
  state.version = version;
  state.device = device;
  state.lang = lang;
  remember.set("version", version);
  remember.set("device", device);
  remember.set("lang", lang);
  history.replaceState(null, "", configURL());

  const info = deviceInfo(device);
  $("#session-label").textContent = `Krux ${version} no ${info.name}`;
  document.title = `Krux ${version}, ${info.name}`;
  app.dataset.view = "sim";
  $("#launcher").hidden = true;
  $("#stage-wrap").hidden = false;
  $("#panel").hidden = false;
  $("#keys-hint").hidden = false;
  setupStage(info);
  await refreshSD();
  state.applyLang = true; // only on this first boot: later reboots keep what Krux saved
  boot();
}

function backToLauncher() {
  stopWorker();
  exitPresent();
  app.dataset.view = "launcher";
  $("#launcher").hidden = false;
  $("#stage-wrap").hidden = true;
  $("#panel").hidden = true;
  $("#keys-hint").hidden = true;
  $("#session-label").textContent = "";
  history.replaceState(null, "", location.pathname);
  document.title = "Simulador Krux";
}

// -------------------------------------------------------------------- stage

const lcd = $("#lcd");
const lctx = lcd.getContext("2d");
let imageData = null;

function setupStage(info) {
  const [W, H] = info.window;
  const stage = $("#stage");
  stage.style.width = W + "px";
  stage.style.height = H + "px";
  const img = $("#device-img");
  if (info.image) {
    img.hidden = false;
    img.src = `versions/${state.version}/${info.image}`;
    img.onload = () => {
      img.style.left = (W - img.naturalWidth) / 2 + "px";
      img.style.top = (H - img.naturalHeight) / 2 + "px";
    };
  } else {
    img.hidden = true;
  }
  placeLCD(320, 480);
  fitStage();
}

function placeLCD(w, h) {
  state.lcdW = w;
  state.lcdH = h;
  const stage = $("#stage");
  const W = parseInt(stage.style.width), H = parseInt(stage.style.height);
  if (lcd.width !== w || lcd.height !== h) {
    lcd.width = w;
    lcd.height = h;
  }
  imageData = lctx.createImageData(w, h);
  for (const el of [lcd, $("#overlay")]) {
    el.style.left = Math.floor((W - w) / 2) + "px";
    el.style.top = Math.floor((H - h) / 2) + "px";
    el.style.width = w + "px";
    el.style.height = h + "px";
  }
  // Black behind the screen opening of the device picture (it is a little
  // larger than the LCD), like the black window of the desktop simulator.
  const bed = $("#screen-bed"), pad = 14;
  bed.style.left = Math.floor((W - w) / 2) - pad + "px";
  bed.style.top = Math.floor((H - h) / 2) - pad + "px";
  bed.style.width = w + 2 * pad + "px";
  bed.style.height = h + 2 * pad + "px";
}

function fitStage() {
  const stage = $("#stage");
  const wrap = $("#stage-wrap");
  if (!stage.style.width || wrap.hidden) return;
  const W = parseInt(stage.style.width), H = parseInt(stage.style.height);
  const availW = wrap.clientWidth, availH = wrap.clientHeight;
  if (!availW || !availH) return;
  const max = app.classList.contains("present") ? 3 : 1.5;
  const s = Math.max(0.25, Math.min(availW / W, availH / H, max));
  stage.style.setProperty("--s", s.toFixed(4));
}
new ResizeObserver(fitStage).observe($("#stage-wrap"));
window.addEventListener("resize", fitStage);

function render() {
  requestAnimationFrame(render);
  const ctrl = state.ctrl;
  if (!ctrl) return;
  const seq = ctrl.get(C.FRAME_SEQ);
  if (seq === state.lastFrame) return;
  state.lastFrame = seq;
  const w = ctrl.get(C.LCD_W), h = ctrl.get(C.LCD_H);
  if (!w || !h) return;
  if (w !== state.lcdW || h !== state.lcdH || !imageData) placeLCD(w, h);
  imageData.data.set(new Uint8Array(state.shared.fb, 0, w * h * 4));
  lctx.putImageData(imageData, 0, 0);
  if (state.booting) {
    state.booting = false;
    hideOverlay();
  }
}
requestAnimationFrame(render);
window.__krux = state; // for debugging and tests

// ------------------------------------------------------------------ overlay

function showOverlay(text, { spinner = false, detail = null, button = null, action = null } = {}) {
  const o = $("#overlay");
  o.hidden = false;
  const t = $("#overlay-text");
  t.textContent = text;
  o.querySelector(".spinner")?.remove();
  if (spinner) {
    const s = document.createElement("div");
    s.className = "spinner";
    o.prepend(s);
  }
  const d = $("#overlay-detail");
  d.hidden = !detail;
  d.textContent = detail || "";
  const b = $("#overlay-btn");
  b.hidden = !button;
  b.textContent = button || "";
  b.onclick = action;
}
function hideOverlay() {
  $("#overlay").hidden = true;
}

// ------------------------------------------------------------------- worker

function stopWorker() {
  if (state.worker) state.worker.terminate();
  state.worker = null;
  state.running = false;
  if (state.ctrl) state.ctrl.set(C.CAM_ON, 0);
  state.ctrl = null;
}

function applyLanguage(files, lang) {
  if (!lang) return files;
  const enc = new TextEncoder(), dec = new TextDecoder();
  let touched = false;
  const out = files.map((f) => {
    if (f.path !== "flash/settings.json" && f.path !== "sd/settings.json") return f;
    try {
      const j = JSON.parse(dec.decode(f.data));
      j.settings = j.settings || {};
      j.settings.i18n = j.settings.i18n || {};
      j.settings.i18n.locale = lang;
      touched = true;
      return { path: f.path, data: enc.encode(JSON.stringify(j)) };
    } catch {
      return f;
    }
  });
  if (!touched) {
    out.push({ path: "flash/settings.json", data: enc.encode(JSON.stringify({ settings: { i18n: { locale: lang } } })) });
  }
  return out;
}

const STEPS = { python: "Carregando o Python…", krux: "Carregando a Krux…", boot: "Ligando…" };

async function boot() {
  stopWorker();
  state.pendingReboot = false;
  state.shutdown = false;
  state.crashed = false;
  state.lastFrame = -1;
  state.booting = true;
  showOverlay(STEPS.python, { spinner: true });
  lctx.fillStyle = "#000";
  lctx.fillRect(0, 0, lcd.width, lcd.height);

  const shared = createShared();
  state.shared = shared;
  state.ctrl = new Ctrl(shared);
  camera.attach({ ctrl: state.ctrl, shared });

  let files = await storage.filesFor(state.device);
  if (state.applyLang) files = applyLanguage(files, state.lang);
  state.applyLang = false;

  const worker = new Worker(new URL("./worker.js", import.meta.url), { type: "module" });
  state.worker = worker;
  state.running = true;
  worker.onmessage = (e) => onWorkerMessage(worker, e.data);
  worker.onerror = (e) => {
    if (worker !== state.worker) return;
    showCrash(String(e.message || e));
  };
  worker.postMessage({ shared, device: state.device, version: state.version, files });
  updateCameraUI();
}

function showCrash(detail) {
  state.crashed = true;
  state.running = false;
  showOverlay("A Krux parou com um erro.", {
    detail,
    button: "Reiniciar",
    action: boot,
  });
}

const logLines = [];
function log(text) {
  logLines.push(text);
  if (logLines.length > 400) logLines.splice(0, logLines.length - 400);
  const pre = $("#log");
  pre.textContent = logLines.join("\n");
  pre.scrollTop = pre.scrollHeight;
}

async function onWorkerMessage(worker, m) {
  if (worker !== state.worker) return;
  switch (m.kind) {
    case "progress":
      if (STEPS[m.step]) showOverlay(STEPS[m.step], { spinner: true });
      break;
    case "stdout":
    case "stderr":
      log(m.text);
      break;
    case "camera":
      updateCameraUI();
      break;
    case "file":
      await storage.putFile(state.device, m.path, m.data);
      if (m.path.startsWith("sd/")) {
        await mirrorWrite(m.path.slice(3), m.data);
        refreshSD();
      }
      break;
    case "fs-delete":
      await storage.deleteFile(state.device, m.path);
      if (m.path.startsWith("sd/")) {
        await mirrorDelete(m.path.slice(3));
        refreshSD();
      }
      break;
    case "reset":
      if (m.shutdown) state.shutdown = true;
      else state.pendingReboot = true;
      break;
    case "crash":
      log(m.traceback);
      showCrash(m.traceback);
      break;
    case "exited":
      state.running = false;
      updateCameraUI();
      if (state.crashed) break;
      if (state.pendingReboot) {
        boot();
      } else {
        showOverlay("A Krux foi desligada.", { button: "Ligar", action: boot });
      }
      break;
  }
}

// -------------------------------------------------------------------- input

function lcdPoint(e) {
  const r = lcd.getBoundingClientRect();
  const x = Math.floor(((e.clientX - r.left) / r.width) * state.lcdW);
  const y = Math.floor(((e.clientY - r.top) / r.height) * state.lcdH);
  return [x, y];
}

lcd.addEventListener("pointerdown", (e) => {
  const ctrl = state.ctrl;
  if (!ctrl || !state.running) return;
  e.preventDefault();
  lcd.focus({ preventScroll: true });
  lcd.setPointerCapture(e.pointerId);
  const [x, y] = lcdPoint(e);
  ctrl.set(C.MOUSE_X, x);
  ctrl.set(C.MOUSE_Y, y);
  ctrl.set(C.TOUCH_X, x);
  ctrl.set(C.TOUCH_Y, y);
  ctrl.set(C.MOUSE_DOWN, 1);
  ctrl.add(C.EV_TOUCH);
  ctrl.wake();
});
lcd.addEventListener("pointermove", (e) => {
  const ctrl = state.ctrl;
  if (!ctrl || !ctrl.get(C.MOUSE_DOWN)) return;
  const [x, y] = lcdPoint(e);
  ctrl.set(C.MOUSE_X, x);
  ctrl.set(C.MOUSE_Y, y);
});
const release = () => {
  const ctrl = state.ctrl;
  if (!ctrl) return;
  ctrl.set(C.MOUSE_DOWN, 0);
  ctrl.wake();
};
lcd.addEventListener("pointerup", release);
lcd.addEventListener("pointercancel", release);

const EVENT_FOR = { ENTER: C.EV_ENTER, DOWN: C.EV_PAGE, UP: C.EV_PREV };
function keyDown(name) {
  const ctrl = state.ctrl;
  if (!ctrl || !state.running) return;
  Atomics.or(ctrl.i32, C.KEYS, KEY[name]);
  ctrl.add(EVENT_FOR[name]);
  ctrl.wake();
  document.querySelector(`.hw[data-key="${name}"]`)?.classList.add("down");
}
function keyUp(name) {
  const ctrl = state.ctrl;
  document.querySelector(`.hw[data-key="${name}"]`)?.classList.remove("down");
  if (!ctrl) return;
  Atomics.and(ctrl.i32, C.KEYS, ~KEY[name]);
  ctrl.wake();
}

const KEYMAP = { Enter: "ENTER", ArrowDown: "DOWN", ArrowUp: "UP" };
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && app.classList.contains("present")) return exitPresent();
  if (app.dataset.view !== "sim") return;
  const t = e.target;
  if (t.closest && t.closest("input, select, textarea")) return;
  if (e.key === "Enter" && t.closest && t.closest("button, summary, a")) return;
  const name = KEYMAP[e.key];
  if (!name) return;
  e.preventDefault();
  if (!e.repeat) keyDown(name);
});
document.addEventListener("keyup", (e) => {
  const name = KEYMAP[e.key];
  if (name) keyUp(name);
});
for (const b of document.querySelectorAll(".hw")) {
  b.addEventListener("pointerdown", (e) => { e.preventDefault(); b.setPointerCapture(e.pointerId); keyDown(b.dataset.key); });
  b.addEventListener("pointerup", () => keyUp(b.dataset.key));
  b.addEventListener("pointercancel", () => keyUp(b.dataset.key));
  b.addEventListener("keydown", (e) => { if (e.key === " " || e.key === "Enter") { e.preventDefault(); if (!e.repeat) keyDown(b.dataset.key); } });
  b.addEventListener("keyup", (e) => { if (e.key === " " || e.key === "Enter") keyUp(b.dataset.key); });
}

// ------------------------------------------------------------------- camera

const camera = new CameraFeed({ preview: $("#cam-preview"), onChange: () => updateCameraUI() });
window.__cam = camera; // for debugging and tests

function updateCameraUI() {
  const wants = camera.kruxWants && state.running;
  const status = $("#cam-status");
  status.textContent = wants ? (camera.active ? "lendo" : "a Krux está esperando") : "desligada na Krux";
  status.classList.toggle("live", wants);
  $("#cam-preview-box").classList.toggle("waiting", wants && !camera.active);
  $("#cam-empty").hidden = camera.active;
  $("#cam-hint").hidden = !camera.active;
  $("#cam-actions").hidden = !camera.active;
  $("#cam-full").disabled = !camera.region;
  if (!camera.active) closePicker();
  for (const b of document.querySelectorAll(".seg-btn")) b.setAttribute("aria-pressed", String(camera.kind === b.dataset.src));
  $("#img-drop").classList.toggle("active", camera.kind === "image");
  const q = camera.lastQR;
  $("#qr-note").textContent = q ? `Último QR lido: ${q.size} bytes, às ${new Date(q.at).toLocaleTimeString("pt-BR")}` : "";
}
setInterval(updateCameraUI, 1000);

for (const b of document.querySelectorAll(".seg-btn")) {
  b.addEventListener("click", async () => {
    try {
      if (b.dataset.src === "webcam") await camera.useWebcam();
      else if (b.dataset.src === "screen") {
        await camera.useScreen();
        openPicker();
      }
    } catch (err) {
      if (err && err.name === "NotAllowedError") toast("Permissão negada. Libere o acesso no navegador e tente de novo.", 4500);
      else if (err && err.name === "NotFoundError") toast("Nenhuma câmera encontrada.");
      else toast("Não deu para abrir essa fonte: " + (err && err.message ? err.message : err), 4500);
    }
  });
}
$("#cam-file").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (f) await camera.useImage(f).catch(() => toast("Esse arquivo não é uma imagem que o navegador consiga abrir."));
});
$("#cam-full").addEventListener("click", () => camera.clearRegion());

// Large region picker (a "snipping tool" over the captured image)
const picker = $("#picker");
function openPicker() {
  if (!camera.active) return;
  picker.hidden = false;
  camera.addView($("#picker-canvas"));
  $("#picker-done").focus();
}
function closePicker() {
  if (picker.hidden) return;
  picker.hidden = true;
  camera.removeView($("#picker-canvas"));
}
$("#cam-pick").addEventListener("click", openPicker);
$("#picker-done").addEventListener("click", closePicker);
$("#picker-all").addEventListener("click", () => { camera.clearRegion(); closePicker(); });
picker.addEventListener("keydown", (e) => { if (e.key === "Escape") { e.stopPropagation(); closePicker(); } });
$("#cam-stop").addEventListener("click", () => camera.stop());
// Images as the camera source: paste, drop (files or images dragged from
// another page) or the clipboard button.
async function useImageBlob(blob, how) {
  try {
    await camera.useImage(blob);
    toast(how);
  } catch {
    toast("Esse arquivo não é uma imagem que o navegador consiga abrir.");
  }
}

async function imageFromDrop(dt) {
  const f = [...dt.files].find((x) => x.type.startsWith("image/"));
  if (f) return f;
  // An image dragged from another tab arrives as a URL
  const url = (dt.getData("text/uri-list") || "").split("\n").find((l) => l && !l.startsWith("#"))
    || (dt.getData("text/html").match(/<img[^>]+src="([^"]+)"/i) || [])[1];
  if (!url) return null;
  try {
    const r = await fetch(url, { mode: "cors" });
    const b = await r.blob();
    return b.type.startsWith("image/") ? b : null;
  } catch {
    toast("Não consegui pegar essa imagem do outro site. Copie a imagem (botão direito, Copiar imagem) e cole aqui.", 6000);
    return null;
  }
}

function dropTarget(el, overEl = el) {
  el.addEventListener("dragover", (e) => { e.preventDefault(); e.stopPropagation(); overEl.classList.add("over"); });
  el.addEventListener("dragleave", () => overEl.classList.remove("over"));
  el.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    overEl.classList.remove("over");
    const img = await imageFromDrop(e.dataTransfer);
    if (img) await useImageBlob(img, "Imagem carregada como fonte da câmera.");
  });
}
dropTarget($("#img-drop"));
dropTarget($("#cam-preview-box"), $("#img-drop"));
dropTarget($("#picker-canvas"), picker);

document.addEventListener("paste", async (e) => {
  if (app.dataset.view !== "sim") return;
  if (e.target.closest && e.target.closest("input, textarea")) return;
  const item = [...(e.clipboardData?.items || [])].find((i) => i.type.startsWith("image/"));
  if (!item) {
    if ([...(e.clipboardData?.items || [])].length) toast("A área de transferência não tem uma imagem. Copie a imagem do QR (não o link) e cole de novo.", 5000);
    return;
  }
  e.preventDefault();
  await useImageBlob(item.getAsFile(), "Imagem colada como fonte da câmera.");
});

$("#img-paste").addEventListener("click", async () => {
  if (!navigator.clipboard || !navigator.clipboard.read) {
    return toast("Este navegador não deixa o botão ler a área de transferência. Use Ctrl+V.", 5000);
  }
  try {
    for (const item of await navigator.clipboard.read()) {
      const type = item.types.find((t) => t.startsWith("image/"));
      if (type) return useImageBlob(await item.getType(type), "Imagem colada como fonte da câmera.");
    }
    toast("A área de transferência não tem uma imagem. Copie a imagem do QR e tente de novo.", 5000);
  } catch {
    toast("O navegador não liberou a área de transferência. Use Ctrl+V.", 5000);
  }
});
$("#img-choose").addEventListener("click", () => $("#cam-file").click());
if (/Mac|iPhone|iPad/.test(navigator.platform)) $("#paste-key").textContent = "⌘V";

// ------------------------------------------------------------------ SD card

async function refreshSD() {
  const files = await storage.sdFiles();
  const ul = $("#sd-list");
  ul.innerHTML = "";
  if (!files.length) {
    const li = document.createElement("li");
    li.className = "empty";
    li.textContent = "Cartão vazio. Adicione uma PSBT, um backup ou qualquer arquivo para a Krux ler.";
    ul.append(li);
  }
  let total = 0;
  for (const f of files) {
    total += f.data.length;
    const li = document.createElement("li");
    const name = document.createElement("span");
    name.className = "name";
    name.title = f.name;
    name.textContent = f.name;
    const size = document.createElement("span");
    size.className = "size";
    size.textContent = fmtSize(f.data.length);
    name.append(size);
    const dl = document.createElement("button");
    dl.className = "btn act";
    dl.type = "button";
    dl.textContent = "Baixar";
    dl.onclick = () => download(f.name.split("/").pop(), new Blob([f.data]));
    const rm = document.createElement("button");
    rm.className = "btn act danger";
    rm.type = "button";
    rm.textContent = "Apagar";
    rm.onclick = () => removeSDFile(f.name);
    li.append(name, dl, rm);
    ul.append(li);
  }
  $("#sd-status").textContent = files.length ? `${files.length} arquivo${files.length > 1 ? "s" : ""}, ${fmtSize(total)}` : "";
}

// Sends a file operation to the running Krux (one at a time).
const inboxQueue = [];
let inboxBusy = false;
function sendToKrux(op, path, data = new Uint8Array(0)) {
  return new Promise((resolve) => {
    inboxQueue.push({ op, path, data, resolve });
    pumpInbox();
  });
}
async function pumpInbox() {
  if (inboxBusy) return;
  inboxBusy = true;
  while (inboxQueue.length) {
    const job = inboxQueue.shift();
    const ctrl = state.ctrl;
    if (ctrl && state.running) {
      const p = new TextEncoder().encode(job.path);
      const total = 3 + p.length + job.data.length;
      if (total <= INBOX_BYTES) {
        const t0 = Date.now();
        while (ctrl.get(C.INBOX_ACK) !== ctrl.get(C.INBOX_SEQ) && Date.now() - t0 < 5000) {
          await new Promise((r) => setTimeout(r, 20));
        }
        const buf = new Uint8Array(state.shared.inbox);
        buf[0] = job.op;
        buf[1] = p.length & 0xff;
        buf[2] = p.length >> 8;
        buf.set(p, 3);
        buf.set(job.data, 3 + p.length);
        ctrl.set(C.INBOX_LEN, total);
        ctrl.add(C.INBOX_SEQ);
        ctrl.wake();
      } else {
        toast("Arquivo grande demais para enviar com a Krux ligada. Ele entra no cartão no próximo boot.", 5000);
      }
    }
    job.resolve();
  }
  inboxBusy = false;
}

async function addSDFile(name, data) {
  name = name.replace(/^\/+/, "");
  await storage.putFile(state.device, "sd/" + name, data);
  await sendToKrux(1, "sd/" + name, data);
  await mirrorWrite(name, data);
}

async function removeSDFile(name) {
  await storage.deleteFile(state.device, "sd/" + name);
  await sendToKrux(2, "sd/" + name);
  await mirrorDelete(name);
  refreshSD();
}

async function addFiles(fileList) {
  let n = 0;
  for (const f of fileList) {
    await addSDFile(f.name, new Uint8Array(await f.arrayBuffer()));
    n++;
  }
  await refreshSD();
  if (n) toast(n === 1 ? "Arquivo gravado no cartão." : `${n} arquivos gravados no cartão.`);
}

$("#sd-add").addEventListener("click", () => $("#sd-file").click());
$("#sd-file").addEventListener("change", async (e) => {
  const files = [...e.target.files];
  e.target.value = "";
  await addFiles(files);
});
$("#sd-zip").addEventListener("click", async () => {
  const files = await storage.sdFiles();
  if (!files.length) return toast("O cartão está vazio.");
  const z = {};
  for (const f of files) z[f.name] = f.data;
  download("cartao-sd-krux.zip", new Blob([zipSync(z)], { type: "application/zip" }));
});
$("#sd-import").addEventListener("click", () => $("#sd-zip-file").click());
$("#sd-zip-file").addEventListener("change", async (e) => {
  const f = e.target.files[0];
  e.target.value = "";
  if (!f) return;
  let entries;
  try {
    entries = unzipSync(new Uint8Array(await f.arrayBuffer()));
  } catch {
    return toast("Não foi possível abrir esse .zip.");
  }
  let n = 0;
  for (const [name, data] of Object.entries(entries)) {
    if (name.endsWith("/") || name.startsWith("__MACOSX")) continue;
    await addSDFile(name, data);
    n++;
  }
  await refreshSD();
  toast(`${n} arquivo${n === 1 ? "" : "s"} importado${n === 1 ? "" : "s"} para o cartão.`);
});
armed($("#sd-clear"), "Confirmar: esvaziar", async () => {
  for (const f of await storage.sdFiles()) {
    await storage.deleteFile(state.device, f.path);
    await sendToKrux(2, f.path);
    await mirrorDelete(f.name);
  }
  await refreshSD();
  toast("Cartão esvaziado.");
});

const mat = $("#mat"), panel = $("#panel");
for (const zone of [mat, $("#sd-block")]) {
  zone.addEventListener("dragover", (e) => {
    if (app.dataset.view !== "sim" || ![...e.dataTransfer.types].includes("Files")) return;
    e.preventDefault();
    panel.classList.add("dropping");
  });
  zone.addEventListener("dragleave", () => panel.classList.remove("dropping"));
  zone.addEventListener("drop", async (e) => {
    if (app.dataset.view !== "sim") return;
    e.preventDefault();
    panel.classList.remove("dropping");
    await addFiles([...e.dataTransfer.files]);
  });
}

// Real folder as the SD card (File System Access API: Chrome and Edge)
if ("showDirectoryPicker" in window) {
  $("#sd-folder").hidden = false;
  $("#sd-folder").addEventListener("click", async () => {
    if (state.folder) {
      state.folder = null;
      $("#sd-folder").textContent = "Usar uma pasta do computador";
      $("#sd-folder-note").hidden = true;
      return;
    }
    let dir;
    try {
      dir = await window.showDirectoryPicker({ id: "krux-sd", mode: "readwrite" });
    } catch {
      return;
    }
    const files = [];
    async function walk(h, prefix) {
      for await (const [name, entry] of h.entries()) {
        if (name.startsWith(".")) continue;
        if (entry.kind === "file") {
          const f = await entry.getFile();
          files.push([prefix + name, new Uint8Array(await f.arrayBuffer())]);
        } else {
          await walk(entry, prefix + name + "/");
        }
      }
    }
    await walk(dir, "");
    await storage.clearArea("sd");
    for (const [name, data] of files) await storage.putFile(state.device, "sd/" + name, data);
    state.folder = dir;
    $("#sd-folder").textContent = "Parar de usar a pasta";
    const note = $("#sd-folder-note");
    note.hidden = false;
    note.textContent = `O cartão agora espelha a pasta "${dir.name}": o que a Krux gravar aparece lá. Arquivos colocados na pasta por fora entram ao reiniciar a Krux.`;
    await refreshSD();
    toast(`Pasta "${dir.name}" carregada. Reiniciando a Krux com ela.`);
    boot();
  });
}

async function folderFor(path, create) {
  let dir = state.folder;
  const parts = path.split("/");
  for (const p of parts.slice(0, -1)) dir = await dir.getDirectoryHandle(p, { create });
  return [dir, parts[parts.length - 1]];
}
async function mirrorWrite(name, data) {
  if (!state.folder) return;
  try {
    const [dir, file] = await folderFor(name, true);
    const h = await dir.getFileHandle(file, { create: true });
    const w = await h.createWritable();
    await w.write(data);
    await w.close();
  } catch (e) {
    toast("Não consegui gravar na pasta: " + e.message, 4000);
  }
}
async function mirrorDelete(name) {
  if (!state.folder) return;
  try {
    const [dir, file] = await folderFor(name, false);
    await dir.removeEntry(file);
  } catch { /* already gone */ }
}

// ------------------------------------------------------------------ session

$("#btn-restart").addEventListener("click", boot);
$("#btn-change").addEventListener("click", backToLauncher);
$("#btn-link").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(configURL());
    toast("Link copiado. Ele abre direto nesta versão, dispositivo e idioma.");
  } catch {
    toast(configURL(), 6000);
  }
});
armed($("#btn-flash"), "Confirmar: apagar", async () => {
  await storage.clearArea("flash", state.device);
  toast("Memória interna apagada.");
  boot();
});

$("#btn-shot").addEventListener("click", () => {
  const scale = 2;
  const c = document.createElement("canvas");
  c.width = state.lcdW * scale;
  c.height = state.lcdH * scale;
  const g = c.getContext("2d");
  g.imageSmoothingEnabled = false;
  g.drawImage(lcd, 0, 0, c.width, c.height);
  const stamp = new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-");
  c.toBlob((b) => download(`krux-${state.version}-${stamp}.png`, b), "image/png");
});

function enterPresent() {
  app.classList.add("present");
  document.documentElement.requestFullscreen?.().catch(() => {});
  requestAnimationFrame(fitStage);
}
function exitPresent() {
  app.classList.remove("present");
  if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
  requestAnimationFrame(fitStage);
}
$("#btn-present").addEventListener("click", enterPresent);
$("#btn-present-exit").addEventListener("click", exitPresent);
document.addEventListener("fullscreenchange", () => {
  if (!document.fullscreenElement && app.classList.contains("present")) exitPresent();
});

// --------------------------------------------------------------------- init

if (!window.crossOriginIsolated) {
  // coi-serviceworker reloads the page once it is active; if we are still not
  // isolated after that, the page was opened in a way that can't work.
  setTimeout(() => {
    if (!window.crossOriginIsolated) $("#blocked").hidden = false;
  }, location.protocol === "file:" ? 0 : 2500);
} else {
  initLauncher().catch((e) => {
    console.error(e);
    toast("Não foi possível carregar a lista de versões: " + e.message, 8000);
  });
}
