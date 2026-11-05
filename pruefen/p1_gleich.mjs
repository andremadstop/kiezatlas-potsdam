// Gleichheitsprobe Paket P1 (themen.js): Startseite und freie Karte vorher/nachher vergleichen.
// Schreibt je Wurzel einen Zustandsabzug als JSON: Schaugrafik-SVG (Export mit Schriften, drei
// Kartenthemen und ein Vergleich von zwei Stadtteilen), MapLibre-Stil der Zellen und Stadtteile je
// Thema, Legende, Kopfzahlen, Fragen-Texte, Register je Sortierung, Grenzfall-Grafik, Steckbrief.
// Zwei Abzüge vergleicht man mit --vergleich a.json b.json (Rückgabe 0 = gleich).
//
// Aufruf:  node pruefen/p1_gleich.mjs --wurzel <ordner> --json <datei>
//          node pruefen/p1_gleich.mjs --vergleich vorher.json nachher.json
// Kein Netz: Fremdabrufe (Kacheln, Luftbild) beantwortet der Prüfbrowser mit einem leeren Bild.
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };

if (process.argv.includes("--vergleich")) {
  const i = process.argv.indexOf("--vergleich");
  const a = JSON.parse(fs.readFileSync(process.argv[i + 1], "utf8")), b = JSON.parse(fs.readFileSync(process.argv[i + 2], "utf8"));
  let n = 0;
  for (const k of Object.keys(a).sort()) {
    if (k === "wurzel" || k === "stand") continue;
    const x = JSON.stringify(a[k]), y = JSON.stringify(b[k]);
    if (x === y) { console.log(`  gleich  ${k} (${x.length} Zeichen)`); continue; }
    n++;
    let p = 0; while (p < x.length && x[p] === y[p]) p++;
    console.log(`  ANDERS  ${k}: ab Zeichen ${p}\n     vorher  …${x.slice(Math.max(0, p - 60), p + 120)}\n     nachher …${(y || "").slice(Math.max(0, p - 60), p + 120)}`);
  }
  for (const k of Object.keys(b)) if (!(k in a)) { n++; console.log(`  NEU     ${k}`); }
  console.log(n ? `\n${n} Abweichung(en)` : "\ngleich");
  process.exit(n ? 1 : 0);
}

const WURZEL = path.resolve(arg("--wurzel", "."));
const AUS = arg("--json");
const LEERBILD = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
const TYP = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml", ".png": "image/png", ".woff2": "font/woff2" };
const server = http.createServer((q, a) => {
  const p = path.normalize(path.join(WURZEL, decodeURIComponent(new URL(q.url, "http://x").pathname)));
  if (!p.startsWith(WURZEL + path.sep)) { a.writeHead(403); a.end(); return; }
  fs.readFile(p, (f, d) => { if (f) { a.writeHead(404); a.end(); return; } a.writeHead(200, { "content-type": TYP[path.extname(p)] || "application/octet-stream" }); a.end(d); });
});
await new Promise((r) => server.listen(0, "127.0.0.1", r));
const HTTP = `http://127.0.0.1:${server.address().port}/`;
const browser = await chromium.launch();
const abzug = { wurzel: WURZEL, stand: new Date().toISOString() };
const fehler = [];

async function oeffnen(datei, hash = "") {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, reducedMotion: "reduce", acceptDownloads: true, locale: "de-DE", timezoneId: "Europe/Berlin" });
  const page = await ctx.newPage();
  await page.route("**/*", (r) => r.request().url().startsWith(HTTP) ? r.continue() : r.fulfill({ status: 200, contentType: "image/png", body: LEERBILD }));
  page.on("pageerror", (e) => fehler.push(datei + ": " + e.message));
  await page.goto(HTTP + datei + hash, { waitUntil: "load" });
  await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 });
  return { ctx, page };
}
const stil = (page) => page.evaluate(() => {
  const m = window.KIEZ_KARTE, o = {};
  for (const id of ["teile-flaeche", "zellen-2d", "zellen-flach", "zellen-3d"]) {
    const l = m.getStyle().layers.find((x) => x.id === id); if (!l) continue;
    o[id] = { paint: l.paint, filter: l.filter || null, sichtbar: (l.layout || {}).visibility || "visible" };
  }
  return o;
});
const html = (page, sel) => page.$eval(sel, (e) => e.innerHTML).catch(() => null);

