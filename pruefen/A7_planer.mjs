// Abnahme Paket A7 (Planer-Seite): planer.html, planer-methode.html, planer-daten.html.
// Prüft per file:// und HTTP (127.0.0.1): lädt ohne Konsolenfehler, Gewicht beim Start (JS, gzip -9),
// axe ohne Verstoß, Hash-Rundreise, keine Kamerafahrt bei reduzierter Bewegung, 375 px ohne seitliches
// Scrollen, sichtbarer Quellenvermerk an jeder Zahl, Orientierungswerte gekennzeichnet, Luftlinie/Fußweg an
// jeder Zahl, Download-Liste deckt alle Verträge in daten/schema/ ab und ihr Stand stimmt mit daten/ überein.
//
// Kein Netz: Jede Anfrage, die nicht an file:// oder den eigenen Prüfserver geht (Kacheln von basemap.de),
// beantwortet der Prüfbrowser selbst mit einem leeren 1-px-PNG (wie pruefen/seiten.mjs).
//
// Aufruf: node pruefen/A7_planer.mjs [--wurzel <ordner>] [--json <datei>]   Rückgabe 0 = grün, 1 = Befund.
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
const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".json": "application/json" };
const GRENZE_JS_KB = 320;   // 06.11.: +16 KB gz für die Vektor-Grundkarte (daten/grundkarte.js) statt Rasterkacheln

const befunde = [];
const bericht = { stand: new Date().toISOString(), wurzel: WURZEL, laeufe: [] };
function pruef(ok, text) { console.log((ok ? "  ok   " : "  FEHLT ") + text); if (!ok) befunde.push(text); return ok; }

