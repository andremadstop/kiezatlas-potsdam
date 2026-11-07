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
  // keine Zellsäulen (07.11.): je Frage zellen-3d aus und 0 gerendert, Zellen flach (zellen-2d) und von oben
  const flach = [];
  const zellen = () => page.evaluate(() => { const m = window.KIEZ_KARTE, n = (l) => m.queryRenderedFeatures({ layers: [l] }).length;
    return { s3: m.getLayoutProperty("zellen-3d", "visibility"), n3: n("zellen-3d"), s2: m.getLayoutProperty("zellen-2d", "visibility"), n2: n("zellen-2d"), p: Math.round(m.getPitch()), t: (document.querySelector("#thema input:checked") || {}).value, y: Math.round(scrollY) }; });
  const ruhe = () => page.waitForFunction(() => !window.KIEZ_KARTE.isMoving() && window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {}).then(() => page.waitForTimeout(300));
  for (const s of [1, 3, 5, 7]) {
    await page.locator(`.frage[data-schritt="${s}"]`).scrollIntoViewIfNeeded();
    await page.evaluate((s) => document.querySelector(`.frage[data-schritt="${s}"]`).scrollIntoView({ block: "center" }), s);
    const ok = await page.waitForFunction((s) => document.querySelector(`.frage[data-schritt="${s}"]`).classList.contains("ist-aktiv"), s, { timeout: 8000 }).then(() => true, () => false);
    scrollOk = scrollOk && ok;
    if (!ok) console.log(`     Schritt ${s} wurde beim Scrollen nicht aktiv`);
    await ruhe();
    flach.push([s, await zellen()]);
  }
  pruef(scrollOk, "Scroll-Steuerung: Fragen 1, 3, 5, 7 werden beim Scrollen aktiv");
  pruef(flach.every(([, z]) => z.s3 === "none" && z.n3 === 0 && z.s2 === "visible" && z.n2 > 0 && z.p === 0),
    `keine Zellsäulen: ${flach.map(([s, z]) => `Frage ${s} zellen-3d ${z.s3}/${z.n3}, flach ${z.n2}, Neigung ${z.p}`).join("; ")}`);
  // eine flache Zelle anklicken öffnet ihr Fenster
  const punkt = await page.evaluate(() => { const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect();
    for (let y = 120; y < r.height - 80; y += 17) for (let x = 80; x < r.width - 120; x += 19) {
      if (m.queryRenderedFeatures([x, y], { layers: ["zellen-2d"] }).length && document.elementFromPoint(r.left + x, r.top + y) === m.getCanvas()) return { x: r.left + x, y: r.top + y };
    }
    return null; });
  if (punkt) { await page.mouse.click(punkt.x, punkt.y); await page.waitForTimeout(400); }
  const fenster = await page.$eval(".maplibregl-popup", (e) => e.textContent).catch(() => "");
  pruef(punkt && /Gitterzelle/.test(fenster), `Klick auf eine flache Zelle öffnet ihr Fenster (${fenster.slice(0, 40)}…)`);
  await page.evaluate(() => document.querySelectorAll(".maplibregl-popup").forEach((e) => e.remove()));
  // Gegenprobe 2 (07.11.): Doppelklick auf eine Zelle zoomt und lässt kein Fenster offen
  if (punkt) {
    const z0 = await page.evaluate(() => window.KIEZ_KARTE.getZoom());
    await page.mouse.dblclick(punkt.x, punkt.y); await page.waitForTimeout(400); await ruhe();
    const d = await page.evaluate(() => ({ z: window.KIEZ_KARTE.getZoom(), f: document.querySelectorAll(".maplibregl-popup").length }));
    pruef(d.z > z0 + 0.5 && d.f === 0, `Doppelklick auf eine Zelle: Zoom ${z0.toFixed(2)} → ${d.z.toFixed(2)}, ${d.f} Fenster offen`);
  }
  // „3D-Häuser“: Gebäude als Körper, nah heran, Zellen flach darunter, keine Säulen; aus: wieder von oben.
  // Klick auf die sichtbare Stelle des Chips: page.check scrollt die Seite erst (y 5624 → 4682) und schaltet so Frage 6 dazwischen
  const chip3d = async () => { const r = await page.evaluate(() => { const b = document.querySelector("label:has(#dreid)").getBoundingClientRect(); return { x: b.left + b.width / 2, y: b.top + b.height / 2 }; });
    await page.mouse.click(r.x, r.y); };
  await chip3d();
  await page.waitForFunction(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length > 0, null, { timeout: 20000 }).catch(() => {});
  await ruhe();
  const h3 = await page.evaluate(() => { const m = window.KIEZ_KARTE; return { n: m.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length, p: Math.round(m.getPitch()), z: m.getZoom() }; });
  const z3 = await zellen();
  // Gegenprobe 2: selbst eingeschaltet, nimmt die nächste Frage die Häuser nicht weg; sie färbt nur die Zellen
  await page.evaluate(() => document.querySelector('.frage[data-schritt="8"]').scrollIntoView({ block: "center" }));
  await page.waitForFunction(() => document.querySelector('.frage[data-schritt="8"]').classList.contains("ist-aktiv"), null, { timeout: 8000 }).catch(() => {});
  await ruhe();
  const w = await page.evaluate(() => { const m = window.KIEZ_KARTE; return { d3: document.getElementById("dreid").checked, n: m.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length,
    p: Math.round(m.getPitch()), t: (document.querySelector("#thema input:checked") || {}).value }; });
  pruef(w.d3 && w.n > 0 && w.p >= 45 && w.t === "q_u18", `Weiterlesen bei 3D-Häusern (Frage 8): 3D ${w.d3}, ${w.n} Häuser, Neigung ${w.p}, Thema ${w.t}`);
  await chip3d(); await ruhe();
  const z0 = await zellen();
  pruef(h3.n > 0 && h3.p >= 45 && h3.z >= 15.5 && z3.s3 === "none" && z3.n3 === 0 && z3.s2 === "visible" && z3.n2 > 0 && z0.p === 0 && z0.n3 === 0,
    `„3D-Häuser“: ${h3.n} Häuser, Zoom ${h3.z.toFixed(1)}, Neigung ${h3.p}, zellen-3d ${z3.s3}/${z3.n3}, flache Zellen darunter ${z3.s2}/${z3.n2} (Thema ${z3.t}, y ${z3.y}); aus: Neigung ${z0.p}`);
  // Gegenprobe 2: aus Frage 5 (Zoom 14, mitten im Stadtteil) fliegt der Schalter nah heran, statt nur zu neigen
  await page.evaluate(() => document.querySelector('.frage[data-schritt="5"]').scrollIntoView({ block: "center" }));
  await page.waitForFunction(() => document.querySelector('.frage[data-schritt="5"]').classList.contains("ist-aktiv"), null, { timeout: 8000 }).catch(() => {});
  await ruhe();
  const f5 = await page.evaluate(() => window.KIEZ_KARTE.getZoom());
  await chip3d();
  await page.waitForFunction(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length > 0, null, { timeout: 20000 }).catch(() => {});
  await ruhe();
  const h5 = await page.evaluate(() => { const m = window.KIEZ_KARTE; return { n: m.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length, z: m.getZoom() }; });
  await chip3d(); await ruhe();
  pruef(h5.z >= 15.5 && h5.n > 0, `„3D-Häuser“ aus Frage 5 (Zoom ${f5.toFixed(1)}): Zoom ${h5.z.toFixed(1)}, ${h5.n} Häuser`);
  // Gegenprobe 2: „3D-Häuser“ steht vor den Themen (auf dem Handy im ersten Bild)
  const erster = await page.$eval(".werkzeug .chip", (e) => e.innerText.trim());
  pruef(erster === "3D-Häuser", `erster Chip der Leiste: ${erster}`);
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

  // 3D = Häuser (07.11.): „3D-Häuser“ ohne Stadtteil wählt einen, lädt seine Gebäude, der Hinweis ist danach leer;
  // keine Zellsäulen. Auf dem Handy steht der Schalter ganz im Bild.
  for (const breite of [1440, 390]) {
    const c = await oeffnen(basis, "karte.html", { breite });
    const box = await c.page.locator("label:has(#dreid)").boundingBox();
    await c.page.check("#gebaeude", { force: true }); await c.page.waitForTimeout(200);
    const hin0 = await c.page.$eval("#teilen-hinweis", (e) => e.textContent);
    await c.page.check("#dreid", { force: true });
    await c.page.waitForFunction(() => { const m = window.KIEZ_KARTE; return m.loaded() && m.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length > 0; }, null, { timeout: 20000 }).catch(() => {});
    const z = await c.page.evaluate(() => { const m = window.KIEZ_KARTE; return { hin: document.getElementById("teilen-hinweis").textContent, griff: document.getElementById("griff-name").textContent,
      g3: m.getLayoutProperty("gebaeude3d", "visibility"), n: m.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length, s3: m.getLayoutProperty("zellen-3d", "visibility"), z: m.getZoom(), p: m.getPitch(), hash: location.hash.replace(/&k=.*$/, "") }; });
    pruef(/zuerst einen Stadtteil/.test(hin0) && z.hin === "" && z.griff !== "Ganz Potsdam" && z.g3 === "visible" && z.n > 0 && z.s3 === "none" && z.p >= 45 && /st=\d+&3d=1&geb=1/.test(z.hash)
      && (breite > 400 || box.x + box.width <= breite) && c.fehler.length === 0,
      `${breite} px: „3D-Häuser“ ohne Stadtteil wählt ${z.griff}, ${z.n} Häuser, Zoom ${z.z.toFixed(1)}, Neigung ${Math.round(z.p)}, Hinweis danach leer (vorher „${hin0.slice(0, 30)}…“), Schalter rechts bei ${Math.round(box.x + box.width)} px`);
    // Gegenprobe 07.11.: nah genug für Körper (Zoom 16,2 bzw. 15,6), Themen auf dem Handy ab dem zweiten Chip
    const chips = await c.page.$$eval(".werkzeug .chip", (l) => l.map((e) => [e.innerText.trim(), Math.round(e.getBoundingClientRect().right)]));
    const imBild = chips.filter(([, r]) => r <= breite).map(([t]) => t);
    pruef(z.z >= 15.5 && (breite > 400 || (chips[0][0] === "3D-Häuser" && imBild.length >= 4)), `${breite} px: Zoom nach „3D-Häuser“ ${z.z.toFixed(1)}; Chips ganz im Bild: ${imBild.join(", ")}`);
    if (breite > 400) {
      // Doppelklick auf den Nachbarn wählt ihn (der zweite Klick wählt ihn nicht wieder ab); ein Klick in den gewählten
      // Stadtteil wählt nichts ab; Wahl aus der Liste fliegt zu den Häusern
      const griff = () => c.page.$eval("#griff-name", (e) => e.textContent);
      const n3d = () => c.page.evaluate(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length);
      const ruhe = () => c.page.waitForFunction(() => !window.KIEZ_KARTE.isMoving() && window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {}).then(() => c.page.waitForTimeout(300));
      const g0 = await griff();
      // freier Punkt ohne Haus, im gewählten Stadtteil (gleich) oder in einem anderen
      const frei = async (gleich) => c.page.evaluate(([nr, gleich]) => { const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect();
        for (let y = 200; y < r.height - 60; y += 23) for (let x = 120; x < r.width - 120; x += 29) {
          const t = m.queryRenderedFeatures([x, y], { layers: ["teile-flaeche"] });
          if (t.length && (t[0].properties.nr === nr) === gleich && !m.queryRenderedFeatures([x, y], { layers: ["gebaeude3d"] }).length && document.elementFromPoint(r.left + x, r.top + y) === m.getCanvas()) return { x: r.left + x, y: r.top + y };
        }
        return null; }, [(await griff()).split(" ")[0], gleich]);
      await c.page.evaluate(() => window.KIEZ_KARTE.jumpTo({ zoom: 14.6 })); await ruhe();   // bei 16,2 liegt nur die Innenstadt im Bild
      const leer = await frei(false);
      if (leer) { await c.page.mouse.dblclick(leer.x, leer.y); await c.page.waitForTimeout(300); await ruhe(); }
      const g1 = await griff();
      const leer2 = await frei(true);
      if (leer2) { await c.page.mouse.click(leer2.x, leer2.y); await c.page.waitForTimeout(400); }
      const g2 = await griff();
      await c.page.evaluate(() => document.querySelector('.treffer[data-nr="72"]').click()); await c.page.waitForTimeout(300);
      await c.page.waitForFunction(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["gebaeude3d"] }).length > 0, null, { timeout: 15000 }).catch(() => {}); await ruhe();
      const g3 = await griff(), n3 = await n3d();
      pruef(leer && leer2 && g1 !== g0 && /^\d\d /.test(g1) && g2 === g1 && /^72 /.test(g3) && n3 > 0 && c.fehler.length === 0,
        `Doppelklick auf einen Nachbarn von ${g0}: ${g1} gewählt; Klick in ihn: weiter ${g2}; Liste „72“: ${g3}, ${n3} Häuser im Bild`);
    }
    await c.ctx.close();
  }
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

