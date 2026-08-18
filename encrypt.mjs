// Encrypts every page JPEG with AES-256-GCM for the static (GitHub Pages) build.
// Usage: SITE_PASSPHRASE="user:pass" node encrypt.mjs <srcPagesDir> <dstEncDir> <manifestPath>
// Output file layout: iv(12) || ciphertext || gcmTag(16)  — matches WebCrypto decrypt.
import { readdirSync, readFileSync, writeFileSync, mkdirSync } from "fs";
import { join } from "path";
import { pbkdf2Sync, randomBytes, createCipheriv } from "crypto";

const [, , srcDir, dstDir, manifestPath] = process.argv;
const passphrase = process.env.SITE_PASSPHRASE;
if (!passphrase || !srcDir || !dstDir || !manifestPath) {
  console.error("usage: SITE_PASSPHRASE=user:pass node encrypt.mjs <src> <dst> <manifest>");
  process.exit(1);
}

const ITER = 210000;
const CHECK_TEXT = "renal-guidelines-ok";
const salt = randomBytes(16);
const key = pbkdf2Sync(passphrase, salt, ITER, 32, "sha256");

function enc(buf) {
  const iv = randomBytes(12);
  const c = createCipheriv("aes-256-gcm", key, iv);
  return Buffer.concat([iv, c.update(buf), c.final(), c.getAuthTag()]);
}

let n = 0;
for (const slug of readdirSync(srcDir).filter((d) => !d.startsWith("."))) {
  mkdirSync(join(dstDir, slug), { recursive: true });
  for (const f of readdirSync(join(srcDir, slug)).filter((f) => f.endsWith(".jpg"))) {
    writeFileSync(join(dstDir, slug, f.replace(/\.jpg$/, ".bin")), enc(readFileSync(join(srcDir, slug, f))));
    n++;
  }
}

writeFileSync(
  manifestPath,
  JSON.stringify({
    v: 1,
    iter: ITER,
    salt: salt.toString("base64"),
    check: enc(Buffer.from(CHECK_TEXT)).toString("base64"),
  })
);
console.log(`encrypted ${n} pages`);
