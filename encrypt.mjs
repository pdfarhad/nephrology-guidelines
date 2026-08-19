// Encrypts page JPEGs and study-chapter HTML fragments with AES-256-GCM for the
// static (GitHub Pages) build.
// Usage:
//   SITE_PASSPHRASE="user:pass" node encrypt.mjs <srcPagesDir> <dstEncDir> <manifestPath> [studySrcDir studyDstDir]
// Output file layout: iv(12) || ciphertext || gcmTag(16)  — matches WebCrypto decrypt.
// If the manifest already exists and the passphrase still verifies, its salt is reused
// and already-encrypted page images are left untouched (keeps git diffs small).
import { readdirSync, readFileSync, writeFileSync, mkdirSync, existsSync } from "fs";
import { join, basename } from "path";
import { pbkdf2Sync, randomBytes, createCipheriv, createDecipheriv } from "crypto";

const [, , srcDir, dstDir, manifestPath, studySrcDir, studyDstDir] = process.argv;
const passphrase = process.env.SITE_PASSPHRASE;
if (!passphrase || !srcDir || !dstDir || !manifestPath) {
  console.error("usage: SITE_PASSPHRASE=user:pass node encrypt.mjs <src> <dst> <manifest> [studySrc studyDst]");
  process.exit(1);
}

const ITER = 210000;
const CHECK_TEXT = "renal-guidelines-ok";

function verifies(key, checkB64) {
  try {
    const buf = Buffer.from(checkB64, "base64");
    const d = createDecipheriv("aes-256-gcm", key, buf.subarray(0, 12));
    d.setAuthTag(buf.subarray(buf.length - 16));
    const pt = Buffer.concat([d.update(buf.subarray(12, buf.length - 16)), d.final()]);
    return pt.toString() === CHECK_TEXT;
  } catch {
    return false;
  }
}

let salt = null, key = null, check = null, reused = false;
if (existsSync(manifestPath)) {
  const m = JSON.parse(readFileSync(manifestPath, "utf8"));
  const candidate = pbkdf2Sync(passphrase, Buffer.from(m.salt, "base64"), m.iter, 32, "sha256");
  if (verifies(candidate, m.check)) {
    salt = Buffer.from(m.salt, "base64");
    key = candidate;
    check = m.check;
    reused = true;
  }
}
if (!key) {
  salt = randomBytes(16);
  key = pbkdf2Sync(passphrase, salt, ITER, 32, "sha256");
}

function enc(buf) {
  const iv = randomBytes(12);
  const c = createCipheriv("aes-256-gcm", key, iv);
  return Buffer.concat([iv, c.update(buf), c.final(), c.getAuthTag()]);
}

let fresh = 0, kept = 0;
for (const slug of readdirSync(srcDir).filter((d) => !d.startsWith("."))) {
  mkdirSync(join(dstDir, slug), { recursive: true });
  for (const f of readdirSync(join(srcDir, slug)).filter((f) => f.endsWith(".jpg"))) {
    const out = join(dstDir, slug, f.replace(/\.jpg$/, ".bin"));
    if (reused && existsSync(out)) { kept++; continue; }
    writeFileSync(out, enc(readFileSync(join(srcDir, slug, f))));
    fresh++;
  }
}

let study = 0;
if (studySrcDir && studyDstDir) {
  mkdirSync(studyDstDir, { recursive: true });
  for (const f of readdirSync(studySrcDir).filter((f) => f.endsWith(".html"))) {
    writeFileSync(join(studyDstDir, basename(f, ".html") + ".bin"),
      enc(readFileSync(join(studySrcDir, f))));
    study++;
  }
}

writeFileSync(
  manifestPath,
  JSON.stringify({
    v: 1,
    iter: ITER,
    salt: salt.toString("base64"),
    check: check || enc(Buffer.from(CHECK_TEXT)).toString("base64"),
  })
);
console.log(`pages: ${fresh} encrypted, ${kept} unchanged · study fragments: ${study} · salt ${reused ? "reused" : "new"}`);
