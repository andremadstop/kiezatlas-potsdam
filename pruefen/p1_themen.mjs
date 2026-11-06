// Vertragsprobe Paket P1: themen.js gegen daten/schema/themen.md, per file:// und per HTTP.
// Prüft die Teile, die heute noch keine Seite nutzt (Ebenen-Register, Nachladen, Zellwerte, eigene
// Klassen), dazu Objektumfang, Themen-Schlüssel und Gewicht. Fixture: daten/fixtures/erreichbar.js.
//
// Aufruf:  node pruefen/p1_themen.mjs [--wurzel <ordner>]      Rückgabe 0 = grün, 1 = Befund.
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import zlib from "node:zlib";
import { fileURLToPath, pathToFileURL } from "node:url";

const HIER = path.dirname(fileURLToPath(import.meta.url));
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const WURZEL = path.resolve(arg("--wurzel", path.join(HIER, "..")));
const LEERBILD = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
// Grundkarte (Vektor): Kacheln und Schriften als leere Protobuf-Antwort, alles andere als leeres PNG
const fremdAntwort = (u) => /\.pbf(\?|$)/.test(u) ? { status: 200, contentType: "application/x-protobuf", body: Buffer.alloc(0) } : { status: 200, contentType: "image/png", body: LEERBILD };
const befunde = [];
function pruef(ok, text) { console.log((ok ? "  ok   " : "  FEHLT ") + text); if (!ok) befunde.push(text); }

const gz = zlib.gzipSync(fs.readFileSync(path.join(WURZEL, "themen.js")), { level: 9 }).length;
pruef(gz <= 6 * 1024, `themen.js ${(gz / 1024).toFixed(2)} KB gz (Vertrag: höchstens 6 KB)`);