// ---------- Startseite
{
  const { ctx, page } = await oeffnen("index.html");
  abzug.index_kopf = await html(page, "#stadtzahlen");
  abzug.index_felder = await page.$$eval("[data-q],[data-feld]", (l) => l.map((e) => (e.dataset.q || e.dataset.feld) + "=" + e.textContent));
  abzug.index_grenzfall = await html(page, "#grenz-figur");
  abzug.index_grenztext = await page.$$eval("#grenz-lead,#grenz-kern,#grenz-cap,#grenz-tab", (l) => l.map((e) => e.innerHTML));
  abzug.index_themen = await page.$$eval('#thema input[name="thema"]', (l) => l.map((i) => i.value + "|" + i.parentNode.textContent + "|" + (i.parentNode.title || "")));
  for (const w of await page.$$eval('#thema input[name="thema"]', (l) => l.map((i) => i.value))) {
    await page.check(`#thema input[value="${w}"]`, { force: true });
    await page.waitForTimeout(400);
    abzug["index_stil_" + w] = await stil(page);
    abzug["index_legende_" + w] = await html(page, "#legende");
  }
  for (const s of await page.$$eval('#sortierung input[name="sort"]', (l) => l.map((i) => i.value))) {
    await page.check(`#sortierung input[value="${s}"]`, { force: true });
    abzug["index_register_" + s] = await html(page, "#teile");
  }
  abzug.index_steckbrief = await html(page, "#kacheln");
  // Schaugrafik: Export-SVG für drei Kartenthemen, dazu ein Vergleich zweier Stadtteile
  await page.locator("#schaugrafik").scrollIntoViewIfNeeded();
  const faelle = [["ew", [""]], ["q_fern", [""]], ["stadtteile", [""]], ["d_alter", ["13", "52"]]];
  for (const [thema, gebiete] of faelle) {
    await page.evaluate(([thema, gebiete]) => {
      document.querySelectorAll('#schaugrafik input[name="gebiet"]').forEach((i) => { i.checked = gebiete.includes(i.value); i.disabled = false; });
      const kt = document.getElementById("schau-kartenthema"); kt.value = thema;
      kt.dispatchEvent(new Event("change", { bubbles: true }));
    }, [thema, gebiete]);
    const [d] = await Promise.all([page.waitForEvent("download", { timeout: 30000 }), page.click("#schau-svg")]);
    abzug[`schau_svg_${thema}_${gebiete.join("+") || "stadt"}`] = { datei: d.suggestedFilename(), svg: fs.readFileSync(await d.path(), "utf8") };
  }
  await ctx.close();
}

// ---------- freie Karte
{
  const { ctx, page } = await oeffnen("karte.html");
  abzug.karte_themen = await page.$$eval('#thema input[name="thema"]', (l) => l.map((i) => i.value + "|" + i.parentNode.textContent + "|" + (i.parentNode.title || "")));
  for (const w of await page.$$eval('#thema input[name="thema"]', (l) => l.map((i) => i.value))) {
    for (const d3 of [false, true]) {
      await page.check(`#thema input[value="${w}"]`, { force: true });
      if (d3) await page.check("#dreid", { force: true }); else await page.uncheck("#dreid", { force: true });
      await page.waitForTimeout(300);
      abzug[`karte_stil_${w}_${d3 ? "3d" : "2d"}`] = await stil(page);
      abzug[`karte_legende_${w}_${d3 ? "3d" : "2d"}`] = await html(page, "#legende");
      abzug[`karte_hash_${w}_${d3 ? "3d" : "2d"}`] = await page.evaluate(() => location.hash.replace(/&k=.*$/, ""));
    }
  }
  abzug.karte_steckbrief = await html(page, "#kacheln");
  await ctx.close();
  const b = await oeffnen("karte.html", "#thema=vor1949&st=13");
  await b.page.waitForTimeout(500);
  abzug.karte_hash_lesen = await b.page.evaluate(() => [(document.querySelector('#thema input:checked') || {}).value, location.hash.replace(/&k=.*$/, "")]);
  abzug.karte_steckbrief_13 = await html(b.page, "#kacheln");
  await b.ctx.close();
}
abzug.seitenfehler = fehler;
await browser.close(); server.close();
if (AUS) fs.writeFileSync(AUS, JSON.stringify(abzug));
console.log(`${Object.keys(abzug).length - 2} Abschnitte, Seitenfehler: ${fehler.length}`);
