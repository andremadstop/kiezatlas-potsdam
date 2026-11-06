// Prüfgerüst Seiten (Paket P0): index.html und karte.html per file:// und per HTTP (127.0.0.1).
// Prüft je Seite: lädt bis window.KIEZ_BEREIT, alle Themen schalten, keine Konsolenfehler (außer
// abgewiesenen Fremdabrufen), axe ohne Verstoß, Gewicht in KB gz. Dazu die Punkte aus
// pruefen/INVENTAR.md, die sich im Browser prüfen lassen (Fragen samt Scroll-Steuerung, Hash-Rundreise,
// Schaugrafik-Export SVG/PNG/PDF, Kopfzahlen, Register-Sortierung, reduzierte Bewegung).
//
// Kein Netz: Jede Anfrage, die nicht an file:// oder den eigenen Prüfserver geht (Kacheln von
// basemap.de, Luftbild-WMS der LGB), beantwortet der Browser selbst mit einem leeren 1-px-PNG.
// So entsteht kein Abruf bei fremden Diensten. (Abweisen statt Ersetzen ließ MapLibre bei manchen
// Fenstergrößen nie „load“ melden.) Erlaubt bleibt nur ERR_ABORTED bei Kacheln, die beim Weiterbewegen
// der Karte abgebrochen werden.
//
// Aufruf:  node pruefen/seiten.mjs [--wurzel <ordner>] [--json <datei>]
// Braucht: node_modules mit playwright und axe-core (im Worktree als Verweis auf das Haupt-Repo),
//          Chromium unter ~/.cache/ms-playwright. Rückgabe 0 = grün, 1 = Befund.
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath, pathToFileURL } from "node:url";

const HIER = path.dirname(fileURLToPath(import.meta.url));
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const WURZEL = path.resolve(arg("--wurzel", path.join(HIER, "..")));
const AXE = fs.readFileSync(path.join(HIER, "..", "node_modules", "axe-core", "axe.min.js"), "utf8");
const LEERBILD = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
// Grundkarte (Vektor): Kacheln und Schriften als leere Protobuf-Antwort, alles andere als leeres PNG
const fremdAntwort = (u) => /\.pbf(\?|$)/.test(u) ? { status: 200, contentType: "application/x-protobuf", body: Buffer.alloc(0) } : { status: 200, contentType: "image/png", body: LEERBILD };
const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml",
  ".png": "image/png", ".woff2": "font/woff2", ".json": "application/json" };

const befunde = [];
const bericht = { stand: new Date().toISOString(), wurzel: WURZEL, seiten: [] };
function pruef(ok, text) { console.log((ok ? "  ok   " : "  FEHLT ") + text); if (!ok) befunde.push(text); return ok; }

// ---------- Textstellen, die nicht wiederkommen dürfen (Audit 06.11.2026, berichte/audit_20261106.md)
{
  const VERBOTEN = [
    [/Höhe = Geschosse × 3 m|Höhe \(genähert\)|Geschosszahl mal 3 m\. Gemessene/, "K1: Gebäudehöhe als Geschosse × 3 m beschrieben (seit 06.11. Katasterhöhe mit Herkunft je Gebäude)"],
    [/zugeordnet über die Nummer der Denkmalliste oder/, "K2: Denkmallisten-Nummer als Zuordnungsweg genannt (nur Prüfung)"],
  ];
  const DATEIEN = ["index.html", "karte.html", "planer.html", "planer-methode.html", "planer-daten.html", "jahre.html", "jahre-methode.html",
    "jahre-daten.html", "atlas.js", "karte.js", "planer.js", "jahre.js", "themen.js", "schaugrafik.js"];
  console.log("Textstellen (Audit)");
  for (const [re, was] of VERBOTEN) {
    const treffer = DATEIEN.filter((f) => re.test(fs.readFileSync(path.join(WURZEL, f), "utf8")));
    pruef(treffer.length === 0, `${was}${treffer.length ? ": " + treffer.join(", ") : ""}`);
  }
}

// ---------- eigener Prüfserver, nur 127.0.0.1, nur Dateien unter WURZEL
const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (p !== WURZEL && !p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p.endsWith(path.sep) ? path.join(p, "index.html") : p, (f, d) => {
    if (f) { a.writeHead(404); a.end(); return; }
    a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d);
  });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const HTTP = `http://127.0.0.1:${server.address().port}/`;
