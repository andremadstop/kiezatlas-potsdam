// Vorschaubild og.png (1200 × 630) aus einer eigenen Aufnahme der Bauzeiten-Seite mit 3D-Häusern (Innenstadt).
// Ersetzt das alte Bild mit dem Chip „Gebäude 3D“ (seit 07.11.2026 heißt 3D Häuser, keine Säulen).
//
// Ablauf: eigener Server auf 127.0.0.1 (nur Dateien dieses Ordners), headless Chromium aus node_modules,
// jahre.html laden, „3D-Häuser“ einschalten (fliegt in die Innenstadt), feste Kamera, warten bis Karte ruht und
// alle Kacheln da sind. Dann Kopfleiste, Text und Knöpfe ausblenden, Karte bildfüllend, Titelzeile und
// Quellenvermerk darüberlegen, Bildschirmfoto. Ausgabe: MD5 und Größe des Bildes.
//
// Netz: nur die Grundkarte von basemap.de (sgx.geodatenzentrum.de/gdz_basemapde_vektor/, Kacheln und Schriften;
// robots.txt erlaubt den Pfad, gesperrt sind nur /gdz_geoviewserver/ und /gdz_geoviewserv/). Alles andere aus dem
// Netz beantwortet der Browser mit einer leeren Antwort (kein Luftbild, keine Zählung).
//
// Aufruf:  node skripte/28_vorschaubild.mjs [--aus og.png] [--ohne-netz]
//          --ohne-netz: auch die Grundkarte leer (zum Probelauf ohne Abruf; das Bild zeigt dann nur Häuser und Zellen)
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

const WURZEL = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
const AUS = path.resolve(arg("--aus", path.join(WURZEL, "og.png")));
const OHNE_NETZ = process.argv.includes("--ohne-netz");
const ERLAUBT = "https://sgx.geodatenzentrum.de/gdz_basemapde_vektor/";
const KAMERA = { center: [13.0585, 52.3985], zoom: 16.15, pitch: 58, bearing: -24 };   // Innenstadt um den Platz der Einheit, Blick nach Nordwesten
const TITEL = "Kiezatlas Potsdam", UNTER = "Bauzeiten der Gebäude, Haus für Haus geschätzt. Innenstadt";
// Quellenvermerk: wörtlich, was die Seite im „i“ für die sichtbaren Quellen zeigt (Grundkarte, Zensus-Zellen, Stadtteile,
// Gebäude), je Quelle eine Zeile. Vorher stand hier ein verkürzter Text ohne Lizenzen, Änderungshinweis und Zensus (Gegenprobe 07.11.)

