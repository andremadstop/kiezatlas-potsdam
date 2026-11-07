// Prüfung Paket B5 (Zweig 1 und 2): Seiten jahre.html, jahre-methode.html, jahre-daten.html.
// Je Seite per file:// und per HTTP (127.0.0.1): lädt bis window.KIEZ_BEREIT, keine Konsolenfehler, axe ohne
// Verstoß, alle Zahlenfelder gefüllt, bei 375 px kein waagrechtes Scrollen, Farbtöne der gerenderten Seite
// und der Kartenfarben außerhalb 20°–70°. Dazu auf jahre.html: Fragen stellen die Karte ein, reduzierte
// Bewegung ohne Animation, Klassenleiste per Klick und Tastatur, Zell-Popup mit Quelle, Hash-Rundreise,
// Vergleichsliste, keine Gebäudedateien geladen. Auf jahre-daten.html: alle vier Downloads, Inhalt geprüft.
// Statisch: verbotene Tokens, Namen und Schriften (Bauplan Abschnitt 5), keine Geviertstriche, Palette.
// Zweig 2 (Gebäude ab Zoom 14 aus daten/jahre/<nr>.js): Datenvertrag aller 32 Dateien, daten/jahre_methode.js
// aktuell, Gebäude erst ab Zoom 14 und nie beim Start geladen, Zeitfilter ohne Nachladen, Gebäude-Popup mit
// Quelle und Status (echt; „belegt“ mit der Fixture über HTTP), Hash mit Blick, Rücktest auf der Methodenseite.
//
// Kein Netz: Anfragen an fremde Server (Kacheln basemap.de, Luftbild LGB) beantwortet der Browser selbst
// mit einem leeren 1-px-PNG (wie pruefen/seiten.mjs). So entsteht kein Abruf bei fremden Diensten.
//
// Aufruf:  node pruefen/B5_jahre.mjs [--json <datei>] [--bilder <ordner>]      Rückgabe 0 = grün, 1 = Befund.
// Grauschwelle der Farbtonprüfung: Farben mit HSL-Sättigung unter SAT_MIN haben keinen erkennbaren
// Farbton und zählen nicht (Kartenpapier, Linien). Alles darüber muss außerhalb 20°–70° liegen.
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { DatabaseSync } from "node:sqlite";  // Node ≥ 22.5; für den Abgleich des GeoPackage
import { execFileSync } from "node:child_process";

const HIER = path.dirname(fileURLToPath(import.meta.url));
const WURZEL = path.resolve(HIER, "..");
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const AXE = fs.readFileSync(path.join(WURZEL, "node_modules", "axe-core", "axe.min.js"), "utf8");
const LEERBILD = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
// Grundkarte (Vektor): Kacheln und Schriften als leere Protobuf-Antwort, alles andere als leeres PNG
const fremdAntwort = (u) => /\.pbf(\?|$)/.test(u) ? { status: 200, contentType: "application/x-protobuf", body: Buffer.alloc(0) } : { status: 200, contentType: "image/png", body: LEERBILD };
const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
const SEITEN = ["jahre.html", "jahre-methode.html", "jahre-daten.html"];
const EIGENE = ["jahre.html", "jahre.js", "jahre.css", "jahre-methode.html", "jahre-daten.html"];
const BILDER = arg("--bilder");  // Ordner für Bildschirmfotos (optional, nicht im Repo ablegen)
const bild = (page, name) => BILDER ? page.screenshot({ path: path.join(BILDER, name) }) : null;
const SAT_MIN = 0.12, HUE_VON = 20, HUE_BIS = 70;

const befunde = [], bericht = { stand: new Date().toISOString(), sat_min: SAT_MIN, punkte: [] };
function pruef(ok, text) { console.log((ok ? "  ok   " : "  FEHLT ") + text); bericht.punkte.push({ ok, text }); if (!ok) befunde.push(text); return ok; }

// ---------- Farben
function hsl(c) {
  let m, r, g, b;
  c = c.trim().toLowerCase();
  if ((m = c.match(/^#([0-9a-f]{3,8})$/))) {
    let h = m[1]; if (h.length <= 4) h = h.split("").map((x) => x + x).join("");
    [r, g, b] = [0, 2, 4].map((i) => parseInt(h.slice(i, i + 2), 16));
  } else if ((m = c.match(/^rgba?\(([^)]+)\)$/))) {
    const t = m[1].split(/[\s,/]+/).filter(Boolean).map(parseFloat); [r, g, b] = t; if (t.length > 3 && t[3] === 0) return null;
  } else if ((m = c.match(/^hsla?\(([^)]+)\)$/))) {
    const t = m[1].split(/[\s,/]+/).filter(Boolean).map(parseFloat); return { h: t[0], s: t[1] / 100, l: t[2] / 100 };
  } else return null;
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), min = Math.min(r, g, b), l = (max + min) / 2, d = max - min;
  if (!d) return { h: 0, s: 0, l };
  const s = d / (1 - Math.abs(2 * l - 1));
  let h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  h *= 60; if (h < 0) h += 360;
  return { h, s, l };
}
function verboteneToene(liste) {
  const aus = [];
  for (const c of new Set(liste)) { const x = hsl(c); if (x && x.s >= SAT_MIN && x.h >= HUE_VON && x.h <= HUE_BIS) aus.push(`${c} (${Math.round(x.h)}°, S ${x.s.toFixed(2)})`); }
  return aus;
}
const FARBMUSTER = /#[0-9a-fA-F]{3,8}\b|rgba?\([^)]*\)|hsla?\([^)]*\)/g;