// ---------- K31: gleiche erste Kopfzeile auf allen Seiten (Start · Karte · Planer · Bauzeiten), der eigene Teil mit aria-current
{
  const TEILE = ["index.html", "karte.html", "planer.html", "jahre.html"];
  const SEITEN = { "index.html": "index.html", "karte.html": "karte.html", "planer.html": "planer.html", "planer-methode.html": "planer.html",
    "planer-daten.html": "planer.html", "jahre.html": "jahre.html", "jahre-methode.html": "jahre.html", "jahre-daten.html": "jahre.html", "404.html": null };
  // jahre-methode.html gehört im Audit-Durchgang einer anderen Gruppe; bis ihr Kopf nachgezogen ist, nur Hinweis statt Befund
  const AUSSTEHEND = new Set([]);
  console.log("Kopfzeile (K31)");
  for (const [datei, eigen] of Object.entries(SEITEN)) {
    const t = fs.readFileSync(path.join(WURZEL, datei), "utf8");
    const nav = (t.match(/<nav class="kopf-haupt"[^>]*>([\s\S]*?)<\/nav>/) || [])[1] || "";
    const links = [...nav.matchAll(/<a class="nav" href="([^"]+)"([^>]*)>/g)].map((m) => ({ href: m[1], aktuell: /aria-current/.test(m[2]) }));
    const ok = JSON.stringify(links.map((l) => l.href)) === JSON.stringify(TEILE)
      && JSON.stringify(links.filter((l) => l.aktuell).map((l) => l.href)) === JSON.stringify(eigen ? [eigen] : []);
    const text = `${datei}: erste Kopfzeile ${links.map((l) => l.href.replace(".html", "") + (l.aktuell ? "*" : "")).join(" · ") || "fehlt"}`;
    if (!ok && AUSSTEHEND.has(datei)) console.log("  offen " + text + " (Datei außerhalb dieses Durchgangs)");
    else pruef(ok, text);
  }
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
