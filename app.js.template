// Client-side gate + decryption for the encrypted static build.
// Loaded on every page as: <script src="{root}/assets/app.js" data-root="{root}" defer></script>
const ROOT = document.currentScript ? document.currentScript.dataset.root || "." : ".";
const STORE = "rg-key-v1";
const CHECK_TEXT = "renal-guidelines-ok";

let aesKey = null;
let manifestPromise = null;

const b64dec = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const b64enc = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));

function getManifest() {
  if (!manifestPromise) {
    manifestPromise = fetch(`${ROOT}/assets/manifest.json`).then((r) => r.json());
  }
  return manifestPromise;
}

async function deriveKey(user, pass) {
  const m = await getManifest();
  const base = await crypto.subtle.importKey(
    "raw", new TextEncoder().encode(`${user}:${pass}`), "PBKDF2", false, ["deriveKey"]);
  return crypto.subtle.deriveKey(
    { name: "PBKDF2", hash: "SHA-256", salt: b64dec(m.salt), iterations: m.iter },
    base, { name: "AES-GCM", length: 256 }, true, ["decrypt"]);
}

async function decryptWith(key, bytes) {
  return crypto.subtle.decrypt({ name: "AES-GCM", iv: bytes.slice(0, 12) }, key, bytes.slice(12));
}

async function verify(key) {
  try {
    const m = await getManifest();
    const pt = await decryptWith(key, b64dec(m.check));
    return new TextDecoder().decode(pt) === CHECK_TEXT;
  } catch {
    return false;
  }
}

function setLocked(locked) {
  document.body.classList.toggle("locked", locked);
  const lockLink = document.querySelector(".lock-link");
  if (lockLink) lockLink.hidden = locked;
}

// ---- study chapters (encrypted HTML fragments) ----
async function startStudy() {
  const target = document.getElementById("study-body");
  const src = document.body.dataset.study;
  if (!target || !src || !aesKey || target.dataset.done) return;
  target.dataset.done = "1";
  try {
    const buf = await (await fetch(src)).arrayBuffer();
    const pt = await decryptWith(aesKey, new Uint8Array(buf));
    target.innerHTML = new TextDecoder().decode(pt);
    if (window.initQuizLite) window.initQuizLite(target);
    startImages();
  } catch {
    delete target.dataset.done;
  }
}

async function unlockWith(user, pass) {
  const key = await deriveKey(user, pass);
  if (!(await verify(key))) return false;
  aesKey = key;
  try {
    const raw = await crypto.subtle.exportKey("raw", key);
    localStorage.setItem(STORE, b64enc(raw));
  } catch { /* private browsing — session only */ }
  setLocked(false);
  startImages();
  startStudy();
  return true;
}
window.renalUnlock = unlockWith; // used by the form and by tests

function lock() {
  localStorage.removeItem(STORE);
  location.reload();
}

// ---- image decryption ----
async function decryptImg(img) {
  if (!aesKey || img.dataset.done) return;
  img.dataset.done = "1";
  try {
    const buf = await (await fetch(img.dataset.enc)).arrayBuffer();
    const pt = await decryptWith(aesKey, new Uint8Array(buf));
    img.src = URL.createObjectURL(new Blob([pt], { type: "image/jpeg" }));
    img.classList.remove("pending");
  } catch {
    delete img.dataset.done;
  }
}

function pendingImgs() {
  return [...document.querySelectorAll("img[data-enc]:not([data-done])")];
}

function startImages() {
  const imgs = pendingImgs();
  if (!imgs.length) return;
  const io = new IntersectionObserver(
    (entries) => entries.forEach((e) => e.isIntersecting && decryptImg(e.target)),
    { rootMargin: "1500px 0px" });
  imgs.forEach((img) => io.observe(img));
  const btn = document.querySelector(".load-all");
  if (btn) {
    btn.hidden = false;
    btn.addEventListener("click", () => { btn.hidden = true; pendingImgs().forEach(decryptImg); });
  }
  addEventListener("beforeprint", () => pendingImgs().forEach(decryptImg));
}

// ---- init ----
async function init() {
  if (!window.crypto || !crypto.subtle) return; // gate stays up with its noscript-ish message
  const form = document.getElementById("gate-form");
  if (form) {
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const err = document.getElementById("gate-err");
      err.hidden = true;
      const ok = await unlockWith(form.u.value.trim(), form.p.value);
      if (!ok) err.hidden = false;
    });
  }
  const lockLink = document.querySelector(".lock-link");
  if (lockLink) lockLink.addEventListener("click", (e) => { e.preventDefault(); lock(); });

  const stored = localStorage.getItem(STORE);
  if (stored) {
    try {
      const key = await crypto.subtle.importKey("raw", b64dec(stored), "AES-GCM", true, ["decrypt"]);
      if (await verify(key)) {
        aesKey = key;
        setLocked(false);
        startImages();
        startStudy();
        return;
      }
    } catch { /* fall through to gate */ }
    localStorage.removeItem(STORE);
  }
}
init();
