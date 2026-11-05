// Prüfung Paket B5 (Zweig 1): Seiten jahre.html, jahre-methode.html, jahre-daten.html.
// Je Seite per file:// und per HTTP (127.0.0.1): lädt bis window.KIEZ_BEREIT, keine Konsolenfehler, axe ohne
// Verstoß, alle Zahlenfelder gefüllt, bei 375 px kein waagrechtes Scrollen, Farbtöne der gerenderten Seite
// und der Kartenfarben außerhalb 20°–70°. Dazu auf jahre.html: Fragen stellen die Karte ein, reduzierte
// Bewegung ohne Animation, Klassenleiste per Klick und Tastatur, Zell-Popup mit Quelle, Hash-Rundreise,
// Vergleichsliste, keine Gebäudedateien geladen. Auf jahre-daten.html: alle vier Downloads, Inhalt geprüft.
// Statisch: verbotene Tokens, Namen und Schriften (Bauplan Abschnitt 5), keine Geviertstriche, Palette.
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
const VERBOTEN = [/#05060B/i, /#EAE7DE/i, /#8BE8D2/i, /Unbounded/i, /Host Grotesk/i, /Newsreader/i, /\bGeist\b/i, /Atlas der Fragen/i, /Jahresring/i, /\bRing\b/, /visinage/i, /—/];
let statischeFarben = [];
for (const f of EIGENE) {
  const t = fs.readFileSync(path.join(WURZEL, f), "utf8");
  const treffer = VERBOTEN.filter((r) => r.test(t)).map(String);
  pruef(treffer.length === 0, `${f}: keine verbotenen Tokens, Namen, Schriften, Geviertstriche ${treffer.join(" ")}`);
  if (/\.(css|js)$/.test(f)) statischeFarben = statischeFarben.concat(t.match(FARBMUSTER) || []);
  pruef(!/\bfetch\s*\(|XMLHttpRequest/.test(t), `${f}: kein fetch/XHR (file://)`);
  pruef(!/daten\/gebaeude\//.test(t), `${f}: keine Gebäudedateien (Zweig 1 färbt keine Gebäude)`);
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
    pruef(!geladen.some((u) => /daten\/gebaeude\//.test(u)), "keine Gebäudedatei geladen");

    if (seite === "jahre.html") {
      // Reduzierte Bewegung: keine CSS-Animation, Kartenstil ohne Übergang, Kamera springt
      pruef(await page.evaluate(() => document.getAnimations().length === 0), "reduzierte Bewegung: keine laufende Animation nach dem Laden");
      pruef(await page.evaluate(() => { const t = window.KIEZ_KARTE.getStyle().transition; return t && t.duration === 0; }), "reduzierte Bewegung: Kartenstil ohne Überblendung (transition 0)");
      pruef(await page.$eval("#j-abspielen", (b) => b.hidden), "reduzierte Bewegung: „Nacheinander“ ausgeblendet");
      const erwartet = { 1: ["spanne", 0, 0, false], 2: ["spanne", 2, 3, false], 3: ["spanne", 4, 7, true], 4: ["spanne", 6, 7, false], 5: ["ueberblick"], 6: ["ueberblick"] };
      for (const n of Object.keys(erwartet)) {
        await page.$eval("#frage-" + n, (e) => e.scrollIntoView({ block: "center" }));
        await page.waitForFunction((n) => document.getElementById("frage-" + n).classList.contains("ist-aktiv"), n, { timeout: 5000 }).catch(() => {});
        await page.waitForTimeout(150);
        const s = await page.evaluate(() => { const J = window.KIEZ_JAHRE, m = J.map; return { a: J.S.ansicht, v: J.S.von, b: J.S.bis, d: J.S.d3, beweg: m.isMoving(), anim: document.getAnimations().length, pitch: m.getPitch() }; });
        const e = erwartet[n];
        const ok = s.a === e[0] && (e.length < 2 || (s.v === e[1] && s.b === e[2] && s.d === e[3]));
        pruef(ok && !s.beweg && s.anim === 0, `Frage ${n}: Karte eingestellt (${s.a} ${s.v}–${s.b}${s.d ? " 3D" : ""}), Kamera steht, keine Animation${ok && !s.beweg && s.anim === 0 ? "" : " " + JSON.stringify(s)}`);
      }
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
      // Zell-Popup
      // erst die Ansicht (schritt setzt die Kamera auf ganz Potsdam), dann nah heran, damit eine Zelle viele Pixel groß ist
      await page.evaluate(() => window.KIEZ_JAHRE.schritt(5));
      await page.evaluate(() => window.KIEZ_KARTE.jumpTo({ center: [13.0645, 52.3989], zoom: 14, pitch: 0 }));
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