const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (!p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p, (f, d) => { if (f) { a.writeHead(404); a.end(); return; } a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const HTTP = `http://127.0.0.1:${server.address().port}/`;
const FILE = pathToFileURL(WURZEL + path.sep).href;
const eigen = (u) => u.startsWith(HTTP) || u.startsWith("file://") || u.startsWith("data:") || u.startsWith("blob:");
const browser = await chromium.launch();

async function probe(basis, art) {
  console.log(`karte.html über ${art}`);
  const ctx = await browser.newContext({ reducedMotion: "reduce" });
  const page = await ctx.newPage();
  const konsole = [], seitenfehler = [];
  await page.route("**/*", (r) => eigen(r.request().url()) ? r.continue() : r.fulfill(fremdAntwort(r.request().url())));
  page.on("console", (m) => { if (m.type() === "error") konsole.push(m.text()); });
  page.on("pageerror", (e) => seitenfehler.push(e.message));
  await page.goto(basis + "karte.html", { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });

  const r = await page.evaluate(async () => {
    const T = window.KIEZ_THEMEN, o = {};
    o.schluessel = Object.keys(T).sort();
    o.paare = T.THEMEN.map((t) => t.id + "/" + t.h);
    o.hashOk = T.THEMEN.every((t) => T.HASH[t.h] === t.id && T.THEMA[t.id] === t);
    // Nachladen: zwei gleichzeitige Aufrufe, ein Script-Tag, beide bekommen dasselbe Objekt
    const [a, b] = await Promise.all([1, 2].map(() => new Promise((ok) => T.laden("daten/fixtures/erreichbar.js", "KIEZ_ERREICHBAR", ok))));
    o.ladenEinmal = document.querySelectorAll('script[src="daten/fixtures/erreichbar.js"]').length;
    o.ladenGleich = !!a && a === b && a.fixture === true;
    o.ladenSofort = await new Promise((ok) => { let sync = false; T.laden("daten/fixtures/erreichbar.js", "KIEZ_ERREICHBAR", () => { sync = true; }); ok(sync); });
    // Ebenen-Register
    const vor = T.THEMEN.length;
    const e = T.ebenen.registrieren({ id: "erreichbar", datei: "daten/fixtures/erreichbar.js", global: "KIEZ_ERREICHBAR", art: "zellwert",
      themen: [{ id: "m_kita", h: "kita", kurz: "Kita", name: "Luftlinie zur nächsten Kita", einheit: "m" }], odbl: false });
    T.ebenen.registrieren({ id: "erreichbar", themen: [{ id: "doppelt", h: "doppelt" }] });
    o.register = { liste: T.ebenen.liste().map((x) => x.id), themenNeu: T.THEMEN.length - vor, ebene: T.THEMA.m_kita && T.THEMA.m_kita.ebene,
      hash: T.HASH.kita, zurueck: e.id, keinDoppel: !T.THEMA.doppelt };
    // Zellwerte: passend → Liste in Zellreihenfolge, abweichend → null und Meldung
    const w = T.ebenen.zellwerte("erreichbar", "kita");
    o.zellwerte = { laenge: w && w.length, zellen: window.KIEZ_ZELLEN.features.length, erster: w && w[0] };
    const echt = window.KIEZ_ERREICHBAR;
    window.KIEZ_ERREICHBAR = Object.assign({}, echt, { erste_id: "CRS3035RES100mN0000000E0000000" });
    o.zellwerteFalsch = T.ebenen.zellwerte("erreichbar", "kita");
    o.meldungFalsch = (document.getElementById("ladestatus") || {}).textContent || "";
    window.KIEZ_ERREICHBAR = Object.assign({}, echt, { anzahl: 3 });
    o.zellwerteAnzahl = T.ebenen.zellwerte("erreichbar", "kita");
    window.KIEZ_ERREICHBAR = echt;
    o.zellwerteArtFehlt = T.ebenen.zellwerte("erreichbar", "gibtsnicht");
    o.zellwerteEbeneFehlt = T.ebenen.zellwerte("gibtsnicht", "kita");
    // Ladefehler: fertig(null), Meldung im aria-live-Element
    o.fehlt = await new Promise((ok) => T.laden("daten/fixtures/gibt-es-nicht.js", "KIEZ_GIBTSNICHT", ok));
    const m = document.getElementById("ladestatus");
    o.meldungFehlt = m ? [m.getAttribute("aria-live"), m.textContent] : null;
    // eigene Klassen und Farben
    const t = T.THEMA.m_kita;
    o.farbeEigen = T.farbe(t, { grenzen: [300, 500, 1000, 2000], min: 0, max: 5000 });
    o.klasseEigen = [0, 300, 700, 1500, 9000].map((v) => T.klasse(t, v, { grenzen: [300, 500, 1000, 2000] }));
    // 9 gültige Werte sortiert 1,2,3,3,4,5,6,8,10: Quintile an Index 1,3,5,7 → 2,3,5,8
    const feats = [5, 1, 4, 2, 3, 3, null, 10, 8, 6].map((v) => ({ properties: { m_kita: v } }));
    o.klassenFeatures = T.klassen(t, feats);
    o.klassenProzent = T.klassen({ id: "x", einheit: "%" });
    o.hoeheFaktor = JSON.stringify(T.hoehe(T.THEMA.ew, { faktor: 0.5 })) !== JSON.stringify(T.hoehe(T.THEMA.ew));
    o.hoeheEins = JSON.stringify(T.hoehe(T.THEMA.ew, { faktor: 1 })) === JSON.stringify(T.hoehe(T.THEMA.ew));
    o.text = [T.fmt.format(182673), T.fmt1.format(17.94), T.rundEw(182673), T.rundEw(456), T.proz(null), T.proz(20.15), T.name(""), T.name("13"), T.esc('<a "b">&')];
    o.geometrie = { ganz: T.GANZ.length === 2, teile: Object.keys(T.TEIL).length, umriss: T.umriss(T.TEIL["13"]).length, polys: T.polys(T.TEIL["13"]).length >= 1,
      farbe: Object.keys(T.FARBE).length, bezirk: Object.keys(T.BEZIRKFARBE).length, stufen: T.STUFEN.filter(Boolean).length, grau: T.GRAU };
    // Ebenen-Thema ohne eigene Klassen: vor dem Einmischen einfarbig und nicht gemerkt, danach Quintile
    T.ebenen.registrieren({ id: "erreichbar_fuss", datei: "daten/fixtures/erreichbar_fuss_odbl.js", global: "KIEZ_ERREICHBAR_FUSS", art: "zellwert", odbl: true,
      themen: [{ id: "f_hort", h: "fhort", kurz: "Hort zu Fuß", name: "Fußweg zum nächsten Hort", einheit: "min" }] });
    const th = T.THEMA.f_hort, vorher = T.farbe(th), map = window.KIEZ_KARTE;
    let mapFehler = null;
    try { map.setPaintProperty("zellen-2d", "fill-color", vorher); } catch (x) { mapFehler = x.message; }
    o.leer = { ausdruck: vorher, gemerkt: "f_hort" in T.KLASSEN, mapFehler };
    o.fuss = await new Promise((ok) => T.laden("daten/fixtures/erreichbar_fuss_odbl.js", "KIEZ_ERREICHBAR_FUSS", ok)) && T.ebenen.zellwerte("erreichbar_fuss", "hort");
    if (o.fuss) window.KIEZ_ZELLEN.features.forEach((f, i) => { f.properties.f_hort = o.fuss[i]; });
    map.getSource("zellen").setData(window.KIEZ_ZELLEN);
    const nachher = T.farbe(th);
    try { map.setPaintProperty("zellen-2d", "fill-color", nachher); } catch (x) { mapFehler = x.message; }
    o.gemischt = { ausdruck: nachher, klassen: T.KLASSEN.f_hort, mapFehler };
    o.fuss = o.fuss && o.fuss.length;
    // jahre_zellen.js: Listen stehen oben (gebaeude, anteile, vorherrschend), nicht unter werte
    T.ebenen.registrieren({ id: "jahre", datei: "daten/fixtures/jahre_zellen.js", global: "KIEZ_JAHRE_ZELLEN", art: "zellwert", themen: [] });
    await new Promise((ok) => T.laden("daten/fixtures/jahre_zellen.js", "KIEZ_JAHRE_ZELLEN", ok));
    o.jahre = ["gebaeude", "vorherrschend", "anteile"].map((k) => (T.ebenen.zellwerte("jahre", k) || []).length);
    o.jahreKeinArray = T.ebenen.zellwerte("jahre", "anzahl");
    // vergebene id oder h: altes Thema bleibt, nichts doppelt
    const n0 = T.THEMEN.length;
    T.ebenen.registrieren({ id: "kollision", themen: [{ id: "ew", h: "neu1" }, { id: "neu2", h: "alter" }] });
    o.kollision = { neu: T.THEMEN.length - n0, ew: T.THEMA.ew.ebene === undefined, alter: T.HASH.alter === "d_alter", neu2: !T.THEMA.neu2 };
    // gleiche Datei, anderes Global: jeder Aufruf bekommt sein eigenes Global
    const [g1, g2] = await Promise.all([["KIEZ_ERREICHBAR_X", "x"], ["KIEZ_ERREICHBAR", "y"]].map(([g]) =>
      new Promise((ok) => { delete window.KIEZ_ERREICHBAR; T.laden("daten/fixtures/erreichbar.js?zwei", g, ok); })));
    o.zweiGlobals = [g1, g2 && g2.methode];
    return o;
  });

  const soll = ["BEZIRKFARBE", "FARBE", "GANZ", "GRAU", "GRUNDKARTE", "HASH", "KLASSEN", "STUFEN", "TEIL", "THEMA", "THEMEN", "ebenen", "esc", "farbe", "fmt", "fmt1",
    "grundLuft", "grundkarte", "hoehe", "kachel", "klasse", "klassen", "laden", "name", "polys", "proBezirk", "proz", "rundEw", "umriss", "unscharf", "v"];
  pruef(JSON.stringify(r.schluessel) === JSON.stringify(soll), `Objekt KIEZ_THEMEN hat genau die ${soll.length} Namen des Vertrags`);
  pruef(r.paare.slice(0, 7).join(",") === "stadtteile/stadtteile,ew/ew,d_alter/alter,q_u18/u18,q_65p/65p,q_v1949/vor1949,q_fern/fern" && r.hashOk,
    `Themen-Schlüssel id/h wie im Vertrag (${r.paare.slice(0, 7).join(", ")})`);
  pruef(r.ladenEinmal === 1 && r.ladenGleich, `laden: zwei gleichzeitige Aufrufe, ${r.ladenEinmal} Script-Tag, beide erhalten dasselbe Objekt`);
  pruef(r.ladenSofort, "laden: liegt das Global schon vor, kommt fertig() sofort");
  pruef(r.register.liste.join() === "erreichbar" && r.register.themenNeu === 1 && r.register.ebene === "erreichbar" && r.register.hash === "m_kita" && r.register.keinDoppel,
    `ebenen.registrieren: ${JSON.stringify(r.register)}`);
  pruef(r.zellwerte.laenge === r.zellwerte.zellen && r.zellwerte.erster === 50, `ebenen.zellwerte: ${r.zellwerte.laenge} Werte für ${r.zellwerte.zellen} Zellen, erster ${r.zellwerte.erster}`);
  pruef(r.zellwerteFalsch === null && r.zellwerteAnzahl === null && r.zellwerteArtFehlt === null && r.zellwerteEbeneFehlt === null && /passen nicht/.test(r.meldungFalsch),
    `ebenen.zellwerte bei falscher erste_id, anzahl, Art oder Ebene: null und Meldung („${r.meldungFalsch}“)`);
  pruef(r.fehlt === null && r.meldungFehlt && r.meldungFehlt[0] === "polite" && /nicht laden/.test(r.meldungFehlt[1]), `laden bei fehlender Datei: fertig(null), aria-live-Meldung („${r.meldungFehlt && r.meldungFehlt[1]}“)`);
  const S = r.geometrie;
  pruef(Array.isArray(r.farbeEigen) && r.farbeEigen[0] === "step" && r.farbeEigen.length === 11 && [3, 5, 7, 9].map((i) => r.farbeEigen[i]).join() === "300,500,1000,2000",
    `farbe mit eigenen Klassen: ${JSON.stringify(r.farbeEigen)}`);
  pruef(r.klasseEigen.join() === "0,1,2,3,4", `klasse mit eigenen Klassen: ${r.klasseEigen.join(",")}`);
  pruef(JSON.stringify(r.klassenFeatures) === JSON.stringify({ grenzen: [2, 3, 5, 8], min: 1, max: 10 }), `klassen über übergebene Features: ${JSON.stringify(r.klassenFeatures)}`);
  pruef(r.klassenProzent.fest === true && r.klassenProzent.grenzen.join() === "20,40,60,80", "klassen für Prozent: fest 20/40/60/80");
  pruef(r.hoeheFaktor && r.hoeheEins, "hoehe: faktor wirkt, faktor 1 = Standard");
  pruef(r.text.join("|") === "182.673|17,9|182.700|460|k. A.|20,2 %|Potsdam|" + r.text[7] + "|&lt;a &quot;b&quot;&gt;&amp;" && r.text[7] !== "Potsdam",
    `Texthelfer: ${r.text.join(" | ")}`);
  pruef(S.ganz && S.teile === 32 && S.umriss === 2 && S.polys && S.farbe === 32 && S.bezirk >= 7 && S.stufen === 5 && S.grau === "#d5d8d3", `Geometrie und Farben: ${JSON.stringify(S)}`);
  pruef(typeof r.leer.ausdruck === "string" && /^#/.test(r.leer.ausdruck) && !r.leer.gemerkt && !r.leer.mapFehler,
    `Ebenen-Thema ohne Werte: einfarbig ${JSON.stringify(r.leer.ausdruck)}, nicht gemerkt, MapLibre nimmt es an`);
  pruef(r.fuss === 3443 && r.gemischt.klassen && r.gemischt.klassen.grenzen.length >= 1 && r.gemischt.klassen.grenzen.every((g) => typeof g === "number") && !r.gemischt.mapFehler,
    `nach dem Einmischen (erreichbar_fuss_odbl.js, hort): ${JSON.stringify(r.gemischt.klassen)}, MapLibre nimmt es an`);
  pruef(r.jahreKeinArray === null, "ebenen.zellwerte nimmt nur Listen (anzahl → null)");
  pruef(r.kollision.neu === 0 && r.kollision.ew && r.kollision.alter && r.kollision.neu2, `registrieren mit vergebener id oder h: ${JSON.stringify(r.kollision)}`);
  pruef(r.zweiGlobals[0] === null && r.zweiGlobals[1] === "luftlinie", `laden: gleiche Datei, verschiedene Globals getrennt (${JSON.stringify(r.zweiGlobals)})`);
  pruef(r.jahre.join() === "3443,3443,3443", `ebenen.zellwerte auf jahre_zellen.js (gebaeude, vorherrschend, anteile): ${r.jahre.join(", ")}`);
  pruef(seitenfehler.length === 0, `keine Seitenfehler (${seitenfehler.length})`);
  const fremd = konsole.filter((t) => !/ERR_FILE_NOT_FOUND|404/.test(t));
  pruef(fremd.length === 0, `Konsole: ${konsole.length} Fehler, davon ${konsole.length - fremd.length} nur von der absichtlich fehlenden Datei (${konsole.join(" | ") || "keine"})`);
  await ctx.close();
}

try { await probe(FILE, "file://"); await probe(HTTP, "HTTP"); }
catch (e) { befunde.push("Abbruch: " + e.message.split("\n")[0]); console.log("  FEHLT Abbruch: " + e.message.split("\n")[0]); }
finally { await browser.close(); server.close(); }
console.log(befunde.length ? `\n${befunde.length} Befund(e)` : "\ngrün");
process.exit(befunde.length ? 1 : 0);