const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2", ".json": "application/json" };
const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (p !== WURZEL && !p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p, (f, d) => { if (f) { a.writeHead(404); a.end(); return; } a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const BASIS = `http://127.0.0.1:${server.address().port}/`;

const browser = await chromium.launch();
const zaehler = { eigen: 0, grundkarte: 0, leer: 0 };
try {
  const ctx = await browser.newContext({ viewport: { width: 1200, height: 630 }, deviceScaleFactor: 1, reducedMotion: "reduce", locale: "de-DE" });
  const page = await ctx.newPage();
  const fehler = [];
  page.on("pageerror", (e) => fehler.push(e.message));
  await page.route("**/*", (r) => {
    const u = r.request().url();
    if (u.startsWith(BASIS) || /^(data|blob):/.test(u)) { zaehler.eigen++; return r.continue(); }
    if (!OHNE_NETZ && u.startsWith(ERLAUBT)) { zaehler.grundkarte++; return r.continue(); }
    zaehler.leer++;
    return r.fulfill(/\.pbf(\?|$)/.test(u) ? { status: 200, contentType: "application/x-protobuf", body: Buffer.alloc(0) } : { status: 204, body: "" });
  });
  await page.goto(BASIS + "jahre.html", { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  // 3D-Häuser über den Schalter der Seite (lädt die Gebäude der Innenstadt), dann feste Kamera
  await page.evaluate(() => { const c = document.getElementById("j-dreid"); if (!c.checked) c.click(); });
  await page.waitForFunction(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-3d"] }).length > 0, null, { timeout: 30000 });
  // Bühne bildfüllend, alles andere aus; Titel und Vermerk als eigene Lage darüber
  await page.addStyleTag({ content: `
    body > *:not(#buehne):not(.og-lage) { display: none !important; }
    #buehne .werkzeug, #buehne .maplibregl-control-container, #buehne .j-leiste, #buehne .schild { display: none !important; }
    html, body { overflow: hidden !important; }
    html, body { height: 100% !important; }
    #buehne { position: fixed !important; inset: 0 !important; width: 100vw !important; height: 100vh !important; border: 0 !important; z-index: 50; display: block !important; }
    #buehne #karte { position: absolute !important; inset: 0 !important; }
    .og-lage { position: fixed; inset: 0; z-index: 60; pointer-events: none; font-family: var(--f-text); color: var(--ink); }
    .og-kopf { position: absolute; left: 0; top: 0; padding: 30px 40px 26px 44px; background: rgba(241,242,238,.94); border-right: 1px solid var(--line); border-bottom: 4px solid var(--accent); }
    .og-marke { display: flex; align-items: center; gap: 16px; font: 600 64px/1 var(--f-display); letter-spacing: -.02em; margin: 0; }
    .og-marke i { width: 30px; height: 30px; flex: 0 0 auto; outline: 2px solid var(--ink); background: linear-gradient(var(--accent) 0 0) 0 0/50% 50% no-repeat, linear-gradient(var(--ink) 0 0) 100% 100%/50% 50% no-repeat; }
    .og-unter { font: 500 24px/1.25 var(--f-text); color: var(--muted); margin: 12px 0 0 46px; }
    .og-vermerk { position: absolute; right: 0; bottom: 0; padding: 6px 12px; font: 400 14px/1.35 var(--f-text); color: var(--ink); background: rgba(250,251,248,.9); white-space: pre-line; text-align: right; }` });
  await page.evaluate(([titel, unter]) => {
    const l = document.createElement("div"); l.className = "og-lage";
    l.innerHTML = '<div class="og-kopf"><p class="og-marke"><i></i><span></span></p><p class="og-unter"></p></div><p class="og-vermerk"></p>';
    l.querySelector(".og-marke span").textContent = titel; l.querySelector(".og-unter").textContent = unter;
    document.body.appendChild(document.getElementById("buehne"));   // Bühne aus dem Raster der Seite lösen
    document.body.appendChild(l);
  }, [TITEL, UNTER]);
  await page.evaluate((k) => { const m = window.KIEZ_KARTE; m.resize(); m.jumpTo(k); }, KAMERA);
  await page.waitForFunction(() => window.KIEZ_KARTE.queryRenderedFeatures({ layers: ["geb-3d"] }).length > 200, null, { timeout: 30000 });
  // Ruhe: keine Bewegung, Stil und alle Kacheln geladen, Häuser im Bild, Schriften da
  await page.waitForFunction(() => { const m = window.KIEZ_KARTE; return !m.isMoving() && m.loaded() && m.areTilesLoaded(); }, null, { timeout: 60000, polling: 250 });
  // neu zeichnen lassen und auf „idle“ warten (once allein hinge, wenn die Karte schon ruht), höchstens 20 s
  await page.evaluate(() => new Promise((r) => { const m = window.KIEZ_KARTE; m.once("idle", r); m.triggerRepaint(); setTimeout(r, 20000); }));
  await page.evaluate(() => document.fonts.ready);
  await page.waitForTimeout(800);
  const vermerk = await page.evaluate(() => {
    const t = document.querySelector("#karte .maplibregl-ctrl-attrib-inner").textContent.split(" | ").map((x) => x.trim()).filter(Boolean);
    document.querySelector(".og-vermerk").textContent = t.join("\n"); return t;
  });
  if (!vermerk.length) throw new Error("kein Quellenvermerk auf der Seite");
  await page.waitForTimeout(200);
  const z = await page.evaluate(() => { const m = window.KIEZ_KARTE, ex = m.getStyle().layers.filter((l) => l.type === "fill-extrusion" && m.getLayoutProperty(l.id, "visibility") !== "none").map((l) => l.id);
    return { haeuser: m.queryRenderedFeatures({ layers: ["geb-3d"] }).length, schichten: ex, zoom: +m.getZoom().toFixed(2), neigung: Math.round(m.getPitch()) }; });
  await page.screenshot({ path: AUS, type: "png" });
  const md5 = crypto.createHash("md5").update(fs.readFileSync(AUS)).digest("hex");
  console.log(`og.png: ${AUS}\n  ${fs.statSync(AUS).size} Byte, MD5 ${md5}`);
  console.log("  Vermerk:\n    " + vermerk.join("\n    "));
  console.log(`  Häuser im Bild: ${z.haeuser} (${z.schichten.join(", ")}), Zoom ${z.zoom}, Neigung ${z.neigung}`);
  console.log(`  Abrufe: ${zaehler.eigen} eigene, ${zaehler.grundkarte} Grundkarte (basemap.de), ${zaehler.leer} leer beantwortet; Seitenfehler ${fehler.length}`);
  if (!z.haeuser || fehler.length) { console.log("  BEFUND: keine Häuser im Bild oder Seitenfehler " + fehler.join(" | ")); process.exitCode = 1; }
  await ctx.close();
} finally {
  await browser.close();
  server.close();
}