// ---------- Statische Prüfung der eigenen Dateien
console.log("Statisch (" + EIGENE.join(", ") + ")");
const VERBOTEN = [/#05060B/i, /#EAE7DE/i, /#8BE8D2/i, /Unbounded/i, /Host Grotesk/i, /Newsreader/i, /\bGeist\b/i, /Atlas der Fragen/i, /Jahresring/i, /\bRing\b/, /—/];
let statischeFarben = [];
for (const f of EIGENE) {
  const t = fs.readFileSync(path.join(WURZEL, f), "utf8");
  const treffer = VERBOTEN.filter((r) => r.test(t)).map(String);
  pruef(treffer.length === 0, `${f}: keine verbotenen Tokens, Namen, Schriften, Geviertstriche ${treffer.join(" ")}`);
  // Methodenvorbild: genau eine Nennung, nur auf der Methodenseite (Bauplan Abschnitt 5, Prüfbericht)
  const vis = (t.match(/visinage/gi) || []).length;
  pruef(f === "jahre-methode.html" ? vis === 1 : vis === 0, `${f}: „visinage“ ${vis}-mal (erlaubt: ${f === "jahre-methode.html" ? "genau einmal als Methodenvorbild" : "nie"})`);
  if (/\.(css|js)$/.test(f)) statischeFarben = statischeFarben.concat(t.match(FARBMUSTER) || []);
  pruef(!/\bfetch\s*\(|XMLHttpRequest/.test(t), `${f}: kein fetch/XHR (file://)`);
  pruef(!/daten\/gebaeude\//.test(t), `${f}: keine ALKIS-Gebäudedateien daten/gebaeude/ (Bauzeit je Gebäude nur aus daten/jahre/)`);
}

// ---------- Datenvertrag der Gebäudedateien (B4) und Methodendatei (Zweig 2)
console.log("\nGebäudedateien daten/jahre/*.js");
const ladeJs = (p) => { const s = fs.readFileSync(p, "utf8"); return JSON.parse(s.slice(s.indexOf("=") + 1).trim().replace(/;$/, "")); };
const JAHRE = path.join(WURZEL, "daten", "jahre");
const JDATEIEN = fs.readdirSync(JAHRE).filter((f) => /^\d{2}\.js$/.test(f)).sort();
let gebAlle = 0;
{
  const fehl = [], NAMEN = ["j", "k", "g", "q", "s", "h", "hq"];   // h = Höhe in m für 3D, hq = ihre Herkunft (06.11.)
  for (const f of JDATEIEN) {
    const d = ladeJs(path.join(JAHRE, f));
    if (d.fixture) fehl.push(f + ": Fixture");
    // Vermerk je Lizenz (Nachtrag N3): dl-de mit „Daten verändert“ und Lizenzlink; CC0 (Wikidata) mit Link zur CC0-Erklärung.
    // Andere Lizenzen (ODbL, CC BY-SA, ungeklärt) fallen durch, auch wenn der Vermerk passt.
    for (const [q, v] of Object.entries(d.quellen)) {
      const dl = /dl-de\/by-2-0/.test(v.lizenz) && !/odbl|by-sa|ungekl/i.test(v.lizenz) && /Daten verändert \(eigene Berechnung\)/.test(v.vermerk) && /govdata\.de\/dl-de\/by-2-0/.test(v.vermerk);
      const cc0 = v.lizenz === "CC0 1.0" && /creativecommons\.org\/publicdomain\/zero\/1\.0/.test(v.vermerk);
      if (!v.quelle || !(dl || cc0)) fehl.push(`${f}: Quelle ${q} (${v.lizenz}) ohne Vermerk „Daten verändert“ mit dl-de-Link oder CC0-Link`);
    }
    for (const x of d.features) {
      gebAlle++;
      const p = x.properties, extra = Object.keys(p).filter((k) => !NAMEN.includes(k));
      if (extra.length) fehl.push(`${f}: Feld ${extra.join(",")}`);
      if (!["belegt", "geschaetzt", "nicht_datiert"].includes(p.g)) fehl.push(`${f}: g=${p.g}`);
      if (!(Number.isInteger(p.h) && p.h >= 1 && p.h <= 200)) fehl.push(`${f}: h=${p.h}`);
      if (!["kataster", "geschosse", "ersatz"].includes(p.hq)) fehl.push(`${f}: hq=${p.hq}`);
      if ((p.k == null) !== (p.g === "nicht_datiert")) fehl.push(`${f}: k=${p.k} bei g=${p.g}`);
      if (p.g !== "nicht_datiert" && !(p.q && d.quellen[p.q])) fehl.push(`${f}: Quelle ${p.q} fehlt`);
      if (p.j != null && p.g !== "belegt") fehl.push(`${f}: Jahr bei ${p.g}`);
      if (fehl.length > 5) break;
    }
  }
  pruef(JDATEIEN.length === 32 && fehl.length === 0, `${JDATEIEN.length} Dateien, ${gebAlle} Gebäude: nur j/k/g/q/s/h/hq, Höhe 1–200 m mit Herkunft, jede Angabe mit Status und Quelle samt Vermerk, Jahr nur bei „belegt“ ${fehl.slice(0, 5).join(" | ")}`);
  let ok = true, aus = "";
  try { aus = execFileSync("python3", ["-I", path.join(WURZEL, "skripte", "26_jahre_methode.py"), "--pruefen"], { encoding: "utf8" }).trim(); } catch (e) { ok = false; aus = String(e.stdout || e.message).trim(); }
  let vertrag = "";
  try { vertrag = execFileSync("python3", ["-I", path.join(WURZEL, "pruefen", "B5_methode.py")], { encoding: "utf8" }).trim(); } catch (e) { vertrag = "FEHLT " + String(e.stdout || e.message).trim(); }
  pruef(/^\s*ok\s/.test(vertrag), `daten/jahre_methode.js gegen pruefen/B5_schema/jahre_methode.json (Prüfmaschine aus daten.py): ${vertrag.replace(/\s+/g, " ")}`);
  const M = ladeJs(path.join(WURZEL, "daten", "jahre_methode.js"));
  pruef(ok && M.gebaeude === gebAlle && M.ruecktest.every((r) => r.je_bauzeit.length && r.je_stufe.every((x) => x.n > 0)), `daten/jahre_methode.js aktuell (${aus}), ${M.gebaeude} Gebäude, Rücktest je Bauzeit und Stufe mit n`);
}
{
  const v = verboteneToene(statischeFarben);
  pruef(v.length === 0, `Farben in jahre.css/jahre.js: ${new Set(statischeFarben).size} geprüft, keine zwischen ${HUE_VON}° und ${HUE_BIS}° ${v.join(" ")}`);
  const pal = (fs.readFileSync(path.join(WURZEL, "jahre.js"), "utf8").match(/PALETTE = \[([^\]]+)\]/) || [])[1];
  const pl = pal ? pal.match(/#[0-9a-f]{6}/gi) : [];
  pruef(pl.length === 8 && verboteneToene(pl).length === 0 && pl.every((c) => hsl(c).s >= 0.12), `Palette: 8 Stufen, alle mit Farbton außerhalb ${HUE_VON}°–${HUE_BIS}°: ${pl.map((c) => c + " " + Math.round(hsl(c).h) + "°").join(", ")}`);
}

// ---------- Prüfserver
const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (p !== WURZEL && !p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p, (f, d) => { if (f) { a.writeHead(404); a.end(); return; } a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const HTTP = `http://127.0.0.1:${server.address().port}/`, FILE = pathToFileURL(WURZEL + path.sep).href;
const eigen = (u) => u.startsWith("file://") || u.startsWith(HTTP) || u.startsWith("data:") || u.startsWith("blob:");
const browser = await chromium.launch();

async function oeffnen(basis, datei, { hash = "", bewegung = "reduce", breite = 1440, hoehe = 900, touch = false } = {}) {
  const ctx = await browser.newContext({ viewport: { width: breite, height: hoehe }, reducedMotion: bewegung, acceptDownloads: true, hasTouch: touch, isMobile: touch });
  const page = await ctx.newPage(), fehler = [], abgewiesen = [], geladen = [];
  await page.route("**/*", (r) => { const u = r.request().url(); if (eigen(u)) return r.continue(); abgewiesen.push(u); return r.fulfill(fremdAntwort(r.request().url())); });
  page.on("console", (m) => { if (m.type() !== "error") return; const ort = (m.location() || {}).url || ""; if (!(/ERR_ABORTED/.test(m.text()) && (!ort || !eigen(ort)))) fehler.push(m.text().split("\n")[0]); });
  page.on("pageerror", (e) => fehler.push("pageerror: " + e.message));
  page.on("request", (q) => geladen.push(q.url()));
  await page.goto(basis + datei + hash, { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  if (datei === "jahre.html") await page.waitForFunction(() => window.KIEZ_KARTE && window.KIEZ_KARTE.loaded(), null, { timeout: 30000 }).catch(() => {});
  return { ctx, page, fehler, abgewiesen, geladen };
}
async function axe(page) {
  await page.addScriptTag({ content: AXE });
  const datei = page.url().startsWith("file://");
  return page.evaluate(async (datei) => (await window.axe.run(document, { resultTypes: ["violations"], preload: !datei })).violations.map((v) => v.id + " (" + v.nodes.length + ": " + v.nodes.slice(0, 2).map((n) => n.target.join(" ")).join("; ") + ")"), datei);
}
async function gerenderteFarben(page) {
  return page.evaluate(() => {
    const props = ["color", "background-color", "border-top-color", "border-bottom-color", "border-left-color", "border-right-color", "outline-color", "fill", "stroke", "text-decoration-color"];
    const aus = [];
    const sichtbar = (s) => s.display !== "none" && s.visibility !== "hidden";
    document.querySelectorAll("*").forEach((e) => {
      [null, "::before", "::after"].forEach((p) => {
        const s = getComputedStyle(e, p); if (!sichtbar(s)) return;
        props.forEach((k) => { const v = s.getPropertyValue(k); if (v && v !== "none") aus.push(v); });
        const bg = s.getPropertyValue("background-image"); if (bg && bg !== "none") (bg.match(/rgba?\([^)]*\)|#[0-9a-f]{3,8}/gi) || []).forEach((x) => aus.push(x));
      });
    });
    const m = window.KIEZ_KARTE;
    if (m) {
      const st = m.getStyle(), lauf = (x) => { if (typeof x === "string") aus.push(x); else if (Array.isArray(x)) x.forEach(lauf); else if (x && typeof x === "object") Object.values(x).forEach(lauf); };
      st.layers.forEach((l) => lauf(l.paint || {}));
    }
    return aus;
  });
}
const leereFelder = (page) => page.$$eval("[data-j]", (l) => l.filter((n) => /^…?$/.test(n.textContent.trim())).map((n) => n.getAttribute("data-j")));

for (const [art, basis] of [["file", FILE], ["http", HTTP]]) {
  for (const seite of SEITEN) {
    console.log(`\n${seite} per ${art}`);
    const { ctx, page, fehler, abgewiesen, geladen } = await oeffnen(basis, seite);
    const leer = await leereFelder(page);
    pruef(leer.length === 0, `alle Zahlenfelder aus den Daten gefüllt ${leer.join(" ")}`);
    pruef(await page.$eval("#j-fixture", (e) => e.hidden), "keine Meldung (Daten echt, passend zu den Zellen)");
    const v = await axe(page);
    pruef(v.length === 0, `axe: ${v.length} Verstöße ${v.join(", ")}`);
    const farben = await gerenderteFarben(page), vb = verboteneToene(farben);
    pruef(vb.length === 0, `gerenderte Farben (${new Set(farben).size} verschiedene, DOM + Kartenstil) ohne Farbton ${HUE_VON}°–${HUE_BIS}° ${vb.slice(0, 6).join(" ")}`);
    pruef(!geladen.some((u) => /daten\/gebaeude\//.test(u)), "keine ALKIS-Gebäudedatei daten/gebaeude/ geladen");
    pruef(!geladen.some((u) => /daten\/jahre\//.test(u)), "beim Start keine Gebäudedatei daten/jahre/ geladen");

    if (seite === "jahre.html") {
      // Reduzierte Bewegung: keine CSS-Animation, Kartenstil ohne Übergang, Kamera springt
      pruef(await page.evaluate(() => document.getAnimations().length === 0), "reduzierte Bewegung: keine laufende Animation nach dem Laden");
      pruef(await page.evaluate(() => { const t = window.KIEZ_KARTE.getStyle().transition; return t && t.duration === 0; }), "reduzierte Bewegung: Kartenstil ohne Überblendung (transition 0)");
      pruef(await page.$eval("#j-abspielen", (b) => b.hidden), "reduzierte Bewegung: „Nacheinander“ ausgeblendet");
      const erwartet = { 1: ["spanne", 0, 0, false], 2: ["spanne", 2, 3, false], 3: ["spanne", 4, 7, false], 4: ["spanne", 6, 7, false], 5: ["ueberblick"], 6: ["ueberblick"], 7: ["ueberblick"] };
      for (const n of Object.keys(erwartet)) {
        await page.$eval("#frage-" + n, (e) => e.scrollIntoView({ block: "center" }));
        await page.waitForFunction((n) => document.getElementById("frage-" + n).classList.contains("ist-aktiv"), n, { timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(150);
        const s = await page.evaluate(() => { const J = window.KIEZ_JAHRE, m = J.map; return { a: J.S.ansicht, v: J.S.von, b: J.S.bis, d: J.S.d3, beweg: m.isMoving(), anim: document.getAnimations().length, pitch: m.getPitch() }; });
        const e = erwartet[n];
        const ok = s.a === e[0] && (e.length < 2 || (s.v === e[1] && s.b === e[2] && s.d === e[3]));
        pruef(ok && !s.beweg && s.anim === 0, `Frage ${n}: Karte eingestellt (${s.a} ${s.v}–${s.b}${s.d ? " 3D" : ""}), Kamera steht, keine Animation${ok && !s.beweg && s.anim === 0 ? "" : " " + JSON.stringify(s)}`);
      }
      // zurück auf ganz Potsdam (Frage 7 endete bei den Gebäuden)
      await page.evaluate(() => window.KIEZ_JAHRE.schritt(6));
      // Klassenleiste: Klick und Tastatur
      await page.$eval("#j-klassen", (e) => e.scrollIntoView({ block: "center" }));
      await page.click("#j-klassen .j-klasse:nth-child(4)");
      let s = await page.evaluate(() => [window.KIEZ_JAHRE.S.ansicht, window.KIEZ_JAHRE.S.von, window.KIEZ_JAHRE.S.bis, document.querySelectorAll('#j-klassen [aria-pressed="true"]').length]);
      pruef(s[0] === "spanne" && s[1] === 3 && s[2] === 3 && s[3] === 1, "Leiste: Klick auf die vierte Klasse zeigt nur diese (1979–1990)");
      await page.focus("#j-bis"); await page.keyboard.press("ArrowRight"); await page.keyboard.press("ArrowRight");
      s = await page.evaluate(() => [window.KIEZ_JAHRE.S.von, window.KIEZ_JAHRE.S.bis, document.getElementById("j-bis").getAttribute("aria-valuetext"), document.getElementById("j-status").textContent]);
      pruef(s[0] === 3 && s[1] === 5 && s[2] === "2001–2010" && /1979 bis 2010/.test(s[3]), `Leiste: Regler „bis“ per Pfeiltaste, Status „${s[3]}“`);
      const filt = await page.evaluate(() => JSON.stringify(window.KIEZ_KARTE.getPaintProperty("zellen-2d", "fill-color")));
      pruef(/j_a3/.test(filt) && /j_a5/.test(filt) && !/j_a2"/.test(filt), "Kartenfarbe rechnet genau die gewählten Klassen (ohne neues Laden)");
      // Legende mit Quelle
      const leg = await page.$eval("#j-legende", (e) => e.textContent);
      pruef(/Zensus 2022, Stichtag/.test(leg) && /nicht einzelne Gebäude/.test(leg), "Legende nennt Quelle, Stichtag und „nicht einzelne Gebäude“");
      pruef(/Daten verändert \(eigene Berechnung\)/.test(await page.$eval("#j-zahlen-quelle", (e) => e.textContent)), "Kopfzahlen mit dl-de-Vermerk „Daten verändert (eigene Berechnung)“");
      const ohneHinweis = await page.$$eval('[data-j$="-n"]', (l) => l.filter((b) => !/hochgerechnet/i.test(b.closest("p").textContent)).map((b) => b.getAttribute("data-j")));
      pruef(ohneHinweis.length === 0 && /hochgerechnet und gerundet/.test(await page.$eval("#frage-1", (e) => e.textContent)), `Gebäudezahlen in den Fragen als „hochgerechnet“ gekennzeichnet, Unsicherheitshinweis ${ohneHinweis.join(" ")}`);
      // Zell-Popup
      // erst die Ansicht (schritt setzt die Kamera auf ganz Potsdam), dann nah heran, damit eine Zelle viele Pixel groß ist
      await page.evaluate(() => window.KIEZ_JAHRE.schritt(5));
      await page.evaluate(() => window.KIEZ_KARTE.jumpTo({ center: [13.0645, 52.3989], zoom: 13.6, pitch: 0 }));
      await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      const punkt = await page.evaluate(() => {
        // erste Zelle mit Klasse, deren Mitte frei auf der Kartenfläche liegt (nicht unter Werkzeug, Knöpfen, Leiste)
        const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect(), leinwand = m.getCanvas();
        for (const f of m.queryRenderedFeatures({ layers: ["zellen-2d"] }).filter((x) => x.properties.j_s === 3)) {
          const c = f.geometry.coordinates[0], p = m.project([(c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2]), x = r.left + p.x, y = r.top + p.y;
          if (document.elementFromPoint(x, y) === leinwand) return { x, y };
        }
        return null;
      });
      if (punkt) { await page.mouse.click(punkt.x, punkt.y); await page.waitForTimeout(200); }
      const pop = await page.$eval(".maplibregl-popup-content", (e) => e.textContent).catch(() => "");
      pruef(/Gebäude mit Wohnraum/.test(pop) && /Zensus 2022, Stichtag/.test(pop) && /eigene Berechnung/.test(pop) && /nicht einzelne Gebäude/.test(pop), "Zell-Popup: Werte mit Quelle, Stichtag, Vermerk, „nicht einzelne Gebäude“");
      // Vergleichsliste
      await page.click('#j-liste .j-zeile >> text="Babelsberg Nord"').catch(() => page.click("#j-liste li:nth-child(10) .j-zeile"));
      const sb = await page.evaluate(() => [document.getElementById("j-sb-name").textContent, document.querySelectorAll('#j-liste [aria-pressed="true"]').length, document.querySelectorAll("#j-sb-tabelle tbody tr").length, document.getElementById("j-sb-hinweis").textContent]);
      pruef(sb[1] === 1 && sb[2] === 8 && /Genähert/.test(sb[3]) && /gerundet/.test(sb[3]), `Vergleich: Auswahl „${sb[0]}“, Steckbrief mit 8 Klassen, Hinweis auf Näherung und Rundung`);
      await page.check('input[name="sortierung"][value="anteil"]', { force: true });
      const sortiert = await page.$$eval("#j-liste .j-zeile__wert", (l) => l.map((x) => x.textContent));
      const zahlen = sortiert.filter((x) => /%/.test(x)).map((x) => /unter 1/.test(x) ? 0.5 : parseInt(x, 10));
      pruef(zahlen.every((v, i) => i === 0 || zahlen[i - 1] >= v), "Vergleich: Sortierung nach Anteil absteigend");
      // ---------- Zweig 2: Gebäude
      const jahreAnfragen = () => geladen.filter((u) => /daten\/jahre\/\d{2}\.js/.test(u)).length;
      const vor12 = jahreAnfragen();
      await page.evaluate(() => window.KIEZ_KARTE.jumpTo({ center: [13.06, 52.40], zoom: 12.5 }));
      await page.waitForTimeout(300);
      pruef(jahreAnfragen() === vor12 && await page.evaluate(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-farbe", "geb-nd", "geb-rest"] }).length === 0), "unter Zoom 14: keine Gebäude gezeichnet, keine Gebäudedatei geladen");
      const leg0 = await page.$eval("#j-legende", (e) => e.textContent);
      pruef(/ab Zoom 14/.test(leg0), "unter Zoom 14: Legende weist auf die Gebäude ab Zoom 14 hin");
      // Frage 7 führt zu den Gebäuden am Stern, als 3D-Häuser (seit 07.11.); danach 3D aus für die flachen Prüfungen
      await page.$eval("#frage-7", (e) => e.scrollIntoView({ block: "center" }));
      const gebDa = () => page.waitForFunction(() => { const g = window.KIEZ_JAHRE.geb(); return g.im_bild.length && g.im_bild.every((n) => g.geladen.includes(n)); }, null, { timeout: 15000 }).catch(() => {});
      await gebDa();
      await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(300);
      const g7 = await page.evaluate(() => { const m = window.KIEZ_KARTE; return { z: m.getZoom(), p: m.getPitch(), d: window.KIEZ_JAHRE.S.d3, sicht: m.getLayoutProperty("geb-3d", "visibility"), n: m.queryRenderedFeatures({ layers: ["geb-3d"] }).length, ...window.KIEZ_JAHRE.geb() }; });
      pruef(g7.d && g7.z >= 14 && g7.p >= 45 && g7.sicht === "visible" && g7.n > 50 && g7.geladen.length <= 4 && jahreAnfragen() === g7.geladen.length,
        `Frage 7: 3D-Häuser am Stern (Zoom ${g7.z.toFixed(1)}, Neigung ${Math.round(g7.p)}, ${g7.n} Körper, Dateien ${g7.geladen.join(", ")}, ${jahreAnfragen()} Anfragen)`);
      await page.evaluate(() => { document.getElementById("j-dreid").click(); });
      await page.waitForTimeout(300); await gebDa();
      await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(300);
      let g = await page.evaluate(() => ({ z: window.KIEZ_KARTE.getZoom(), ...window.KIEZ_JAHRE.geb(), n: window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-farbe"] }).length, anim: document.getAnimations().length }));
      pruef(g.z >= 14 && g.geladen.includes("71") && g.n > 50 && g.anim === 0, `Frage 7: Zoom ${g.z.toFixed(1)}, Gebäude aus ${g.geladen.join(", ")} (${g.n} farbig im Bild), keine Animation`);
      pruef(g.im_bild.length <= 4 && jahreAnfragen() === g.geladen.length, `höchstens 4 Stadtteile im Bild geladen, je Datei genau eine Anfrage (${jahreAnfragen()} Anfragen, ${g.geladen.length} Dateien)`);
      const leg1 = await page.$eval("#j-legende", (e) => e.textContent), st1 = await page.$eval("#kartenstatus", (e) => e.textContent);
      pruef(/geschätzt/.test(leg1) && /nicht datiert/.test(leg1) && /keine Aussage über einzelne Grundstücke/.test(leg1) && /Daten verändert \(eigene Berechnung\)/.test(leg1) && /Gebäude aus [^;.]*\b71 Stern/.test(st1), `ab Zoom 14: Legende mit „geschätzt“, „nicht datiert“, Vermerk; Kartenstatus „${st1}“`);
      pruef(/blick=13\.12\d+,52\.37\d+,1[45]\.\d\d/.test(await page.evaluate(() => location.hash)), "Adresse merkt sich den Blick auf die Gebäude (blick=…)");
      // Klick auf ein Gebäude: frei liegende Mitte eines gerenderten Umrisses
      const klickGeb = async (schicht, bed) => {
        const pt = await page.evaluate(([schicht, bed]) => {
          const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect(), lw = m.getCanvas();
          for (const f of m.queryRenderedFeatures({ layers: [schicht] })) {
            if (bed && f.properties.g !== bed) continue;
            const c = f.geometry.type === "Polygon" ? f.geometry.coordinates[0] : f.geometry.coordinates[0][0];
            const x0 = c.reduce((a, p) => a + p[0], 0) / c.length, y0 = c.reduce((a, p) => a + p[1], 0) / c.length, p = m.project([x0, y0]);
            const hit = m.queryRenderedFeatures([p.x, p.y], { layers: ["geb-farbe", "geb-nd", "geb-rest"] });
            if (hit.length && hit[0].layer.id === schicht && document.elementFromPoint(r.left + p.x, r.top + p.y) === lw) return { x: r.left + p.x, y: r.top + p.y };
          }
          return null;
        }, [schicht, bed]);
        if (!pt) return "kein freier Punkt";
        await page.mouse.click(pt.x, pt.y); await page.waitForTimeout(200);
        return page.$eval(".maplibregl-popup-content", (e) => e.textContent).catch(() => "kein Popup");
      };
      const popG = await klickGeb("geb-farbe", "geschaetzt");
      pruef(/Bauzeit \d|Bauzeit vor|Bauzeit ab/.test(popG) && /geschätzt/.test(popG) && /Quelle: /.test(popG) && /Daten verändert \(eigene Berechnung\)/.test(popG) && /keine Aussage über einzelne Grundstücke/.test(popG) && !/Gebäude mit Wohnraum<|Zelle \d/.test(popG),
        `Gebäude-Popup: Bauzeit, „geschätzt“, Weg, Quelle mit Vermerk, Grundstückshinweis (${popG.slice(0, 70)}…)`);
      // K22: Schätzweg statt „Stufe X von 6“, Rücktest der Stufe aus daten/jahre_methode.js (je Prüfsatz, mit n)
      const Mx = await page.evaluate(() => window.KIEZ_JAHRE_METHODE);
      const stufeG = await page.evaluate(() => { const m = window.KIEZ_KARTE; const f = m.queryRenderedFeatures({ layers: ["geb-farbe"] }).filter((x) => x.properties.g === "geschaetzt"); return f.length ? f.map((x) => x.properties.s) : []; });
      const rtErw = (s) => Mx.ruecktest.map((r) => r.je_stufe.find((y) => parseInt(y.stufe, 10) === +s)).filter((x) => x && x.bewertet)
        .map((x) => `${x.treffer.toLocaleString("de-DE")} von ${x.bewertet.toLocaleString("de-DE")} Prüfgebäuden` + (x.bewertet >= Mx.darstellung.mindest_n ? ` (etwa ${Math.round(x.quote / 10)} von 10)` : ""));
      const passt = [...new Set(stufeG)].some((s) => rtErw(s).length && rtErw(s).every((t) => popG.includes(t)));
      pruef(/Schätzweg: /.test(popG) && !/Stufe \d von 6/.test(popG) && /Im Rücktest traf dieser Schätzweg/.test(popG) && passt,
        `Gebäude-Popup: Schätzweg und Rücktest der Stufe mit n aus daten/jahre_methode.js, kein „Stufe X von 6“ (${(popG.match(/Im Rücktest[^.]*\./) || [""])[0].slice(0, 90)}…)`);
      const popN = await klickGeb("geb-nd");
      pruef(/Nicht datiert/.test(popN) && /Umriss: .*GeoBasis-DE\/LGB/.test(popN), "Gebäude-Popup „nicht datiert“ mit Quelle des Umrisses");
      // Zeitfilter: Leiste und Regler filtern die Gebäude, ohne neu zu laden
      const vorher = jahreAnfragen(), nAlle = g.n;
      await page.click("#j-klassen .j-klasse:nth-child(3)");
      await page.focus("#j-bis"); await page.keyboard.press("ArrowRight");
      await page.waitForTimeout(250);
      const f = await page.evaluate(() => ({ filt: JSON.stringify(window.KIEZ_KARTE.getFilter("geb-farbe")), ks: [...new Set(window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-farbe"] }).map((x) => x.properties.k))].sort(), rest: window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-rest"] }).length }));
      pruef(jahreAnfragen() === vorher && /2\]/.test(f.filt) && /3\]/.test(f.filt) && f.ks.every((k) => k === 2 || k === 3) && f.rest > 0,
        `Zeitfilter 1949–1990: nur Klassen ${f.ks.join(",")} farbig, übrige blass, ${jahreAnfragen() - vorher} neue Anfragen`);
      const leg2 = await page.$eval("#j-legende", (e) => e.textContent);
      pruef(/andere Bauzeit/.test(leg2) && !/Prozent der Gebäude in der Zelle/.test(leg2), "Zeitfilter: Legende nennt „andere Bauzeit“, keine Prozentskala der Zellen");
      // Legendenmuster ohne Klassenfarbe (Farbe steht in der Klassenleiste)
      const PAL = JSON.parse(fs.readFileSync(path.join(WURZEL, "jahre.js"), "utf8").match(/var PALETTE = (\[[^\]]+\])/)[1]);
      const PAL_RGB = await page.evaluate((pal) => { const d = document.createElement("i"); document.body.appendChild(d); const r = pal.map((c) => { d.style.background = c; return getComputedStyle(d).backgroundColor; }); d.remove(); return r; }, PAL);
      const muster = await page.$$eval(".j-legende__muster--geschaetzt, .j-legende__muster--belegt", (l) => l.map((e) => getComputedStyle(e).backgroundColor));
      pruef(muster.length >= 1 && muster.every((c) => !PAL_RGB.includes(c)), `Legende ab Zoom 14: Muster für „geschätzt“/„belegt“ ohne Klassenfarbe (${muster.join(" ")})`);
      // 3D ab Zoom 14: keine Säulen über den Gebäuden, Zellen flach
      await page.evaluate(() => { document.getElementById("j-dreid").click(); });
      await page.waitForTimeout(400);
      const d3 = await page.evaluate(() => ({ s3: window.KIEZ_KARTE.getLayoutProperty("zellen-3d", "visibility"), s2: window.KIEZ_KARTE.getLayoutProperty("zellen-2d", "visibility"), d: window.KIEZ_JAHRE.S.d3, z: window.KIEZ_KARTE.getZoom() }));
      pruef(d3.d && d3.z >= 14 && d3.s3 === "none" && d3.s2 === "visible", `3D ab Zoom 14: keine Säulen über den Gebäuden (zellen-3d ${d3.s3}, zellen-2d ${d3.s2}, Zoom ${d3.z.toFixed(1)})`);
      await page.evaluate(() => { document.getElementById("j-dreid").click(); });
      await page.waitForTimeout(300);
      const va2 = await axe(page);
      pruef(va2.length === 0, `Gebäudeansicht: axe ${va2.length} Verstöße ${va2.join(", ")}`);
      const vb2 = verboteneToene(await gerenderteFarben(page));
      pruef(vb2.length === 0, `Gebäudeansicht: Farben ohne Farbton ${HUE_VON}°–${HUE_BIS}° ${vb2.slice(0, 4).join(" ")}`);
      pruef(await page.evaluate(() => document.getAnimations().length === 0), "Gebäudeansicht: reduzierte Bewegung ohne Animation");
      // Breiter Blick bei Zoom 14: mehr Stadtteile im Bild als geladen werden; Zellen blenden nur dort ab, wo Gebäude da sind
      await page.evaluate(() => window.KIEZ_KARTE.jumpTo({ center: [13.055, 52.395], zoom: 14 }));
      await page.waitForFunction(() => { const g = window.KIEZ_JAHRE.geb(); return g.im_bild.length && g.im_bild.every((n) => g.geladen.includes(n)); }, null, { timeout: 20000 }).catch(() => {});
      await page.waitForTimeout(300);
      const w = await page.evaluate(() => {
        const m = window.KIEZ_KARTE, g = window.KIEZ_JAHRE.geb(), deck = JSON.stringify(m.getPaintProperty("zellen-2d", "fill-opacity"));
        const lit = (deck.match(/\["literal",(\[[^\]]*\])\]/) || [])[1];
        const st = [...new Set(m.queryRenderedFeatures({ layers: ["zellen-2d"] }).map((f) => f.properties.st))].sort();
        return { g, lit: lit ? JSON.parse(lit).sort() : null, st };
      });
      const ohne = w.st.filter((n) => !w.g.im_bild.includes(n));
      pruef(w.lit && JSON.stringify(w.lit) === JSON.stringify(w.g.im_bild.slice().sort()) && w.g.im_bild.length <= 4 && (ohne.length === 0 || /weitere Stadtteile beim Heranzoomen/.test(w.g.text)),
        `breiter Blick Zoom 14: Gebäude aus ${w.g.im_bild.join(", ")}, Zellen abgeblendet nur dort (${(w.lit || []).join(", ")}), Zellen voll in ${ohne.join(", ") || "keinem"}; Hinweis „${w.g.text.slice(-40)}“`);
    }
    if (seite === "jahre-methode.html") {
      const M = await page.evaluate(() => window.KIEZ_JAHRE_METHODE);
      const m = await page.evaluate(() => ({ stufen: document.querySelectorAll("#j-m-stufen tbody tr").length, tabs: [...document.querySelectorAll("#j-m-ruecktest table")].map((t) => t.querySelectorAll("tbody tr").length), rt: document.getElementById("j-m-ruecktest").textContent, sf: document.querySelectorAll("#j-m-schieflage tbody tr").length, text: document.getElementById("inhalt").textContent }));
      const erwRt = M.ruecktest.flatMap((r) => [r.je_bauzeit.length, r.je_stufe.length]);
      const rtZeilen = M.ruecktest.flatMap((r) => r.je_bauzeit.concat(r.je_stufe)).filter((x) => x.bewertet != null), mind = M.darstellung.mindest_n;
      const quoten = rtZeilen.map((x) => `${x.treffer.toLocaleString("de-DE")} von ${x.bewertet.toLocaleString("de-DE")}` + (x.bewertet >= mind ? ` (${Math.round(x.quote).toLocaleString("de-DE")}\u00a0%)${Math.round(x.ki.unten)} bis ${Math.round(x.ki.oben)}\u00a0%` : ""));
      const zellen = await page.evaluate(() => [...document.querySelectorAll("#j-m-ruecktest tbody tr")].map((tr) => [...tr.children].map((c) => c.textContent)));
      const klein = zellen.filter((z) => z[3] !== "–" && !/%/.test(z[3]));
      const kleinErw = rtZeilen.filter((x) => x.bewertet < mind).length;
      pruef(m.stufen === 7 && JSON.stringify(m.tabs) === JSON.stringify(erwRt) && quoten.every((q) => m.rt.includes(q)) && m.sf === M.schieflage.length && klein.length === kleinErw && klein.every((z) => z[4] === "–"),
        `Methode: Stufentabelle, ${m.tabs.length} Rücktest-Tabellen je Bauzeit und Stufe (${quoten.length} Quoten mit n und 95-%-Bereich nach Wilson, gleich daten/jahre_methode.js; ${klein.length} mit n < ${mind} nur als Zählung), Vergleich mit dem Zensus`);
      // K23: Wilson-Bereich in der Datei nachrechnen, Kennzeichnung als Darstellung auf der Seite
      const wilson = (t, n) => { const z = M.darstellung.z, p = t / n, z2 = z * z, mi = (p + z2 / (2 * n)) / (1 + z2 / n), h = z * Math.sqrt(p * (1 - p) / n + z2 / (4 * n * n)) / (1 + z2 / n); return [Math.round(1000 * Math.max(0, mi - h)) / 10, Math.round(1000 * Math.min(1, mi + h)) / 10]; };
      const kiOk = M.ruecktest.flatMap((r) => r.je_bauzeit.concat(r.je_stufe)).every((x) => x.bewertet == null ? x.ki === null : (Math.abs(x.ki.unten - wilson(x.treffer, x.bewertet)[0]) < 0.06 && Math.abs(x.ki.oben - wilson(x.treffer, x.bewertet)[1]) < 0.06 && x.ki.unten <= x.quote && x.quote <= x.ki.oben));
      pruef(kiOk && /nur Darstellung/.test(m.text) && /Wilson/.test(m.text) && /Regeln und Ergebnisse der Schätzung ändern sich dadurch nicht/.test(m.text),
        "Methode: 95-%-Bereich je Quote nach Wilson nachgerechnet, Quote liegt im Bereich, als Darstellung gekennzeichnet");
      // K28: Höhenzählung aus der Datei, kein fester Wert im HTML, Kopfsatz eingeschränkt
      const hz = await page.evaluate(() => Object.fromEntries(["g-h-kataster", "g-h-geschosse", "g-h-ersatz", "g-h-kataster-p", "g-h-ohne-p", "g-umrisse-stand", "g-mindest-n"].map((k) => [k, (document.querySelector(`[data-j="${k}"]`) || {}).textContent])));
      const roh = fs.readFileSync(path.join(WURZEL, "jahre-methode.html"), "utf8");
      const hSumme = M.hoehe.kataster + M.hoehe.geschosse + M.hoehe.ersatz;
      pruef(hSumme === M.gebaeude && hz["g-h-kataster"] === M.hoehe.kataster.toLocaleString("de-DE") && hz["g-h-geschosse"] === M.hoehe.geschosse.toLocaleString("de-DE") && hz["g-h-ersatz"] === M.hoehe.ersatz.toLocaleString("de-DE")
        && hz["g-umrisse-stand"] && hz["g-umrisse-stand"] !== "…" && hz["g-mindest-n"] === String(mind)
        && !/\d\.\d{3} der \d\.\d{3} Gebäude|\d+,\d\s?%/.test(roh) && !/Alle Zahlen auf dieser Seite rechnet der Browser/.test(roh),
        `Methode: Höhe aus der Datei (Kataster ${hz["g-h-kataster"]}, Geschosse ${hz["g-h-geschosse"]}, Ersatz ${hz["g-h-ersatz"]}, Summe = ${M.gebaeude} Gebäude, ${hz["g-h-kataster-p"]}), keine feste Zählung im HTML, Kopfsatz eingeschränkt`);
      const sp = await page.evaluate(() => Object.fromEntries(["g-sf-alt", "g-sf-ddr", "g-sf-alt-w", "g-sf-ddr-w", "g-sf-alt-k", "g-sf-ddr-k", "g-nd", "g-neben"].map((k) => [k, document.querySelector(`[data-j="${k}"]`).textContent])));
      const ndDatei = M.je_g.nicht_datiert.toLocaleString("de-DE");
      pruef(sp["g-nd"] === ndDatei && sp["g-neben"] !== "…" && sp["g-neben"] !== sp["g-nd"], `Methode: „Nicht datiert“ nennt alle ${sp["g-nd"]}, davon ${sp["g-neben"]} Nebengebäude`);
      pruef(/\+41\s%/.test(sp["g-sf-alt"]) && /\u221235\s%/.test(sp["g-sf-ddr"]) && sp["g-sf-alt-w"] === "mehr" && sp["g-sf-ddr-w"] === "weniger" && sp["g-sf-alt-k"] === "vor 1919" && /1979/.test(sp["g-sf-ddr-k"]) && /nicht vergleichbar/.test(m.text) && /Prüfgebäude/.test(m.text) && /Denkmale stammen fast alle/.test(m.text),
        "Methode: Schieflage (vor 1919 +41 %, 1979–1990 −35 %), Vorbehalte zum Rücktest, kein Vergleich mit Berlin als Zahl");
      pruef((m.text.match(/visinage/gi) || []).length === 1 && /Methodenvorbild/.test(m.text), "Methode: Vorbild genau einmal genannt, als Methodenvorbild");
      // Nachtrag N3: Baualter-Statistik der LHP (H4) als Plausibilität; Gruppen summieren sich zur Gesamtzeile
      const lh = await page.evaluate(() => ({ n: document.querySelectorAll("#j-m-lhp tbody tr").length, q: (document.getElementById("j-m-lhp-quelle") || {}).textContent || "" }));
      const gr = M.lhp ? M.lhp.gruppen : [], ges = gr.find((x) => x.gruppe === "zusammen"), teil = gr.filter((x) => x !== ges);
      pruef(M.lhp && lh.n === gr.length && ges && teil.reduce((a, x) => a + x.kaskade, 0) === ges.kaskade && teil.reduce((a, x) => a + x.lhp_2025, 0) === ges.lhp_2025
        && ges.kaskade === M.schieflage.reduce((a, x) => a + x.kaskade, 0) && /dl-de\/by-2-0/.test(lh.q) && /Daten verändert/.test(lh.q),
        `Methode: Baualter-Statistik der Stadt (H4), ${lh.n} Zeilen, Gruppen = Gesamt, Gebäudekarte = Summe der Zensus-Tabelle, Vermerk mit Lizenz`);
      pruef(/Wikidata/.test(m.text) && /zurückgehalten/.test(m.text) && !/Bisher keine/.test(m.text), "Methode: genaue Jahre aus Wikidata genannt, im Rücktest zurückgehalten");
    }
    if (seite === "jahre-daten.html") {
      const n = await page.evaluate(() => window.KIEZ_JAHRE_ZELLEN.gebaeude.filter((x) => x != null).length);
      const lade = async (id) => { const [d] = await Promise.all([page.waitForEvent("download"), page.click("#" + id)]); return { name: d.suggestedFilename(), text: fs.readFileSync(await d.path(), "utf8") }; };
      const csv = await lade("j-d-zellen-csv"), z = csv.text.trim().split("\n");
      pruef(z.length === n + 1 && /^gitter_id,stadtteil,gebaeude,anteil_vor_1919,/.test(z[0]) && /vorherrschend,klassen_geheim$/.test(z[0]), `CSV Zellen ${csv.name}: ${z.length - 1} Zeilen (erwartet ${n}), Kopf ${z[0].slice(0, 60)}…`);
      const gj = await lade("j-d-zellen-geojson"), g = JSON.parse(gj.text);
      pruef(g.features.length === n && /Daten verändert \(eigene Berechnung\)/.test(g.vermerk) && g.lizenztext === "https://www.govdata.de/dl-de/by-2-0", `GeoJSON ${gj.name}: ${g.features.length} Zellen, Vermerk und Lizenzlink`);
      const rc = await lade("j-d-raum-csv"), rz = rc.text.trim().split("\n");
      const ok = rz.slice(1).every((l) => { const t = l.split(","); return +t[2] % 10 === 0; });
      pruef(rz.length > 30 && ok, `CSV je Stadtteil ${rc.name}: ${rz.length - 1} Gebiete, Gebäudezahlen auf 10 gerundet`);
      const lm = await lade("j-d-liesmich");
      pruef(/Daten verändert \(eigene Berechnung\)/.test(lm.text) && /https:\/\/www\.govdata\.de\/dl-de\/by-2-0/.test(lm.text) && /Keine Daten aus OpenStreetMap/.test(lm.text), `Liesmich ${lm.name}: Vermerk, Lizenzlink, kein OSM`);
      // GeoPackage (statisch, skripte/25_jahre_gpkg.py): Aufbau nach OGC-Norm und dieselben Werte wie die CSV-Dateien des Browsers
      const href = await page.$eval("#j-d-gpkg", (a) => a.getAttribute("href"));
      const db = new DatabaseSync(path.join(WURZEL, href), { readOnly: true });
      const ein = (sql) => db.prepare(sql).get(), alle = (sql) => db.prepare(sql).all();
      const pflicht = alle("select name from sqlite_master where type='table'").map((r) => r.name);
      const kopf = ein("select geom from zellen limit 1").geom, kb = Buffer.from(kopf);
      const box = ein("select min_x, min_y, max_x, max_y, srs_id from gpkg_contents where table_name='zellen'");
      pruef(ein("pragma application_id").application_id === 0x47504b47 && ["gpkg_spatial_ref_sys", "gpkg_contents", "gpkg_geometry_columns", "zellen", "stadtteile", "hinweis"].every((t) => pflicht.includes(t))
        && kb.toString("latin1", 0, 2) === "GP" && kb.readInt32LE(4) === 25833 && box.srs_id === 25833 && box.min_x > 350000 && box.max_x < 385000 && box.min_y > 5795000 && box.max_y < 5825000
        && ein("select count(*) n from gpkg_spatial_ref_sys where srs_id in (-1, 0, 4326, 25833)").n === 4 && ein("pragma integrity_check").integrity_check === "ok",
        `GeoPackage ${href}: Pflichttabellen, application_id GPKG, Geometriekopf GP, EPSG:25833, Ausdehnung Potsdam`);
      const gz = ein("select count(*) n from zellen").n, gzc = z.slice(1).map((l) => l.split(","));
      const gzOk = gz === n && alle("select gitter_id, gebaeude, anteil_vor_1919 a from zellen order by gitter_id").every((r, i, l) => {
        const c = gzc.find((x) => x[0] === r.gitter_id); return c && +c[2] === r.gebaeude && (c[3] === "" ? r.a === null : Math.abs(+c[3] - r.a) < 1e-9);
      });
      pruef(gzOk, `GeoPackage zellen: ${gz} Zeilen, Gebäude und Anteile gleich der Zell-CSV`);
      const rk = rz[0].split(","), rcsv = rz.slice(1).map((l) => Object.fromEntries(l.split(",").map((w, i) => [rk[i], w])));
      const gst = alle("select * from stadtteile order by cast(nr as integer)");
      const stOk = gst.length === rcsv.length && gst.every((r, i) => rk.every((k) => k === "name" || String(r[k] ?? "") === rcsv[i][k]));
      pruef(stOk, `GeoPackage stadtteile: ${gst.length} Gebiete, alle Spalten gleich der Stadtteil-CSV (gerundet)`);
      const hin = Object.fromEntries(alle("select schluessel, wert from hinweis").map((r) => [r.schluessel, r.wert]));
      const spaltenGp = alle("select name from pragma_table_info('zellen') union all select name from pragma_table_info('stadtteile')").map((r) => r.name).join(" ");
      pruef(/Daten verändert \(eigene Berechnung\)/.test(hin.vermerk) && hin.lizenztext === "https://www.govdata.de/dl-de/by-2-0" && !/strasse|hausnr|adress|eigentu/i.test(spaltenGp),
        "GeoPackage hinweis: Vermerk mit „Daten verändert“, Link zum Lizenztext; keine Adress- oder Eigentümerspalten");
      const standJs = await page.evaluate(() => window.KIEZ_JAHRE_ZELLEN.stand);
      pruef(hin.stand === standJs, `GeoPackage-Stand ${hin.stand} = Stand von jahre_zellen.js ${standJs} (sonst skripte/25_jahre_gpkg.py neu laufen lassen)`);
      db.close();
      const alles = csv.text + gj.text + rc.text;
      pruef(!/strasse|straße|hausnr|adresse|eigentuemer|eigentümer/i.test(alles.replace(/keine Adressen/g, "")), "Downloads ohne Adress- oder Eigentümerfelder");
    }
    pruef(fehler.length === 0, `keine Konsolenfehler ${fehler.slice(0, 3).join(" | ")}`);
    pruef(abgewiesen.every((u) => /geodatenzentrum\.de|geobasis-bb\.de/.test(u)), `Fremdabrufe nur Kacheln (abgewiesen: ${abgewiesen.length})`);
    await ctx.close();

    // Handy
    const h = await oeffnen(basis, seite, { breite: 375, hoehe: 812 });
    const quer = await h.page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth]);
    pruef(quer[0] <= quer[1], `375 px: kein waagrechtes Scrollen (${quer[0]} ≤ ${quer[1]})`);
    const va = await axe(h.page);
    pruef(va.length === 0, `375 px: axe ${va.length} Verstöße ${va.join(", ")}`);
    if (seite === "jahre.html") {
      // Wie ein Mensch blättern: in Schritten scrollen, bis die Frage aktiv wird; ihr Titel muss dann sichtbar und nicht von der Bühne verdeckt sein
      for (const n of [1, 2, 3]) {
        let aktiv = false;
        for (let s = 0; s < 200 && !aktiv; s++) {
          await h.page.mouse.wheel(0, 30); await h.page.waitForTimeout(25);
          aktiv = await h.page.$eval("#frage-" + n, (e) => e.classList.contains("ist-aktiv"));
        }
        const frei = await h.page.$eval("#frage-" + n + " .frage__titel", (t) => {
          const r = t.getBoundingClientRect(), x = r.left + Math.min(40, r.width / 2), y = r.top + r.height / 2;
          return y > 0 && y < innerHeight && t.contains(document.elementFromPoint(x, y));
        });
        pruef(aktiv && frei, `375 px: Frage ${n} wird erst aktiv, wenn ihr Titel unter der Bühne lesbar ist`);
      }
    }
    if (seite === "jahre.html" && art === "file") {
      await bild(h.page, "B5_375.png");
      await h.page.$eval("#frage-2", (e) => e.scrollIntoView({ block: "center" })); await h.page.waitForTimeout(400);
      await bild(h.page, "B5_375_frage2.png");
    }
    await h.ctx.close();
  }
}

// Hash-Rundreise und Bewegung erlaubt (nur file://)
console.log("\nHash und Bewegung");
{
  const { ctx, page } = await oeffnen(FILE, "jahre.html", { hash: "#ansicht=spanne&von=2&bis=3&3d=1&st=52" });
  const s = await page.evaluate(() => { const S = window.KIEZ_JAHRE.S; return [S.ansicht, S.von, S.bis, S.d3, S.nr, location.hash]; });
  pruef(s[0] === "spanne" && s[1] === 2 && s[2] === 3 && s[3] === true && s[4] === "52", `Hash wird gelesen und bleibt (${s[5]})`);
  await bild(page, "B5_1440_hash.png");
  await ctx.close();
  // Verstümmelter Hash (abgeschnittenes %-Escape): Seite muss trotzdem aufgebaut werden
  {
    const v = await oeffnen(FILE, "jahre.html", { hash: "#st=%E0&ansicht=spanne" });
    const s = await v.page.evaluate(() => ({ bereit: window.KIEZ_BEREIT, karte: !!window.KIEZ_KARTE, ansicht: window.KIEZ_JAHRE.S.ansicht }));
    pruef(s.bereit === true && s.karte && s.ansicht === "spanne" && v.fehler.length === 0, `verstümmelter Hash (#st=%E0) bricht die Seite nicht ab ${v.fehler.slice(0, 2).join(" | ")}`);
    await v.ctx.close();
  }
  // Blick aus der Adresse: Gebäude sofort geladen
  for (const [art, basis] of [["file", FILE], ["http", HTTP]]) {
    const v = await oeffnen(basis, "jahre.html", { hash: "#ansicht=spanne&von=4&bis=7&blick=13.06010,52.40020,15.50" });
    await v.page.waitForFunction(() => { const g = window.KIEZ_JAHRE.geb(); return g.im_bild.length && g.im_bild.every((n) => g.geladen.includes(n)); }, null, { timeout: 15000 }).catch(() => {});
    await v.page.waitForTimeout(400);
    const s = await v.page.evaluate(() => ({ z: window.KIEZ_KARTE.getZoom(), g: window.KIEZ_JAHRE.geb(), ks: [...new Set(window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-farbe"] }).map((x) => x.properties.k))].sort(), S: window.KIEZ_JAHRE.S }));
    pruef(Math.abs(s.z - 15.5) < 0.01 && s.g.geladen.length > 0 && s.ks.length > 0 && s.ks.every((k) => k >= 4) && s.S.von === 4, `${art}: Adresse mit blick= öffnet die Gebäude (${s.g.geladen.join(", ")}), Filter ab 1991 aktiv (Klassen ${s.ks.join(",")})`);
    pruef(v.fehler.length === 0, `${art}: Gebäudeansicht ohne Konsolenfehler ${v.fehler.slice(0, 2).join(" | ")}`);
    await bild(v.page, "B5_1440_gebaeude_" + art + ".png");
    await v.ctx.close();
  }
  // „belegt“ gibt es in den echten Daten nicht (Stufe 1 und 2 leer): Fixture für Babelsberg Nord über HTTP einspielen
  {
    const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
    const page = await ctx.newPage(), fehler = [];
    await page.route("**/*", (r) => {
      const u = r.request().url();
      if (/\/daten\/jahre\/52\.js$/.test(u)) return r.fulfill({ status: 200, contentType: "text/javascript", body: fs.readFileSync(path.join(WURZEL, "daten", "fixtures", "jahre", "52.js")) });
      if (eigen(u)) return r.continue();
      return r.fulfill(fremdAntwort(r.request().url()));
    });
    page.on("pageerror", (e) => fehler.push(e.message));
    await page.goto(HTTP + "jahre.html#ansicht=ueberblick&blick=13.09846,52.40150,17.20", { waitUntil: "load" });
    await page.waitForFunction(() => window.KIEZ_BEREIT === true && window.KIEZ_JAHRE && window.KIEZ_JAHRE.geb().geladen.includes("52"), null, { timeout: 30000 }).catch(() => {});
    await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(400);
    const pt = await page.evaluate(() => {
      const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect(), lw = m.getCanvas();
      for (const f of m.queryRenderedFeatures({ layers: ["geb-farbe"] }).filter((x) => x.properties.g === "belegt")) {
        const c = f.geometry.coordinates[0], p = m.project([c.reduce((a, q) => a + q[0], 0) / c.length, c.reduce((a, q) => a + q[1], 0) / c.length]);
        if (document.elementFromPoint(r.left + p.x, r.top + p.y) === lw) return { x: r.left + p.x, y: r.top + p.y };
      }
      return null;
    });
    if (pt) { await page.mouse.click(pt.x, pt.y); await page.waitForTimeout(200); }
    const pop = await page.$eval(".maplibregl-popup-content", (e) => e.textContent).catch(() => "");
    const leg = await page.$eval("#j-legende", (e) => e.textContent), meld = await page.$eval("#j-fixture", (e) => e.hidden ? "" : e.textContent);
    const linie = await page.evaluate(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-belegt"] }).length);
    pruef(/belegt/.test(pop) && /Baujahr \d{4}/.test(pop) && /Quelle: /.test(pop) && /Belegt aus einer Quelle/.test(pop) && /belegt \(Farbe kräftig, mit Rand\)/.test(leg) && linie > 0 && /Beispieldaten/.test(meld) && fehler.length === 0,
      `Fixture: „belegt“ kräftig mit Rand (${linie} Ränder), Popup mit Baujahr und Quelle, Legende, Beispieldaten-Hinweis (${pop.slice(0, 50)}…)`);
    await bild(page, "B5_1440_fixture_belegt.png");
    await ctx.close();
  }
  // Handy in der Gebäudeansicht
  {
    const h = await oeffnen(FILE, "jahre.html", { breite: 375, hoehe: 812, hash: "#ansicht=ueberblick&blick=13.12800,52.37900,15.40" });
    await h.page.waitForFunction(() => window.KIEZ_JAHRE.geb().geladen.length > 0, null, { timeout: 15000 }).catch(() => {});
    await h.page.waitForTimeout(400);
    const quer = await h.page.evaluate(() => [document.documentElement.scrollWidth, document.documentElement.clientWidth, window.KIEZ_JAHRE.geb().geladen.length]);
    const va = await axe(h.page);
    pruef(quer[0] <= quer[1] && quer[2] > 0 && va.length === 0, `375 px Gebäudeansicht: kein waagrechtes Scrollen (${quer[0]} ≤ ${quer[1]}), axe ${va.length} ${va.join(", ")}`);
    await bild(h.page, "B5_375_gebaeude.png");
    await h.ctx.close();
  }
  // 3D = Häuser (Andre 07.11.): Schalter „3D-Häuser“ und Knopf „Häuser in 3D ansehen“ führen mit einem Klick zu
  // Häusern als Körper; nie Zellsäulen; Mausrad und Weiterlesen nehmen 3D nicht weg; Doppelklick ohne Fenster
  {
    const haeuser = async (page, geladen) => {
      await page.waitForFunction(() => { const g = window.KIEZ_JAHRE.geb(); return window.KIEZ_KARTE.getZoom() >= 14 && g.im_bild.length && g.im_bild.every((n) => g.geladen.includes(n)); }, null, { timeout: 20000 }).catch(() => {});
      await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(400);
      const z = await page.evaluate(() => { const m = window.KIEZ_KARTE; return { z: m.getZoom(), p: m.getPitch(), d: window.KIEZ_JAHRE.S.d3, selbst: window.KIEZ_JAHRE.S.selbst, sicht: m.getLayoutProperty("geb-3d", "visibility"), n: m.queryRenderedFeatures({ layers: ["geb-3d"] }).length, s3: m.getLayoutProperty("zellen-3d", "visibility"), ...window.KIEZ_JAHRE.geb() }; });
      z.anfragen = geladen.filter((u) => /daten\/jahre\/\d{2}\.js/.test(u)).length;
      return z;
    };
    for (const [breite, hoehe] of [[1440, 900], [375, 812]]) {
      for (const [wie, sel] of [["Schalter", "label:has(#j-dreid)"], ["Knopf", "#j-haeuser"]]) {
        const v = await oeffnen(FILE, "jahre.html", { breite, hoehe });
        const vor = v.geladen.filter((u) => /daten\/jahre\//.test(u)).length;
        await v.page.click(sel);
        const z = await haeuser(v.page, v.geladen);
        pruef(vor === 0 && z.d && z.selbst && z.z >= 14 && z.p >= 45 && z.sicht === "visible" && z.n >= 200 && z.s3 === "none" && z.geladen.length <= 4 && z.anfragen === z.geladen.length && v.fehler.length === 0,
          `(a) ${breite} px, ${wie}: ein Klick zu den 3D-Häusern (Zoom ${z.z.toFixed(1)}, Neigung ${Math.round(z.p)}, ${z.n} Körper, Dateien ${z.geladen.join(", ")}, beim Start ${vor}, Konsolenfehler ${v.fehler.length})`);
        if (breite === 375 && wie === "Knopf") {
          // Gegenprobe 07.11.: Fragen, die beim Scrollen zur Bühne vorbeiziehen, bekommen die Markierung, die Karte bleibt
          await v.page.waitForTimeout(1000);
          const m = await v.page.evaluate(() => ({ a: (document.querySelector("[data-schritt].ist-aktiv") || {}).getAttribute?.("data-schritt") ?? null, s: window.KIEZ_JAHRE.S.ansicht }));
          pruef(m.a !== null && m.s === "ueberblick", `375 px, Knopf: Markierung bei Frage ${m.a}, Karte bleibt beim Überblick (${m.s})`);
        }
        if (breite === 1440 && wie === "Schalter") {
          // (b) Mausrad über der Karte scrollt die Seite (DESIGN.md, Desktop-Mausrad); die Geschichte blättert weiter,
          // nimmt 3D und Kamera aber nicht weg
          const r = await v.page.locator("#karte").boundingBox();
          await v.page.mouse.move(r.x + r.width / 2, r.y + r.height / 2);
          const a0 = await v.page.evaluate(() => (document.querySelector("[data-schritt].ist-aktiv") || {}).getAttribute?.("data-schritt") ?? null);
          for (let i = 0; i < 3; i++) { await v.page.mouse.wheel(0, 300); await v.page.waitForTimeout(250); }
          await v.page.waitForTimeout(600);
          const a1 = await v.page.evaluate(() => (document.querySelector("[data-schritt].ist-aktiv") || {}).getAttribute?.("data-schritt") ?? null);
          for (let i = 0; i < 3; i++) { await v.page.mouse.wheel(0, -300); await v.page.waitForTimeout(250); }
          await v.page.waitForTimeout(600);
          const zb = await v.page.evaluate(() => { const m = window.KIEZ_KARTE; return { z: m.getZoom(), p: m.getPitch(), d: window.KIEZ_JAHRE.S.d3, y: scrollY }; });
          pruef(a1 !== a0 && zb.d && zb.p >= 45 && zb.z >= 14, `(b) Mausrad 3 Rasten runter und 3 hoch: Frage ${a0} → ${a1}, 3D bleibt (d3 ${zb.d}, Neigung ${Math.round(zb.p)}, Zoom ${zb.z.toFixed(1)})`);
          // 3D aus: Hinweis, dass die Karte wieder der Geschichte folgt
          await v.page.evaluate(() => { document.getElementById("j-dreid").click(); });
          await v.page.waitForTimeout(200);
          const st = await v.page.$eval("#j-status", (e) => e.textContent);
          pruef(/Karte folgt wieder der Geschichte/.test(st) && await v.page.evaluate(() => !window.KIEZ_JAHRE.S.selbst && window.KIEZ_KARTE.getPitch() === 0), `3D aus: Statuszeile „${st.slice(-40)}“, Neigung 0`);
          // Live-Region: der Hinweis als eigener Satz am Ende, nicht mitten in der Angabe (Gegenprobe 07.11.)
          const ks = await v.page.$eval("#kartenstatus", (e) => e.textContent);
          pruef(/\. Karte folgt wieder der Geschichte\.$/.test(ks) && !/Geschichte,/.test(ks), `3D aus: Live-Region „…${ks.slice(-60)}“`);
        }
        await v.ctx.close();
      }
    }
    // (c) Doppelklick zoomt, öffnet aber kein Fenster (auch nicht vom ersten Klick)
    {
      const v = await oeffnen(FILE, "jahre.html");
      await v.page.evaluate(() => window.KIEZ_KARTE.jumpTo({ center: [13.105, 52.392], zoom: 12.6, pitch: 0 }));
      await v.page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      await v.page.waitForTimeout(300);
      const pt = await v.page.evaluate(() => {
        const m = window.KIEZ_KARTE, r = m.getContainer().getBoundingClientRect(), lw = m.getCanvas();
        for (const f of m.queryRenderedFeatures({ layers: ["zellen-2d"] }).filter((x) => x.properties.j_s === 3)) {
          const c = f.geometry.coordinates[0], p = m.project([(c[0][0] + c[2][0]) / 2, (c[0][1] + c[2][1]) / 2]);
          if (document.elementFromPoint(r.left + p.x, r.top + p.y) === lw && m.queryRenderedFeatures([p.x, p.y], { layers: ["zellen-2d"] }).length) return { x: r.left + p.x, y: r.top + p.y };
        }
        return null;
      });
      let n = -1, z0 = 0, z1 = 0;
      if (pt) {
        z0 = await v.page.evaluate(() => window.KIEZ_KARTE.getZoom());
        await v.page.mouse.dblclick(pt.x, pt.y);
        await v.page.waitForTimeout(400);
        await v.page.waitForFunction(() => !window.KIEZ_KARTE.isMoving() && window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
        z1 = await v.page.evaluate(() => window.KIEZ_KARTE.getZoom());
        n = await v.page.locator(".maplibregl-popup").count();
      }
      pruef(pt && z1 > z0 + 0.5 && n === 0, `(c) Doppelklick auf eine Zelle: Zoom ${z0.toFixed(1)} → ${z1.toFixed(1)}, ${n} Fenster offen`);
      await v.ctx.close();
    }
    // Link mit selbst eingeschalteten 3D-Häusern (selbst=1) hält die Geschichte an; Link aus Frage 7 (3d=1 und blick=,
    // ohne selbst=1) und alter Link aus Frage 3 (3d=1 ohne blick=) nicht
    for (const [hash, halten] of [["#ansicht=ueberblick&3d=1&selbst=1&blick=13.06000,52.39950,16.20", true], ["#ansicht=ueberblick&3d=1&blick=13.12800,52.37900,15.40", false], ["#ansicht=spanne&von=4&bis=7&3d=1", false]]) {
      const v = await oeffnen(FILE, "jahre.html", { hash });
      const z0 = await v.page.evaluate(() => window.KIEZ_KARTE.getZoom());
      await v.page.$eval("#frage-5", (e) => e.scrollIntoView({ block: "center" }));
      await v.page.waitForFunction(() => document.getElementById("frage-5").classList.contains("ist-aktiv"), null, { timeout: 5000 }).catch(() => {});
      await v.page.waitForTimeout(300);
      const z = await v.page.evaluate(() => ({ z: window.KIEZ_KARTE.getZoom(), d: window.KIEZ_JAHRE.S.d3, a: window.KIEZ_JAHRE.S.ansicht }));
      const ok = halten ? z.d && Math.abs(z.z - z0) < 0.01 && z.a === "ueberblick" : !z.d && Math.abs(z.z - z0) > 0.01 && z.a === "ueberblick";
      pruef(ok && v.fehler.length === 0, `Link ${hash.slice(0, 40)}…: nach Frage 5 ${halten ? "3D und Kamera unverändert" : "führt die Geschichte (3D aus)"} (d3 ${z.d}, Zoom ${z0.toFixed(1)} → ${z.z.toFixed(1)})`);
      await v.ctx.close();
    }
    // Gegenprobe 07.11.: Adresse aus Frage 7 neu laden, zu Frage 2: die Geschichte führt (3D aus); Knopf schreibt selbst=1
    {
      const v = await oeffnen(FILE, "jahre.html");
      await v.page.mouse.wheel(0, 40); await v.page.waitForTimeout(150);
      await v.page.$eval("#frage-7", (e) => e.scrollIntoView({ block: "center" }));
      await v.page.waitForFunction(() => window.KIEZ_JAHRE.S.d3 && window.KIEZ_KARTE.getZoom() >= 14, null, { timeout: 8000 }).catch(() => {});
      await v.page.waitForTimeout(300);
      const hash = await v.page.evaluate(() => location.hash);
      await v.page.click("#j-haeuser"); await v.page.waitForTimeout(400);
      const hashK = await v.page.evaluate(() => location.hash);
      await v.ctx.close();
      const w = await oeffnen(FILE, "jahre.html", { hash });
      await w.page.$eval("#frage-2", (e) => e.scrollIntoView({ block: "center" }));
      await w.page.waitForFunction(() => document.getElementById("frage-2").classList.contains("ist-aktiv"), null, { timeout: 5000 }).catch(() => {});
      await w.page.waitForTimeout(300);
      const z = await w.page.evaluate(() => ({ d: window.KIEZ_JAHRE.S.d3, s: window.KIEZ_JAHRE.S.selbst, z: window.KIEZ_KARTE.getZoom() }));
      pruef(/3d=1/.test(hash) && !/selbst=1/.test(hash) && /selbst=1/.test(hashK) && !z.d && !z.s && z.z < 14 && w.fehler.length === 0,
        `Adresse aus Frage 7 (${hash.slice(0, 48)}…) neu geladen, Frage 2: 3D aus (d3 ${z.d}, Zoom ${z.z.toFixed(1)}); nach dem Knopf steht selbst=1 in der Adresse`);
      await w.ctx.close();
    }
    // Gegenprobe 07.11.: Knopf fliegt auch bei 3D und nah zum neu gewählten Stadtteil; „Auf der Karte zeigen“ bei 3D zu
    // seinen Häusern (nicht gekippt unter Zoom 14); auf dem Handy steht der Titel von „Selbst erkunden“ unter der Bühne
    for (const [breite, hoehe] of [[1440, 900], [375, 812]]) {
      const v = await oeffnen(FILE, "jahre.html", { breite, hoehe });
      const zeile = (nr) => v.page.evaluate((nr) => [...document.querySelectorAll(".j-zeile")].find((b) => b.querySelector(".j-zeile__nr").textContent === nr).click(), nr);
      await v.page.click("#j-haeuser"); await v.page.waitForTimeout(500);
      await zeile("13"); await v.page.click("#j-haeuser");
      const a = await haeuser(v.page, v.geladen);
      const lp = await v.page.evaluate(() => { const c = window.KIEZ_KARTE.getCenter(), f = window.KIEZ_STADTTEILE.features.find((x) => x.properties.nr === "13").properties; return Math.hypot(c.lng - f.lx, c.lat - f.ly); });
      await zeile("72"); await v.page.click("#j-sb-karte");
      const b = await haeuser(v.page, v.geladen);
      const t = await v.page.evaluate(() => { const r = document.querySelector("#frage-8 .frage__titel").getBoundingClientRect(), u = document.getElementById("buehne").getBoundingClientRect(); return { oben: r.top, unten: u.bottom, h: innerHeight }; });
      const titelOk = breite > 860 || (t.oben >= t.unten && t.oben < t.h);
      pruef(lp < 0.001 && a.im_bild.includes("13") && a.n > 0 && b.z >= 14 && b.p >= 45 && b.im_bild.includes("72") && b.n > 0 && titelOk && v.fehler.length === 0,
        `${breite} px: Knopf nach Wahl von 13 fliegt hin (${a.n} Körper aus ${a.im_bild.join(", ")}); „Auf der Karte zeigen“ 72 bei 3D: Zoom ${b.z.toFixed(1)}, Neigung ${Math.round(b.p)}, ${b.n} Körper${breite > 860 ? "" : `, Titel „Selbst erkunden“ bei ${Math.round(t.oben)} unter der Bühne (${Math.round(t.unten)})`}`);
      await v.ctx.close();
    }
    // (d) 3D über die Adresse, Überblick (Zoom um 10): keine Zellsäulen
    {
      const v = await oeffnen(FILE, "jahre.html", { hash: "#ansicht=ueberblick&3d=1" });
      const z = await v.page.evaluate(() => { const m = window.KIEZ_KARTE; return { z: m.getZoom(), d: window.KIEZ_JAHRE.S.d3, s3: m.getLayoutProperty("zellen-3d", "visibility"), s2: m.getLayoutProperty("zellen-2d", "visibility"), n2: m.queryRenderedFeatures({ layers: ["zellen-2d"] }).length }; });
      pruef(z.d && z.z < 12 && z.s3 === "none" && z.s2 === "visible" && z.n2 > 1000 && v.fehler.length === 0, `(d) 3D bei Zoom ${z.z.toFixed(1)}: zellen-3d ${z.s3}, Zellen flach (${z.n2} gezeichnet), d3 ${z.d}, Konsolenfehler ${v.fehler.length} ${v.fehler.slice(0, 2).join(" | ")}`);
      await v.ctx.close();
    }
  }
  // K32: Zwei-Finger-Schutz bei Touch (wie atlas.js), Maus/Feinzeiger ohne
  {
    const t = await oeffnen(FILE, "jahre.html", { breite: 375, hoehe: 812, touch: true });
    const k = await t.page.evaluate(() => ({ an: window.KIEZ_KARTE.cooperativeGestures.isEnabled(), fein: matchMedia("(hover:hover) and (pointer:fine)").matches, text: (document.querySelector(".maplibregl-cooperative-gesture-screen") || {}).textContent || "" }));
    const va = await axe(t.page);
    pruef(k.an && !k.fein && /zwei Fingern/.test(k.text) && va.length === 0 && t.fehler.length === 0, `Touch 375 px: Zwei-Finger-Schutz an, deutscher Hinweis („${k.text.trim().slice(0, 40)}“), axe ${va.length} ${va.join(", ")}, Konsolenfehler ${t.fehler.length}`);
    await t.ctx.close();
    const f = await oeffnen(FILE, "jahre.html");
    const kf = await f.page.evaluate(() => window.KIEZ_KARTE.cooperativeGestures.isEnabled());
    pruef(!kf, "Feinzeiger 1440 px: Zwei-Finger-Schutz aus");
    await f.ctx.close();
  }
  const b = await oeffnen(FILE, "jahre.html", { bewegung: "no-preference" });
  pruef(!(await b.page.$eval("#j-abspielen", (x) => x.hidden)), "ohne reduzierte Bewegung: „Nacheinander“ sichtbar");
  pruef(await b.page.evaluate(() => window.KIEZ_KARTE.getStyle().transition.duration > 0), "ohne reduzierte Bewegung: Kartenstil blendet über");
  await b.page.waitForTimeout(1200);
  await bild(b.page, "B5_1440.png");
  await b.ctx.close();
}

await browser.close(); server.close();
const ziel = arg("--json"); if (ziel) fs.writeFileSync(ziel, JSON.stringify(bericht, null, 1));
console.log(`\n${befunde.length ? "BEFUND: " + befunde.length : "grün"} (${bericht.punkte.length} Punkte)`);
process.exit(befunde.length ? 1 : 0);
