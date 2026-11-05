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
  const fehl = [], NAMEN = ["j", "k", "g", "q", "s"];
  for (const f of JDATEIEN) {
    const d = ladeJs(path.join(JAHRE, f));
    if (d.fixture) fehl.push(f + ": Fixture");
    for (const [q, v] of Object.entries(d.quellen)) if (!v.quelle || !/Daten verändert \(eigene Berechnung\)/.test(v.vermerk) || !/govdata\.de\/dl-de\/by-2-0/.test(v.vermerk)) fehl.push(`${f}: Quelle ${q} ohne Vermerk „Daten verändert“ oder Lizenzlink`);
    for (const x of d.features) {
      gebAlle++;
      const p = x.properties, extra = Object.keys(p).filter((k) => !NAMEN.includes(k));
      if (extra.length) fehl.push(`${f}: Feld ${extra.join(",")}`);
      if (!["belegt", "geschaetzt", "nicht_datiert"].includes(p.g)) fehl.push(`${f}: g=${p.g}`);
      if ((p.k == null) !== (p.g === "nicht_datiert")) fehl.push(`${f}: k=${p.k} bei g=${p.g}`);
      if (p.g !== "nicht_datiert" && !(p.q && d.quellen[p.q])) fehl.push(`${f}: Quelle ${p.q} fehlt`);
      if (p.j != null && p.g !== "belegt") fehl.push(`${f}: Jahr bei ${p.g}`);
      if (fehl.length > 5) break;
    }
  }
  pruef(JDATEIEN.length === 32 && fehl.length === 0, `${JDATEIEN.length} Dateien, ${gebAlle} Gebäude: nur j/k/g/q/s, jede Angabe mit Status und Quelle samt Vermerk, Jahr nur bei „belegt“ ${fehl.slice(0, 5).join(" | ")}`);
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

async function oeffnen(basis, datei, { hash = "", bewegung = "reduce", breite = 1440, hoehe = 900 } = {}) {
  const ctx = await browser.newContext({ viewport: { width: breite, height: hoehe }, reducedMotion: bewegung, acceptDownloads: true });
  const page = await ctx.newPage(), fehler = [], abgewiesen = [], geladen = [];
  await page.route("**/*", (r) => { const u = r.request().url(); if (eigen(u)) return r.continue(); abgewiesen.push(u); return r.fulfill({ status: 200, contentType: "image/png", body: LEERBILD }); });
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
      const erwartet = { 1: ["spanne", 0, 0, false], 2: ["spanne", 2, 3, false], 3: ["spanne", 4, 7, true], 4: ["spanne", 6, 7, false], 5: ["ueberblick"], 6: ["ueberblick"], 7: ["ueberblick"] };
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
      // Frage 7 führt zu den Gebäuden am Stern
      await page.$eval("#frage-7", (e) => e.scrollIntoView({ block: "center" }));
      await page.waitForFunction(() => { const g = window.KIEZ_JAHRE.geb(); return g.im_bild.length && g.im_bild.every((n) => g.geladen.includes(n)); }, null, { timeout: 15000 }).catch(() => {});
      await page.waitForFunction(() => window.KIEZ_KARTE.loaded(), null, { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(300);
      let g = await page.evaluate(() => ({ z: window.KIEZ_KARTE.getZoom(), ...window.KIEZ_JAHRE.geb(), n: window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-farbe"] }).length, anim: document.getAnimations().length }));
      pruef(g.z >= 14 && g.geladen.includes("71") && g.n > 50 && g.anim === 0, `Frage 7: Zoom ${g.z.toFixed(1)}, Gebäude aus ${g.geladen.join(", ")} (${g.n} farbig im Bild), keine Animation`);
      pruef(g.im_bild.length <= 4 && jahreAnfragen() === g.geladen.length, `höchstens 4 Stadtteile im Bild geladen, je Datei genau eine Anfrage (${jahreAnfragen()} Anfragen, ${g.geladen.length} Dateien)`);
      const leg1 = await page.$eval("#j-legende", (e) => e.textContent), st1 = await page.$eval("#kartenstatus", (e) => e.textContent);
      pruef(/geschätzt/.test(leg1) && /nicht datiert/.test(leg1) && /keine Aussage über einzelne Grundstücke/.test(leg1) && /Daten verändert \(eigene Berechnung\)/.test(leg1) && /Gebäude aus 71/.test(st1), `ab Zoom 14: Legende mit „geschätzt“, „nicht datiert“, Vermerk; Kartenstatus „${st1.slice(0, 80)}…“`);
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
      pruef(/andere Bauzeit/.test(leg2), "Zeitfilter: Legende nennt „andere Bauzeit“");
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
      const quoten = M.ruecktest.flatMap((r) => r.je_bauzeit.concat(r.je_stufe)).filter((x) => x.bewertet != null).map((x) => `${x.treffer.toLocaleString("de-DE")} von ${x.bewertet.toLocaleString("de-DE")} (${x.quote.toLocaleString("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}`);
      pruef(m.stufen === 7 && JSON.stringify(m.tabs) === JSON.stringify(erwRt) && quoten.every((q) => m.rt.includes(q)) && m.sf === M.schieflage.length,
        `Methode: Stufentabelle, ${m.tabs.length} Rücktest-Tabellen je Bauzeit und Stufe (${quoten.length} Quoten mit n, gleich daten/jahre_methode.js), Vergleich mit dem Zensus`);
      pruef(/\+41\s%/.test(m.text) && /\u221235\s%/.test(m.text) && /nicht vergleichbar/.test(m.text) && /Prüfgebäude/.test(m.text) && /Denkmale stammen fast alle/.test(m.text),
        "Methode: Schieflage (vor 1919 +41 %, 1979–1990 −35 %), Vorbehalte zum Rücktest, kein Vergleich mit Berlin als Zahl");
      pruef((m.text.match(/visinage/gi) || []).length === 1 && /Methodenvorbild/.test(m.text), "Methode: Vorbild genau einmal genannt, als Methodenvorbild");
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
      return r.fulfill({ status: 200, contentType: "image/png", body: LEERBILD });
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
    pruef(/belegt/.test(pop) && /Baujahr \d{4}/.test(pop) && /Quelle: /.test(pop) && /Belegt aus einer Quelle/.test(pop) && /belegt \(kräftig, mit Rand\)/.test(leg) && linie > 0 && /Beispieldaten/.test(meld) && fehler.length === 0,
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