const FILE = pathToFileURL(WURZEL + path.sep).href;

function eigen(url) { return url.startsWith("file://") || url.startsWith(HTTP) || url.startsWith("data:") || url.startsWith("blob:"); }
function gz(url) {
  const p = url.startsWith("file://") ? fileURLToPath(url.split(/[?#]/)[0]) : path.join(WURZEL, decodeURIComponent(new URL(url).pathname));
  try { return zlib.gzipSync(fs.readFileSync(p), { level: 9 }).length; } catch { return 0; }
}

const browser = await chromium.launch();

async function oeffnen(basis, datei, { hash = "", bewegung = "reduce", breite = 1440 } = {}) {
  const ctx = await browser.newContext({ viewport: { width: breite, height: 900 }, reducedMotion: bewegung, acceptDownloads: true });
  const page = await ctx.newPage();
  const fehler = [], abgewiesen = [], geladen = new Set();
  await page.route("**/*", (r) => {
    const u = r.request().url();
    if (eigen(u)) return r.continue();
    abgewiesen.push(u); return r.fulfill(fremdAntwort(r.request().url()));
  });
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const ort = (m.location() || {}).url || "";
    const text = m.text();
    const kachel = /ERR_ABORTED/.test(text) && (!ort || !eigen(ort));
    if (!kachel) fehler.push(text.split("\n")[0] + (ort ? " @ " + ort : ""));
  });
  page.on("pageerror", (e) => fehler.push("pageerror: " + e.message));
  page.on("request", (q) => { const u = q.url(); if (eigen(u) && !u.startsWith("data:") && !u.startsWith("blob:")) geladen.add(u.split(/[?#]/)[0]); });
  await page.goto(basis + datei + hash, { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  return { ctx, page, fehler, abgewiesen, geladen };
}

function gewicht(geladen) {
  let js = 0, alles = 0;
  for (const u of geladen) { const n = gz(u); alles += n; if (u.endsWith(".js")) js += n; }
  return { js_kb_gz: Math.round(js / 1024), alles_kb_gz: Math.round(alles / 1024) };
}

async function axe(page) {
  // Per file:// darf axe die Stylesheets nicht per XHR nachladen (CORS); die Fehlermeldung käme von
  // axe, nicht von der Seite. Dort deshalb ohne preload (betrifft nur css-orientation-lock).
  await page.addScriptTag({ content: AXE });
  const datei = page.url().startsWith("file://");
  const r = await page.evaluate(async (datei) => (await window.axe.run(document, { resultTypes: ["violations"], preload: !datei })).violations
    .map((v) => v.id + " (" + v.nodes.length + ")"), datei);
  return r;
}

async function themenSchalten(page) {
  const werte = await page.$$eval('#thema input[name="thema"]', (l) => l.map((i) => i.value));
  for (const w of werte) {
    await page.check(`#thema input[value="${w}"]`, { force: true });
    await page.waitForTimeout(300);
  }
  return werte;
}

async function startseite(basis, art) {
  console.log(`index.html über ${art}`);
  const { ctx, page, fehler, abgewiesen, geladen } = await oeffnen(basis, "index.html");
  const g = gewicht(geladen);
  const themen = await themenSchalten(page);
  pruef(themen.length === 7, `alle Themen geschaltet (${themen.length}: ${themen.join(", ")})`);
  // Kopfzahlen
  const kopf = await page.$$eval("#stadtzahlen > div dd", (l) => l.map((d) => d.textContent.trim()));
  pruef(kopf.length === 5 && kopf.every((t) => /\d/.test(t)), `Kopfzahlen: ${kopf.length} Werte (${kopf.join(" | ")})`);
  // sieben Fragen samt Scroll-Steuerung
  const fragen = await page.$$eval(".erzaehlung .frage", (l) => l.map((f) => +f.dataset.schritt));
  pruef(fragen.filter((s) => s >= 1 && s <= 7).length === 7, `sieben Fragen vorhanden (Schritte ${fragen.join(",")})`);
  let scrollOk = true;
  for (const s of [1, 3, 5, 7]) {
    await page.locator(`.frage[data-schritt="${s}"]`).scrollIntoViewIfNeeded();
    await page.evaluate((s) => document.querySelector(`.frage[data-schritt="${s}"]`).scrollIntoView({ block: "center" }), s);
    const ok = await page.waitForFunction((s) => document.querySelector(`.frage[data-schritt="${s}"]`).classList.contains("ist-aktiv"), s, { timeout: 8000 }).then(() => true, () => false);
    scrollOk = scrollOk && ok;
    if (!ok) console.log(`     Schritt ${s} wurde beim Scrollen nicht aktiv`);
  }
  pruef(scrollOk, "Scroll-Steuerung: Fragen 1, 3, 5, 7 werden beim Scrollen aktiv");
  // Register-Sortierung
  const sorten = await page.$$eval('#sortierung input[name="sort"]', (l) => l.map((i) => i.value));
  const ersteJe = {};
  for (const s of sorten) {
    await page.check(`#sortierung input[value="${s}"]`, { force: true });
    ersteJe[s] = await page.$$eval("#teile .zeile", (l) => [l.length, l[0] && l[0].dataset.nr]);
  }
  const verschieden = new Set(Object.values(ersteJe).map((x) => x[1])).size;
  pruef(Object.values(ersteJe).every((x) => x[0] === 32) && verschieden >= 3,
    `Register-Sortierung: ${sorten.length} Sortierungen, je 32 Zeilen, ${verschieden} verschiedene Spitzenreiter`);
  // Schaugrafik-Export
  await page.locator("#schaugrafik").scrollIntoViewIfNeeded();
  const [dsvg] = await Promise.all([page.waitForEvent("download", { timeout: 30000 }), page.click("#schau-svg")]);
  const svg = fs.readFileSync(await dsvg.path(), "utf8");
  pruef(/<svg[\s>]/.test(svg) && svg.length > 20000 && /@font-face/.test(svg), `Schaugrafik SVG: ${dsvg.suggestedFilename()}, ${Math.round(svg.length / 1024)} KB, Schriften eingebettet`);
  const [dpng] = await Promise.all([page.waitForEvent("download", { timeout: 60000 }), page.click("#schau-png")]);
  const png = fs.readFileSync(await dpng.path());
  pruef(png.subarray(1, 4).toString() === "PNG" && png.length > 50000, `Schaugrafik PNG: ${dpng.suggestedFilename()}, ${Math.round(png.length / 1024)} KB`);
  await page.evaluate(() => { window.__druck = 0; window.print = () => { window.__druck++; }; });
  await page.click("#schau-druck");
  await page.waitForFunction(() => window.__druck > 0, null, { timeout: 5000 });
  const druckSvg = await page.$eval("#druck", (d) => !!d.querySelector("svg"));
  const pdf = await page.pdf({ preferCSSPageSize: true });
  await page.evaluate(() => dispatchEvent(new Event("afterprint")));
  pruef(druckSvg && pdf.subarray(0, 4).toString() === "%PDF" && pdf.length > 20000, `Schaugrafik Druck/PDF: Druckblatt gesetzt, PDF ${Math.round(pdf.length / 1024)} KB`);
  const verstoss = await axe(page);
  pruef(verstoss.length === 0, `axe: ${verstoss.length} Verstöße ${verstoss.join(", ")}`);
  pruef(fehler.length === 0, `Konsole ohne Fehler (${fehler.length}${fehler.length ? ": " + fehler.slice(0, 3).join(" | ") : ""}; lokal ersetzte Fremdabrufe: ${abgewiesen.length})`);
  console.log(`  Gewicht beim Start: ${g.js_kb_gz} KB gz JS, ${g.alles_kb_gz} KB gz gesamt (eigene Dateien)`);
  bericht.seiten.push({ seite: "index.html", art, ...g, abgewiesen: abgewiesen.length, axe: verstoss.length, fehler: fehler.length });
  await ctx.close();
}

async function karte(basis, art) {
  console.log(`karte.html über ${art}`);
  const { ctx, page, fehler, abgewiesen, geladen } = await oeffnen(basis, "karte.html");
  const g = gewicht(geladen);
  const themen = await themenSchalten(page);
  pruef(themen.length === 7, `alle Themen geschaltet (${themen.length})`);
  for (const s of ["dreid", "luftbild", "gebaeude"]) { await page.check("#" + s, { force: true }); await page.waitForTimeout(300); await page.uncheck("#" + s, { force: true }); }
  const verstoss = await axe(page);
  pruef(verstoss.length === 0, `axe: ${verstoss.length} Verstöße ${verstoss.join(", ")}`);
  pruef(fehler.length === 0, `Konsole ohne Fehler (${fehler.length}${fehler.length ? ": " + fehler.slice(0, 3).join(" | ") : ""}; lokal ersetzte Fremdabrufe: ${abgewiesen.length})`);
  console.log(`  Gewicht beim Start: ${g.js_kb_gz} KB gz JS, ${g.alles_kb_gz} KB gz gesamt (eigene Dateien)`);
  bericht.seiten.push({ seite: "karte.html", art, ...g, abgewiesen: abgewiesen.length, axe: verstoss.length, fehler: fehler.length });
  await ctx.close();

  // Hash-Rundreise: Zustand setzen, laden, Hash lesen, neu laden, gleicher Zustand
  const ziel = "#thema=fern&st=52&3d=1&luft=1&geb=1&k=14.20/52.39350/13.07000/45/-12";
  const a = await oeffnen(basis, "karte.html", { hash: ziel });
  await a.page.waitForTimeout(800);
  const zustand = (p) => p.evaluate(() => ({
    thema: (document.querySelector('#thema input[name="thema"]:checked') || {}).value,
    d3: document.getElementById("dreid").checked, luft: document.getElementById("luftbild").checked,
    geb: document.getElementById("gebaeude").checked,
    hash: location.hash.replace(/&k=.*$/, ""), k: (location.hash.match(/k=([^&]*)/) || [])[1] }));
  const z1 = await zustand(a.page);
  const hash1 = await a.page.evaluate(() => location.hash);
  await a.ctx.close();
  const b = await oeffnen(basis, "karte.html", { hash: hash1 });
  await b.page.waitForTimeout(800);
  const z2 = await zustand(b.page);
  await b.ctx.close();
  const kGleich = (x, y) => { const p = (s) => (s || "").split("/").map(Number); const [a1, b1] = [p(x), p(y)]; return a1.length === 5 && a1.every((v, i) => Math.abs(v - b1[i]) < 0.01); };
  pruef(z1.thema === "q_fern" && z1.d3 && z1.luft && z1.geb && z1.hash === "#thema=fern&st=52&3d=1&luft=1&geb=1"
    && JSON.stringify({ ...z1, k: 0 }) === JSON.stringify({ ...z2, k: 0 }) && kGleich(z1.k, z2.k),
    `Hash-Rundreise: ${z1.hash}&k=${z1.k} -> neu geladen gleich (${z2.hash}&k=${z2.k})`);
}

async function bewegung() {
  // Ohne reduzierte Bewegung (GSAP, Kamerafahrten) darf ebenfalls kein Fehler auftreten
  console.log("index.html über HTTP ohne reduzierte Bewegung");
  const { ctx, page, fehler } = await oeffnen(HTTP, "index.html", { bewegung: "no-preference" });
  await page.evaluate(() => document.querySelector('.frage[data-schritt="3"]').scrollIntoView({ block: "center" }));
  await page.waitForTimeout(2500);
  const ruhig = await page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches);
  pruef(!ruhig && fehler.length === 0, `Bewegung an: Konsole ohne Fehler (${fehler.length})`);
  await ctx.close();
  const r = await oeffnen(HTTP, "index.html", { bewegung: "reduce" });
  pruef(await r.page.evaluate(() => matchMedia("(prefers-reduced-motion: reduce)").matches), "reduzierte Bewegung wird von der Seite erkannt");
  await r.ctx.close();
}

try {
  await startseite(FILE, "file://");
  await startseite(HTTP, "HTTP");
  await karte(FILE, "file://");
  await karte(HTTP, "HTTP");
  await bewegung();
} catch (e) {
  befunde.push("Abbruch: " + e.message.split("\n")[0]);
  console.log("  FEHLT Abbruch: " + e.message.split("\n")[0]);
} finally {
  await browser.close();
  server.close();
}
console.log("\nKB gz je Seite (eigene Dateien bis KIEZ_BEREIT):");
for (const s of bericht.seiten) console.log(`  ${s.seite.padEnd(11)} ${s.art.padEnd(8)} JS ${s.js_kb_gz} KB gz, gesamt ${s.alles_kb_gz} KB gz`);
bericht.befunde = befunde;
const j = arg("--json"); if (j) fs.writeFileSync(j, JSON.stringify(bericht, null, 1));
console.log(befunde.length ? `\n${befunde.length} Befund(e)` : "\ngrün");
process.exit(befunde.length ? 1 : 0);