const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (p !== WURZEL && !p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p, (f, d) => { if (f) { a.writeHead(404); a.end(); return; } a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const HTTP = `http://127.0.0.1:${server.address().port}/`;
const FILE = pathToFileURL(WURZEL + path.sep).href;
const eigen = (u) => u.startsWith("file://") || u.startsWith(HTTP) || u.startsWith("data:") || u.startsWith("blob:");
function gz(url) {
  const p = url.startsWith("file://") ? fileURLToPath(url.split(/[?#]/)[0]) : path.join(WURZEL, decodeURIComponent(new URL(url).pathname));
  try { return zlib.gzipSync(fs.readFileSync(p), { level: 9 }).length; } catch { return 0; }
}
const browser = await chromium.launch();

async function oeffnen(basis, datei, { hash = "", bewegung = "reduce", breite = 1440, hoehe = 900, warten = true } = {}) {
  const ctx = await browser.newContext({ viewport: { width: breite, height: hoehe }, reducedMotion: bewegung });
  const page = await ctx.newPage();
  const fehler = [], abgewiesen = [], geladen = [];
  await page.route("**/*", (r) => { const u = r.request().url(); if (eigen(u)) return r.continue(); abgewiesen.push(u); return r.fulfill(fremdAntwort(r.request().url())); });
  page.on("console", (m) => {
    if (m.type() !== "error") return;
    const ort = (m.location() || {}).url || "", text = m.text();
    if (!(/ERR_ABORTED/.test(text) && (!ort || !eigen(ort)))) fehler.push(text.split("\n")[0] + (ort ? " @ " + ort : ""));
  });
  page.on("pageerror", (e) => fehler.push("pageerror: " + e.message));
  page.on("request", (q) => { const u = q.url(); if (eigen(u) && !u.startsWith("data:") && !u.startsWith("blob:")) geladen.push(u.split(/[?#]/)[0]); });
  await page.goto(basis + datei + hash, { waitUntil: "load" });
  if (warten) await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  return { ctx, page, fehler, abgewiesen, geladen };
}
async function axe(page) {
  await page.addScriptTag({ content: AXE });
  const datei = page.url().startsWith("file://");
  return page.evaluate(async (datei) => (await window.axe.run(document, { resultTypes: ["violations"], preload: !datei })).violations.map((v) => v.id + " (" + v.nodes.length + ")"), datei);
}
const jsGewicht = (geladen) => Math.round([...new Set(geladen)].filter((u) => u.endsWith(".js")).reduce((s, u) => s + gz(u), 0) / 1024);
async function warteBereit(page) {
  await page.waitForTimeout(150);
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 60000 });
}
// Sichtbarer Quellenvermerk und Methode an jeder Zahl der Versorgungstabelle und der Legende
async function zahlenPruefen(page) {
  return page.evaluate(() => {
    const sicht = (e) => !!e && e.getClientRects().length > 0 && getComputedStyle(e).visibility !== "hidden";
    const out = { zeilen: 0, ohneQuelle: 0, ohneMethode: 0, orientierung: 0, orientierungMarkiert: 0, ewVermerk: false, quellenListe: 0, legende: null };
    document.querySelectorAll(".vs-zeile").forEach((z) => {
      out.zeilen++;
      const q = z.querySelector(".vs-q"); if (!q || !/Quelle \[\d+\]/.test(q.textContent)) out.ohneQuelle++;
      // Quoten je Raumeinheit (ohne Entfernung) tragen keine Messart, alle anderen genau eine
      const ohneWeg = /^(plaetze_je_kind|plaetze_je_bedarf|schueler_je_kind|ew_je_einrichtung)$/.test(z.dataset.kennzahl || "");
      const m = z.querySelector(".marke-weg");
      if (ohneWeg ? !!m : (!m || !/^(Luftlinie|Fußweg)$/.test(m.textContent))) out.ohneMethode++;
      // „amtlicher Maßstab“ nur mit Richtwert-Zeile
      if (/amtlicher Maßstab/.test(z.textContent) && !z.querySelector(".vs-richt")) out.massstabOhneWert = (out.massstabOhneWert || 0) + 1;
      if (z.classList.contains("vs-zeile--orientierung")) { out.orientierung++; if (/Orientierung, kein Richtwert/.test(z.textContent)) out.orientierungMarkiert++; }
    });
    const ew = document.querySelector(".vs-ew"); out.ewVermerk = !!ew && /Zensus 2022/.test(ew.textContent) && /dl-de\/by-2-0/.test(ew.textContent) && /Daten verändert/.test(ew.textContent);
    out.quellenListe = [...document.querySelectorAll(".vs-quellen li")].filter((li) => /dl-de|ODbL|Lizenz/.test(li.textContent)).length;
    const L = document.getElementById("legende"), v = L && L.querySelector(".legende__vermerk");
    out.legende = L && L.querySelector(".marken") ? { vermerk: sicht(v) && v.textContent.length > 10, methode: /Luftlinie|Fußweg/.test(L.textContent) } : null;
    return out;
  });
}

// Zwei Läufe je Weg: mit den echten Dateien aus daten/ (A6) und mit den Beispieldateien (planer.html?daten=fixtures),
// die auch Fußweg und OpenStreetMap enthalten. Solange <html data-odbl> keine _odbl-Datei nennt, sind Fußweg und
// OSM-Arten mit den echten Daten gesperrt und die Seite fragt keine fehlende Datei an.
const FIX = "?daten=fixtures";
async function planerEcht(basis, art) {
  console.log(`planer.html über ${art}, echte Daten`);
  const { ctx, page, fehler, abgewiesen, geladen } = await oeffnen(basis, "planer.html");
  const js = jsGewicht(geladen);
  pruef(js <= GRENZE_JS_KB, `Startgewicht ${js} KB gz JS mit echten Daten (Grenze ${GRENZE_JS_KB})`);
  pruef(!geladen.some((u) => /\/daten\/fixtures\//.test(u)), "keine Datei aus daten/fixtures/ geladen");
  pruef(await page.evaluate(() => document.getElementById("beispiel").hidden), "kein Hinweis „Beispieldaten“");
  const sperre = await page.evaluate(() => ({
    fuss: document.querySelector('#weg input[value="fuss"]').disabled,
    osm: ["arzt", "apotheke", "supermarkt", "pflege", "spielplatz"].every((a) => { const i = document.querySelector(`#ein input[value="${a}"]`); return !i || i.disabled; }),
    odbl: document.documentElement.getAttribute("data-odbl") }));
  // data-odbl muss zu daten/ passen: genannt = vorhanden; Fußweg offen nur mit beiden Fußweg-Dateien, OSM-Arten nur mit einrichtungen_odbl.js
  const genannt = (sperre.odbl || "").split(/[\s,]+/).filter(Boolean), da = (f) => fs.existsSync(path.join(WURZEL, "daten", f));
  const alleOdbl = ["einrichtungen_odbl.js", "erreichbar_fuss_odbl.js", "planer_fuss_odbl.js"];
  const passt = genannt.every(da) && alleOdbl.every((f) => genannt.includes(f) || !da(f));
  const fussErw = !(genannt.includes("erreichbar_fuss_odbl.js") && genannt.includes("planer_fuss_odbl.js")), osmErw = !genannt.includes("einrichtungen_odbl.js");
  pruef(sperre.odbl !== null && passt && sperre.fuss === fussErw && sperre.osm === osmErw,
    `data-odbl="${sperre.odbl}" passt zu daten/ (${passt}); Fußweg gesperrt ${sperre.fuss} (erwartet ${fussErw}), OSM-Arten gesperrt ${sperre.osm} (erwartet ${osmErw})`);
  const chips = await page.$$eval('#ein input[name="ein"]:not(:disabled)', (l) => l.map((i) => i.value));
  pruef(chips.includes("kita") && chips.includes("grundschule") && chips.length >= 5, `Einrichtungs-Chips aus den echten Daten: ${chips.join(", ")}`);
  await page.check('#zu input[value="kita"]', { force: true }); await warteBereit(page);
  const zl = await page.evaluate(() => ({ sicht: window.KIEZ_KARTE.getLayoutProperty("zellen", "visibility"), n: window.KIEZ_KARTE.querySourceFeatures("zellen").length, ein: (window.KIEZ_EINRICHTUNGEN || {}).features?.length }));
  pruef(zl.sicht === "visible" && zl.n > 0 && zl.ein > 600, `Kita (Luftlinie) mit echten Daten: ${zl.n} Zellen gezeichnet, ${zl.ein} Einrichtungen`);
  // Echte Daten rechnen auf Planungsräumen (A6 nach H1): Ebene Planungsräume ist voreingestellt, 403 = Babelsberg Süd
  const ebene = await page.evaluate(() => ({ wert: document.getElementById("raumebene").value, n: document.querySelectorAll("#raeume .treffer").length, src: window.KIEZ_KARTE.getSource("raum").serialize().data.features.length }));
  pruef(ebene.wert === "pr" && ebene.n === 19 && ebene.src === 19, `Raumebene Planungsräume voreingestellt: ${ebene.wert}, ${ebene.n} in der Liste, ${ebene.src} Flächen in der Karte`);
  await page.click('#raeume .treffer[data-nr="403"]'); await warteBereit(page);
  const z = await zahlenPruefen(page);
  pruef(z.zeilen > 5 && z.ohneQuelle === 0 && z.ohneMethode === 0 && !z.massstabOhneWert && z.ewVermerk && z.quellenListe > 0 && z.orientierung === z.orientierungMarkiert,
    `Versorgungstabelle mit echten Daten: ${z.zeilen} Zeilen, ohne Quelle ${z.ohneQuelle}, Messart falsch ${z.ohneMethode}, „amtlicher Maßstab“ ohne Richtwert ${z.massstabOhneWert || 0}, Orientierung ${z.orientierungMarkiert}/${z.orientierung}`);
  // Wechsel auf Stadtteile: Hinweis statt Tabelle, keine falsche Zuordnung; zurück auf Planungsräume: Tabelle wieder da
  await page.selectOption("#raumebene", "st"); await warteBereit(page);
  await page.click('#raeume .treffer[data-nr="13"]'); await warteBereit(page);
  const st = await page.evaluate(() => ({ zeilen: document.querySelectorAll(".vs-zeile").length, text: document.getElementById("vs-inhalt").textContent, hash: location.hash, n: window.KIEZ_KARTE.getSource("raum").serialize().data.features.length }));
  await page.selectOption("#raumebene", "pr"); await warteBereit(page);
  await page.click('#raeume .treffer[data-nr="403"]'); await warteBereit(page);
  const zurueck = await page.evaluate(() => ({ zeilen: document.querySelectorAll(".vs-zeile").length, hash: location.hash }));
  pruef(st.zeilen === 0 && /Planungsräumen/.test(st.text) && /raum=st&r=13/.test(st.hash) && st.n === 32 && zurueck.zeilen === z.zeilen && /raum=pr&r=403/.test(zurueck.hash),
    `Ebene Stadtteile: Hinweis statt Tabelle (${st.zeilen} Zeilen, ${st.n} Flächen), zurück auf Planungsräume ${zurueck.zeilen} Zeilen (${zurueck.hash.replace(/&k=.*$/, "")})`);
  const popup = await page.evaluate(() => {
    const m = window.KIEZ_KARTE, f = m.queryRenderedFeatures({ layers: ["ein"] })[0]; if (!f) return null;
    const p = m.project(f.geometry.coordinates); m.fire("click", { point: p, lngLat: m.unproject(p), originalEvent: {} });
    const c = document.querySelector(".maplibregl-popup-content"); const t = c ? c.textContent : ""; document.querySelectorAll(".maplibregl-popup").forEach((x) => x.remove()); return t;
  });
  pruef(!!popup && /dl-de/.test(popup) && /Daten verändert/.test(popup), `Klick auf Einrichtung mit echten Daten: ${(popup || "").slice(0, 90)}…`);
  // Audit K14/K24: Zähler und Nenner („a von b“) und ganz Potsdam an den Zeilen, Vergleich aller Planungsräume
  const zn = await page.evaluate(() => {
    const P = window.KIEZ_PLANER, R = P.raeume["403"], fmt = new Intl.NumberFormat("de-DE");
    const mitZn = R.werte.filter((w) => w.zaehler != null && w.nenner != null).length;
    const texte = [...document.querySelectorAll(".vs-zn")].map((e) => e.textContent);
    const erste = R.werte.find((w) => w.zaehler != null && w.nenner != null);
    return { mitZn, zn: texte.length, passt: !!erste && texte.some((x) => x.startsWith(fmt.format(erste.zaehler) + " von " + fmt.format(erste.nenner))),
      stadt: document.querySelectorAll(".vs-stadt").length, gesamt: P.gesamt ? P.gesamt.werte.length : 0 };
  });
  pruef(zn.mitZn > 0 && zn.zn === zn.mitZn && zn.passt && zn.stadt === zn.gesamt && zn.gesamt > 0,
    `Zähler und Nenner an ${zn.zn} von ${zn.mitZn} Zeilen („a von b“ wie planer.js ${zn.passt}), ganz Potsdam an ${zn.stadt} Zeilen (gesamt ${zn.gesamt})`);
  await page.click("#vg-laden"); await warteBereit(page);
  const vg = await page.evaluate(() => {
    const P = window.KIEZ_PLANER, sel = document.getElementById("vg-kennzahl"), tab = document.querySelector(".vg-tabelle");
    const zeilen = tab ? tab.querySelectorAll("tbody tr").length : 0, fuss = tab ? tab.querySelector("tfoot")?.textContent || "" : "";
    const opt = sel.options.length; sel.selectedIndex = Math.min(4, opt - 1); sel.dispatchEvent(new Event("change"));
    const zeilen2 = document.querySelectorAll(".vg-tabelle tbody tr").length;
    return { zeilen, zeilen2, fuss, opt, raeume: Object.keys(P.raeume).length, caption: !!(tab && tab.querySelector("caption")), vsZeilen: document.querySelectorAll(".vs-zeile").length };
  });
  pruef(vg.zeilen === vg.raeume && vg.zeilen2 === vg.raeume && /Ganz Potsdam/.test(vg.fuss) && vg.opt > 5 && vg.caption && vg.vsZeilen === z.zeilen,
    `Vergleich „Alle Planungsräume“: ${vg.zeilen} Zeilen (Räume ${vg.raeume}), Zeile ganz Potsdam ${/Ganz Potsdam/.test(vg.fuss)}, ${vg.opt} Kennzahlen, nach Wechsel ${vg.zeilen2} Zeilen, Tabellenzeilen der Versorgung unverändert ${vg.vsZeilen}`);
  const verstoss = await axe(page);
  pruef(verstoss.length === 0, `axe mit echten Daten: ${verstoss.length} Verstöße ${verstoss.join(", ")}`);
  pruef(fehler.length === 0, `Konsole ohne Fehler mit echten Daten (${fehler.length}${fehler.length ? ": " + fehler.slice(0, 3).join(" | ") : ""})`);
  bericht.laeufe.push({ seite: "planer.html", art: art + ", echt", js_kb_gz: js, axe: verstoss.length, fehler: fehler.length, abgewiesen: abgewiesen.length });
  await ctx.close();
}

async function planer(basis, art) {
  console.log(`planer.html über ${art}, Beispieldaten`);
  const { ctx, page, fehler, abgewiesen, geladen } = await oeffnen(basis, "planer.html" + FIX);
  const js = jsGewicht(geladen);
  pruef(js <= GRENZE_JS_KB, `Startgewicht ${js} KB gz JS (Grenze ${GRENZE_JS_KB}); geladen: ${[...new Set(geladen)].filter((u) => u.endsWith(".js")).map((u) => u.split("/").slice(-2).join("/")).join(", ")}`);
  const zellenAmStart = geladen.some((u) => u.endsWith("/daten/zellen.js"));
  pruef(!zellenAmStart, "zellen.js lädt nicht beim Start, erst bei einer Entfernung");
  const planerAmStart = geladen.some((u) => /\/daten\/(fixtures\/)?planer(_fuss_odbl)?\.js$/.test(u));
  pruef(!planerAmStart, "Versorgungsdatei lädt nicht beim Start, erst bei der Wahl einer Raumeinheit");
  const beispiel = await page.evaluate(() => !document.getElementById("beispiel").hidden);
  pruef(beispiel, "Hinweis „Beispieldaten“ sichtbar, solange Fixtures geladen sind");
  // Chips je Art
  const chips = await page.$$eval('#ein input[name="ein"]', (l) => l.map((i) => i.value));
  pruef(chips.length >= 5, `Einrichtungs-Chips: ${chips.join(", ")}`);
  // Erreichbarkeit Luftlinie, dann Fußweg
  await page.check('#zu input[value="kita"]', { force: true }); await warteBereit(page);
  const zl = await page.evaluate(() => ({ sicht: window.KIEZ_KARTE.getLayoutProperty("zellen", "visibility"), n: window.KIEZ_KARTE.querySourceFeatures("zellen").length }));
  pruef(zl.sicht === "visible" && zl.n > 0, `Erreichbarkeit Kita (Luftlinie) als Zellthema: ${zl.n} Zellen gezeichnet`);
  // Raumeinheit wählen: Versorgungstabelle
  await page.click('#raeume .treffer[data-nr="13"]'); await warteBereit(page);
  let z = await zahlenPruefen(page);
  pruef(z.zeilen > 0 && z.ohneQuelle === 0 && z.ohneMethode === 0 && z.ewVermerk && z.quellenListe > 0,
    `Versorgungstabelle Luftlinie: ${z.zeilen} Zeilen, ohne Quelle ${z.ohneQuelle}, ohne Methode ${z.ohneMethode}, Einwohner mit Vermerk ${z.ewVermerk}, ${z.quellenListe} Vermerke mit Lizenz`);
  pruef(z.orientierung > 0 && z.orientierung === z.orientierungMarkiert, `Orientierungswerte gekennzeichnet: ${z.orientierungMarkiert} von ${z.orientierung}`);
  pruef(z.legende && z.legende.vermerk && z.legende.methode, `Legende der Entfernung mit Methode und sichtbarem Vermerk`);
  // Klick auf eine Zelle: Entfernung mit Methode und vollständigem dl-de-Vermerk (Bearbeitungshinweis + Link)
  const zelle = await page.evaluate(() => {
    // eine Zelle im gewählten Stadtteil 13: der Klick darf die Wahl nicht aufheben
    const m = window.KIEZ_KARTE, mitte = (f) => { const r = f.geometry.coordinates[0]; return m.project([(r[0][0] + r[2][0]) / 2, (r[0][1] + r[2][1]) / 2]); };
    const f = m.queryRenderedFeatures({ layers: ["zellen"] }).find((z) => m.queryRenderedFeatures(mitte(z), { layers: ["raum-flaeche"] }).some((x) => x.properties.nr === "13")); if (!f) return null;
    const p = mitte(f);
    m.fire("click", { point: p, lngLat: m.unproject(p), originalEvent: {} });
    const box = [...document.querySelectorAll(".maplibregl-popup-content")].find((x) => /Gitterzelle/.test(x.textContent));
    const t = box ? { text: box.textContent, link: !!box.querySelector('a[href*="govdata.de/dl-de/by-2-0"]') } : null;
    document.querySelectorAll(".maplibregl-popup").forEach((x) => x.remove()); return t;
  });
  pruef(!!zelle && /Luftlinie/.test(zelle.text) && /Daten verändert \(eigene Berechnung\)/.test(zelle.text) && zelle.link,
    `Klick auf Zelle: Entfernung mit Methode und dl-de-Vermerk samt Bearbeitungshinweis und Lizenzlink (${zelle ? "gefunden" : "kein Popup"})`);
  // Ein Klick auf eine Zelle hebt die Wahl der Raumeinheit nicht auf (die Zelle kann in einer anderen liegen)
  const gewaehlt = await page.$eval('#raeume .treffer[aria-pressed="true"]', (b) => b.dataset.nr).catch(() => null);
  pruef(gewaehlt === "13", `Klick auf eine Zelle im gewählten Stadtteil hebt die Wahl nicht auf (gewählt: ${gewaehlt})`);
  if (gewaehlt !== "13") { await page.click('#raeume .treffer[data-nr="13"]'); await warteBereit(page); }
  await page.check('#weg input[value="fuss"]', { force: true }); await warteBereit(page);
  z = await zahlenPruefen(page);
  const odbl = await page.evaluate(() => !document.getElementById("fuss-odbl").hidden && /ODbL/.test(document.getElementById("legende").textContent + document.querySelector(".vs-quellen").textContent));
  const fussMarke = await page.$$eval(".vs-zeile .marke-weg", (l) => l.every((m) => m.textContent === "Fußweg"));
  pruef(z.zeilen > 0 && z.ohneQuelle === 0 && fussMarke && odbl, `Fußweg: ${z.zeilen} Zeilen mit „Fußweg“, ODbL-Vermerk sichtbar ${odbl}`);
  // OSM-Einrichtungen und Popup einer Einrichtung
  await page.check('#ein input[value="arzt"]', { force: true }); await warteBereit(page);
  const osm = await page.evaluate(() => window.KIEZ_KARTE.getLayoutProperty("ein_odbl", "visibility"));
  pruef(osm === "visible", "OSM-Einrichtungen (ODbL) laden erst bei Auswahl und werden gezeigt");
  const popup = await page.evaluate(() => {
    const m = window.KIEZ_KARTE, f = m.queryRenderedFeatures({ layers: ["ein"] })[0]; if (!f) return null;
    const p = m.project(f.geometry.coordinates); m.fire("click", { point: p, lngLat: m.unproject(p), originalEvent: {} });
    const c = document.querySelector(".maplibregl-popup-content"); return c ? c.textContent : "";
  });
  pruef(!!popup && /Plätze|Schüler|Lage/.test(popup) && /dl-de|ODbL/.test(popup), `Klick auf Einrichtung zeigt Art, Plätze und Quelle: ${(popup || "").slice(0, 90)}…`);
  await page.evaluate(() => document.querySelectorAll(".maplibregl-popup").forEach((p) => p.remove()));
  const verstoss = await axe(page);
  pruef(verstoss.length === 0, `axe: ${verstoss.length} Verstöße ${verstoss.join(", ")}`);
  pruef(fehler.length === 0, `Konsole ohne Fehler (${fehler.length}${fehler.length ? ": " + fehler.slice(0, 3).join(" | ") : ""}; lokal ersetzte Fremdabrufe: ${abgewiesen.length})`);
  bericht.laeufe.push({ seite: "planer.html", art, js_kb_gz: js, axe: verstoss.length, fehler: fehler.length, abgewiesen: abgewiesen.length });
  await ctx.close();
}

async function rundreise(basis, art) {
  const ziel = "#ein=kita,gs,arzt&zu=gs&weg=fuss&raum=st&r=14&k=13.10/52.39000/13.06000/0/0";
  const zustand = (p) => p.evaluate(() => ({
    ein: [...document.querySelectorAll('#ein input:checked')].map((i) => i.value).sort().join(","),
    zu: (document.querySelector('#zu input:checked') || {}).value, weg: (document.querySelector('#weg input:checked') || {}).value,
    r: (document.querySelector('#raeume .treffer[aria-pressed="true"]') || { dataset: {} }).dataset.nr,
    zellen: window.KIEZ_KARTE.getLayoutProperty("zellen", "visibility"),
    hash: location.hash.replace(/&k=.*$/, ""), k: (location.hash.match(/k=([^&]*)/) || [])[1] }));
  const a = await oeffnen(basis, "planer.html" + FIX, { hash: ziel });
  const z1 = await zustand(a.page), h1 = await a.page.evaluate(() => location.hash); await a.ctx.close();
  const b = await oeffnen(basis, "planer.html" + FIX, { hash: h1 });
  const z2 = await zustand(b.page); await b.ctx.close();
  const kGleich = (x, y) => { const p = (s) => (s || "").split("/").map(Number); const [u, v] = [p(x), p(y)]; return u.length === 5 && u.every((w, i) => Math.abs(w - v[i]) < 0.01); };
  pruef(z1.ein === "arzt,grundschule,kita" && z1.zu === "grundschule" && z1.weg === "fuss" && z1.r === "14" && z1.zellen === "visible"
    && JSON.stringify({ ...z1, k: 0 }) === JSON.stringify({ ...z2, k: 0 }) && kGleich(z1.k, z2.k),
    `Hash-Rundreise über ${art}: ${z1.hash}&k=${z1.k} -> neu geladen gleich (${z2.hash}&k=${z2.k})`);
}

async function raumebeneFremd(ohneGrenzen) {
  // Versorgungsdatei auf Planungsräumen, gewählt ist ein Stadtteil: keine falsche Zuordnung, Hinweis statt Tabelle.
  // ohneGrenzen: planungsraeume.js fehlt (404), die Karte kennt nur Stadtteile
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  const page = await ctx.newPage(), fehler = [];
  page.on("pageerror", (e) => fehler.push(e.message));
  await page.route("**/*", async (r) => {
    const u = r.request().url();
    if (!eigen(u)) return r.fulfill(fremdAntwort(r.request().url()));
    if (ohneGrenzen && /\/daten\/planungsraeume\.js$/.test(u.split(/[?#]/)[0])) return r.fulfill({ status: 404, body: "" });
    if (/\/daten\/fixtures\/planer\.js$/.test(u.split(/[?#]/)[0])) {
      const t = fs.readFileSync(path.join(WURZEL, "daten", "fixtures", "planer.js"), "utf8").replace(/"raumebene":\s*"stadtteil"/, '"raumebene":"planungsraum"');
      return r.fulfill({ status: 200, contentType: "text/javascript", body: t });
    }
    return r.continue();
  });
  await page.goto(HTTP + "planer.html" + FIX + "#r=13", { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  const z = await page.evaluate(() => ({ zeilen: document.querySelectorAll(".vs-zeile").length, text: document.getElementById("vs-inhalt").textContent, ebene: window.KIEZ_PLANER && window.KIEZ_PLANER.raumebene,
    optionen: [...document.querySelectorAll("#raumebene option")].map((o) => o.value).join(",") }));
  const erwartet = ohneGrenzen ? /Grenzen fehlen der Karte noch/ : /Ebene „Planungsräume“ wählen/;
  pruef(z.ebene === "planungsraum" && z.zeilen === 0 && erwartet.test(z.text) && z.optionen === (ohneGrenzen ? "st" : "pr,st") && fehler.length === 0,
    `Datei auf Planungsräumen, Stadtteil gewählt, ${ohneGrenzen ? "ohne" : "mit"} Grenzen der Planungsräume: Hinweis statt Tabelle (${z.zeilen} Zeilen, Ebenen ${z.optionen}, Fehler ${fehler.length})`);
  await ctx.close();
}

async function fussFehlschlag() {
  // planer_fuss_odbl.js scheitert beim ersten Mal: Rückfall auf Luftlinie mit Meldung, beim nächsten Wechsel neuer Versuch
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce" });
  const page = await ctx.newPage(), fehler = []; let versuche = 0;
  page.on("pageerror", (e) => fehler.push(e.message));
  await page.route("**/*", (r) => {
    const u = r.request().url();
    if (!eigen(u)) return r.fulfill(fremdAntwort(r.request().url()));
    if (/\/daten\/fixtures\/planer_fuss_odbl\.js$/.test(u.split(/[?#]/)[0]) && ++versuche === 1) return r.fulfill({ status: 404, body: "" });
    return r.continue();
  });
  await page.goto(HTTP + "planer.html" + FIX + "#r=13", { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  await page.check('#weg input[value="fuss"]', { force: true }); await warteBereit(page);
  const a = await page.evaluate(() => ({ weg: document.querySelector('#weg input:checked').value, meldung: document.getElementById("kartenstatus").textContent + document.getElementById("teilen-hinweis").textContent, zeilen: document.querySelectorAll(".vs-zeile").length }));
  await page.check('#weg input[value="fuss"]', { force: true }); await warteBereit(page);
  const b = await page.evaluate(() => ({ weg: document.querySelector('#weg input:checked').value, fuss: [...document.querySelectorAll(".vs-zeile .marke-weg")].filter((m) => m.textContent === "Fußweg").length }));
  pruef(a.weg === "luft" && /Fußweg-Tabelle/.test(a.meldung) && a.zeilen > 0 && b.weg === "fuss" && b.fuss > 0 && versuche === 2 && fehler.length === 0,
    `Fußweg-Tabelle scheitert einmal: Rückfall auf Luftlinie mit Meldung (${a.weg}, ${a.zeilen} Zeilen), zweiter Versuch lädt (${b.weg}, ${b.fuss} Zeilen, ${versuche} Abrufe)`);
  await ctx.close();
}

async function ruhig() {
  // Reduzierte Bewegung: Klick auf Raumeinheit und Frage bewegen die Kamera nicht; Zoomknopf springt (eine Bewegung, keine Fahrt)
  const { ctx, page } = await oeffnen(HTTP, "planer.html", { bewegung: "reduce" });
  await page.evaluate(() => { window.__bew = 0; window.KIEZ_KARTE.on("move", () => window.__bew++); });
  await page.click('#raeume .treffer[data-nr="403"]'); await page.click('.frage-knopf[data-frage="0"]'); await warteBereit(page);
  const nachKlick = await page.evaluate(() => window.__bew);
  await page.click("#zoom-raum"); await page.waitForTimeout(800);
  const nachZoom = await page.evaluate(() => window.__bew);
  pruef(nachKlick === 0 && nachZoom <= 1, `reduzierte Bewegung: Klicks bewegen die Kamera nicht (${nachKlick}), Zoom springt (${nachZoom} Bewegung)`);
  await ctx.close();
  const b = await oeffnen(HTTP, "planer.html", { bewegung: "no-preference" });
  await b.page.click('.frage-knopf[data-frage="1"]'); await warteBereit(b.page); await b.page.click("#zoom-raum"); await b.page.waitForTimeout(1200);
  pruef(b.fehler.length === 0, `ohne reduzierte Bewegung fehlerfrei (${b.fehler.length})`);
  await b.ctx.close();
}

async function handy(basis, art) {
  for (const datei of ["planer.html", "planer-methode.html", "planer-daten.html"]) {
    const { ctx, page, fehler } = await oeffnen(basis, datei, { breite: 375, hoehe: 740, warten: datei !== "planer-daten.html" });
    if (datei === "planer.html") { await page.click("#seite-griff"); await page.click('#raeume .treffer[data-nr="403"]'); await page.waitForTimeout(500); }
    const w = await page.evaluate(() => ({ s: Math.max(document.documentElement.scrollWidth, document.body.scrollWidth), c: document.documentElement.clientWidth }));
    pruef(w.s <= w.c, `${datei} bei 375 px über ${art}: kein seitliches Scrollen (scrollWidth ${w.s}, Breite ${w.c})`);
    if (datei === "planer.html") { const v = await axe(page); pruef(v.length === 0, `axe bei 375 px mit offener Leiste: ${v.length} ${v.join(", ")}`); }
    pruef(fehler.length === 0, `${datei} bei 375 px ohne Konsolenfehler (${fehler.length}${fehler.length ? ": " + fehler[0] : ""})`);
    await ctx.close();
  }
}

async function textseiten(basis, art) {
  const m = await oeffnen(basis, "planer-methode.html");
  const r = await m.page.evaluate(() => ({ zeilen: document.querySelectorAll("#richtwerte tbody tr").length,
    orient: [...document.querySelectorAll("#richtwerte tbody tr")].filter((t) => /Orientierung, kein Richtwert/.test(t.textContent)).length,
    vermerk: [...document.querySelectorAll("#richtwerte tbody tr")].every((t) => /dl-de|ODbL|CC BY|Lizenz/.test(t.textContent)) }));
  // Audit K28: Prüfwerte im Text aus planer.js (pruefwerte), nicht fest im HTML
  const pw = await m.page.evaluate(() => {
    const P = window.KIEZ_PLANER || {}, PW = P.pruefwerte || {}, n = [...document.querySelectorAll("[data-pw]")];
    const st = { ganz: { maximumFractionDigits: 0 }, eins: { minimumFractionDigits: 1, maximumFractionDigits: 1 }, genau: { maximumFractionDigits: 3 } };
    const falsch = n.filter((e) => { const x = PW[e.dataset.pw]; return !x || e.textContent !== new Intl.NumberFormat("de-DE", st[e.dataset.format || "genau"]).format(x.wert); }).map((e) => e.dataset.pw);
    const belege = [...document.querySelectorAll("[data-pw-beleg]")].filter((e) => !PW[e.dataset.pwBeleg] || e.textContent !== PW[e.dataset.pwBeleg].beleg).length;
    return { n: n.length, falsch, belege, schluessel: Object.keys(PW).length };
  });
  pruef(pw.n >= 6 && !pw.falsch.length && !pw.belege && pw.schluessel >= 4,
    `planer-methode.html über ${art}: ${pw.n} Prüfwerte aus planer.js gefüllt (${pw.schluessel} mit Beleg), abweichend ${pw.falsch.join(", ") || "keiner"}, Beleg falsch ${pw.belege}`);
  const v1 = await axe(m.page);
  pruef(r.zeilen > 0 && r.orient > 0 && r.vermerk && v1.length === 0 && m.fehler.length === 0,
    `planer-methode.html über ${art}: ${r.zeilen} Maßstäbe aus der Datei, ${r.orient} als Orientierung, Vermerk je Zeile ${r.vermerk}, axe ${v1.length}, Fehler ${m.fehler.length}`);
  await m.ctx.close();
  const d = await oeffnen(basis, "planer-daten.html", { warten: false });
  const liste = await d.page.$$eval("[data-datei]", (l) => l.map((e) => ({ datei: e.dataset.datei, schema: e.dataset.schema, da: e.dataset.da, odbl: e.dataset.odbl, href: (e.querySelector("a.datei") || {}).getAttribute?.("href") || null, text: e.textContent })));
  // Jeder Link in daten/ (auch die GIS-Exporte und Steckbriefe) führt zu einer Datei
  const links = await d.page.$$eval('a[href^="daten/"]', (l) => l.map((a) => a.getAttribute("href").split(/[?#]/)[0]));
  const tot = links.filter((h) => !fs.existsSync(path.join(WURZEL, h)));
  pruef(links.length > 0 && tot.length === 0, `planer-daten.html über ${art}: ${links.length} Links in daten/, ins Leere ${tot.length}${tot.length ? " (" + tot.join(", ") + ")" : ""}`);
  const v2 = await axe(d.page);
  pruef(v2.length === 0 && d.fehler.length === 0, `planer-daten.html über ${art}: axe ${v2.length}, Fehler ${d.fehler.length}`);
  await d.ctx.close();
  return liste;
}

async function steckbriefUndKita(basis, art) {
  // K26: Die Kita-Frage der Startseite öffnet den Planer im Fußweg, und planer.js versteht den Hash so.
  const start = fs.readFileSync(path.join(WURZEL, "index.html"), "utf8");
  const kitaLink = (start.match(/href="(planer\.html#[^"]*zu=kita[^"]*)"/) || [])[1] || "";
  pruef(/(?:#|&amp;)weg=fuss(?:&|$)/.test(kitaLink), `index.html: Kita-Frage verlinkt den Planer im Fußweg (${kitaLink || "kein Link"})`);
  const k = await oeffnen(basis, "planer.html", { hash: "#" + kitaLink.split("#")[1].replace(/&amp;/g, "&") + "&r=403" });
  const kz = await k.page.evaluate(() => ({ weg: (document.querySelector("#weg input:checked") || {}).value, zu: (document.querySelector("#zu input:checked") || {}).value,
    odbl: !document.getElementById("fuss-odbl").hidden,
    sb: [...document.querySelectorAll("#vs-inhalt .vs-steckbrief a.knopf")].map((a) => ({ href: a.getAttribute("href"), text: a.textContent })),
    hinweis: (document.querySelector("#vs-inhalt .vs-steckbrief + .fuss") || {}).textContent || "" }));
  pruef(kz.weg === "fuss" && kz.zu === "kita" && kz.odbl, `Kita-Link über ${art}: Planer zeigt Fußweg zur Kita, ODbL-Vermerk sichtbar (${kz.weg}, ${kz.zu}, ${kz.odbl})`);
  // K25: Knopf „Steckbrief (A4)“ in der Versorgung führt zur Datei des gewählten Planungsraums, mit Luftlinien-Hinweis
  const sb = kz.sb[0] || {};
  pruef(kz.sb.length === 1 && /\/export\/steckbriefe\/403\.html$/.test(sb.href) && fs.existsSync(path.join(WURZEL, sb.href)) && /Steckbrief \(A4\)/.test(sb.text) && /Luftlinie/.test(kz.hinweis),
    `Versorgung 403 über ${art}: Knopf „Steckbrief (A4)“ auf ${sb.href || "–"}, Datei vorhanden, Hinweis Luftlinie`);
  await k.ctx.close();
  // Beispieldaten (Stadtteile) haben keinen Steckbrief: kein Knopf
  const f = await oeffnen(basis, "planer.html" + FIX, { hash: "#r=13" });
  const fz = await f.page.evaluate(() => ({ zeilen: document.querySelectorAll(".vs-zeile").length, sb: document.querySelectorAll(".vs-steckbrief").length }));
  pruef(fz.zeilen > 0 && fz.sb === 0, `Beispieldaten über ${art}: Versorgung ohne Steckbrief-Knopf (${fz.zeilen} Zeilen, ${fz.sb} Knöpfe)`);
  await f.ctx.close();
  // planer-daten.html listet alle Steckbriefe, je einer je Datei in daten/export/steckbriefe/
  const d = await oeffnen(basis, "planer-daten.html", { warten: false });
  const liste = await d.page.$$eval('.steckbriefliste a[href*="export/steckbriefe/"]', (l) => l.map((a) => a.getAttribute("href").split("/").pop()));
  await d.ctx.close();
  const dateien = fs.readdirSync(path.join(WURZEL, "daten", "export", "steckbriefe")).filter((x) => x.endsWith(".html")).sort();
  pruef(dateien.length > 0 && JSON.stringify([...liste].sort()) === JSON.stringify(dateien),
    `planer-daten.html über ${art}: ${liste.length} Steckbriefe verlinkt, ${dateien.length} Dateien in daten/export/steckbriefe/`);
}

function downloadsPruefen(liste) {
  const schemaDir = path.join(WURZEL, "daten", "schema");
  const schemas = fs.readdirSync(schemaDir).filter((f) => f.endsWith(".json")).map((f) => ({ f, s: JSON.parse(fs.readFileSync(path.join(schemaDir, f), "utf8")) }));
  const fehlend = schemas.filter(({ f }) => !liste.some((e) => e.schema === f)).map(({ f }) => f);
  pruef(fehlend.length === 0, `Download-Liste deckt alle ${schemas.length} Verträge ab${fehlend.length ? " (fehlen: " + fehlend.join(", ") + ")" : ""}`);
  let falsch = [];
  for (const e of liste) {
    const s = (schemas.find((x) => x.f === e.schema) || {}).s || {};
    if (s["x-datei"] !== e.datei) falsch.push(`${e.schema}: Datei ${e.datei} statt ${s["x-datei"]}`);
    const odbl = /_odbl/.test(e.datei);
    if ((e.odbl === "ja") !== odbl || (odbl && !/Open Database License/.test(e.text)) || (!odbl && /Open Database License/.test(e.text))) falsch.push(`${e.datei}: Lizenzgrenze`);
    const muster = path.join(WURZEL, "daten", e.datei.replace("*", "11"));
    const da = e.datei.includes("*") ? fs.existsSync(path.dirname(muster)) && fs.readdirSync(path.dirname(muster)).some((x) => x.endsWith(".js")) : fs.existsSync(muster);
    if ((e.da === "ja") !== da) falsch.push(`${e.datei}: Liste sagt ${e.da === "ja" ? "vorhanden" : "folgt"}, in daten/ ${da ? "vorhanden" : "fehlt"}`);
    if (e.da === "ja" && (!e.href || !fs.existsSync(path.join(WURZEL, e.href)))) falsch.push(`${e.datei}: Link ${e.href} führt ins Leere`);
    if (e.da !== "ja" && e.href) falsch.push(`${e.datei}: Link trotz „folgt“`);
  }
  pruef(falsch.length === 0, `Download-Liste: Lizenzgrenze, Stand und Links stimmen mit daten/ überein${falsch.length ? " (" + falsch.join("; ") + ")" : ""}`);
}

try {
  for (const [basis, art] of [[FILE, "file://"], [HTTP, "HTTP"]]) {
    await planerEcht(basis, art);
    await planer(basis, art);
    await rundreise(basis, art);
    await handy(basis, art);
    const liste = await textseiten(basis, art);
    await steckbriefUndKita(basis, art);
    if (art === "HTTP") downloadsPruefen(liste);
  }
  await raumebeneFremd(true);
  await raumebeneFremd(false);
  await fussFehlschlag();
  await ruhig();
} catch (e) { pruef(false, "Abbruch: " + (e && e.message ? e.message.split("\n")[0] : e)); }
await browser.close(); server.close();
bericht.befunde = befunde;
const j = arg("--json"); if (j) fs.writeFileSync(j, JSON.stringify(bericht, null, 1));
console.log(befunde.length ? `\n${befunde.length} Befund(e).` : "\nA7 grün.");
process.exit(befunde.length ? 1 : 0);
