// Responsive-Messung der Kartenseiten (Andre 07.11.2026: „ja mach lieber voll responsive“).
// Gemeinsamer Baustein für pruefen/seiten.mjs, pruefen/B5_jahre.mjs und pruefen/A7_planer.mjs, dazu als
// eigener Aufruf die Messtabelle für belege/responsive_20261107.md (vorher gegen nachher).
//
// Gemessen wird je Seite und Breite, im Zustand „Start“ und „Lesen“ (Seite bzw. Blatt nach unten gescrollt):
//   karte_px    sichtbare Kartenhöhe: Bildpunkte einer senkrechten Linie durch die Kartenmitte, an denen oben
//               die Karte oder eine ihrer Auflagen liegt (Chips, Legende, Knöpfe), nicht Kopfleiste, Blatt, Text
//   ueberstand  scrollWidth − clientWidth des Dokuments (0 = nichts steht seitlich über). Nicht innerWidth: auf dem
//               Handy (isMobile) wächst innerWidth mit dem Überstand mit, die Prüfung wäre dann immer grün
//   ueberlapp   Paare sichtbarer Bedienelemente, deren Rechtecke sich um mehr als 1 px schneiden
//   klein       Hauptschalter unter 44 × 44 px (nur auf Touch-Breiten gezählt)
//   legende     Höhe der Legende als Anteil der Fensterhöhe
//   kopf        Kopfleiste sichtbar (true) oder eingeklappt (false)
//
// Aufruf:  node pruefen/responsiv.mjs --basis http://127.0.0.1:<port>/ [--bilder <ordner>] [--json <datei>]
//          (Server stellt der Aufrufer, z. B. python3 -m http.server --bind 127.0.0.1 <port>)
// Kein Netz: Fremdabrufe (Kacheln, Luftbild) beantwortet der Prüfbrowser mit einer leeren Antwort.
import fs from "node:fs";
import path from "node:path";
import crypto from "node:crypto";
import { fileURLToPath } from "node:url";

export const BREITEN = [
  { name: "360x740", w: 360, h: 740, touch: true },
  { name: "390x844", w: 390, h: 844, touch: true },
  { name: "844x390", w: 844, h: 390, touch: true },
  { name: "768x1024", w: 768, h: 1024, touch: true },
  { name: "1024x768", w: 1024, h: 768, touch: true },
  { name: "1280x800", w: 1280, h: 800, touch: false },
  { name: "1440x900", w: 1440, h: 900, touch: false },
  { name: "1920x1080", w: 1920, h: 1080, touch: false },
];
export const SEITEN = ["index.html", "karte.html", "jahre.html", "planer.html"];

// Mindestanteil der sichtbaren Karte an der Fensterhöhe im Zustand „Lesen“, je Seite und Breite. Abgeleitet aus der
// Messung vorher (Stand main, belege/responsive_20261107.md): die Schwelle liegt über dem alten Wert, wo die Änderung
// etwas verbessern sollte, damit die Prüfung den alten Stand nicht durchlässt. Wo sich nichts ändern sollte
// (Desktop von Startseite, Karte, Planer), ist sie eine Untergrenze gegen Rückschritte.
export const MINDEST = {
  //            360x740 390x844 844x390 768x1024 1024x768 1280x800 1440x900 1920x1080
  "index.html":  [0.55, 0.56, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85],   // vorher 0,48 0,52 0,52 0,52 1 1 1 1
  "karte.html":  [0.24, 0.24, 0.80, 0.85, 0.85, 0.85, 0.85, 0.85],   // vorher 0,15 0,18 0,08 0,32 0,93 …
  "planer.html": [0.24, 0.24, 0.80, 0.85, 0.85, 0.85, 0.85, 0.85],   // vorher 0,10 0,14 0 0,29 0,88 …
  "jahre.html":  [0.42, 0.44, 0.60, 0.70, 0.66, 0.68, 0.72, 0.78],   // vorher 0,24 0,30 0 0,41 0,61 0,63 0,67 0,74
};
export function mindestKarte(b, seite) { return MINDEST[seite][BREITEN.indexOf(b)]; }
// Kopfleiste klappt beim Lesen ein: Startseite und Bauzeiten immer, Karte und Planer schmal oder niedrig
export function kopfKlappt(b, seite) { return seite === "index.html" || seite === "jahre.html" || b.w <= 860 || b.h <= 500; }
// Legende (Bauzeiten: ganze Leiste unter der Karte) höchstens so viel der Fensterhöhe; Handy hoch knapper
export function hoechstLegende(b, seite) {
  if (seite === "jahre.html") return b.w <= 560 ? 0.25 : b.h <= 500 ? 0.36 : 0.32;   // vorher 0,32 0,28 0,48 bzw. 0,18–0,27
  return 0.35;
}

export function kontext(b, extra = {}) {
  return { viewport: { width: b.w, height: b.h }, hasTouch: b.touch, isMobile: b.touch, ...extra };
}

// Seite „liest“: scrollt in Schritten nach unten (wie ein Daumen), damit die Richtungserkennung greift.
// index/jahre: Fenster bis Frage 2; karte/planer: das Blatt (Desktop) bzw. das geöffnete Blatt (Handy).
export async function lesen(page, seite) {
  if (seite === "index.html" || seite === "jahre.html") {
    const ziel = await page.evaluate(() => { const f = document.getElementById("frage-2"); return Math.max(0, f.getBoundingClientRect().top + scrollY - innerHeight * 0.35); });
    for (let y = await page.evaluate(() => scrollY); y < ziel; y += 160) { await page.evaluate((y) => window.scrollTo(0, y), Math.min(y + 160, ziel)); await page.waitForTimeout(25); }
  } else {
    await page.evaluate(() => {
      const g = document.getElementById("seite-griff");
      if (g && getComputedStyle(g).display !== "none" && g.getAttribute("aria-expanded") !== "true") g.click();
    });
    await page.waitForTimeout(250);
    for (let i = 1; i <= 6; i++) {
      await page.evaluate((i) => { const s = document.getElementById("seite-inhalt"), w = document.getElementById("seite");
        const r = s && s.scrollHeight > s.clientHeight + 4 ? s : w; r.scrollTop = i * 70; r.dispatchEvent(new Event("scroll")); }, i);
      await page.waitForTimeout(25);
    }
  }
  await page.waitForTimeout(700);
}
// etwas zurück nach oben: die Kopfleiste soll wiederkommen
export async function hoch(page, seite) {
  if (seite === "index.html" || seite === "jahre.html") {
    for (let i = 0; i < 3; i++) { await page.evaluate(() => window.scrollBy(0, -60)); await page.waitForTimeout(30); }
  } else {
    for (let i = 0; i < 3; i++) {
      await page.evaluate(() => { const s = document.getElementById("seite-inhalt"), w = document.getElementById("seite");
        const r = s && s.scrollHeight > s.clientHeight + 4 && s.scrollTop > 0 ? s : w; r.scrollTop = Math.max(0, r.scrollTop - 60); r.dispatchEvent(new Event("scroll")); });
      await page.waitForTimeout(30);
    }
  }
  await page.waitForTimeout(700);
}

// Die eigentliche Messung im Browser
export function messen(page, touch) {
  return page.evaluate((touch) => {
    const vw = innerWidth, vh = innerHeight;
    const sichtbar = (e) => { if (!e) return false; const s = getComputedStyle(e); if (s.display === "none" || s.visibility === "hidden" || +s.opacity === 0) return false;
      for (let p = e; p; p = p.parentElement) { const t = getComputedStyle(p); if (t.display === "none" || t.visibility === "hidden" || +t.opacity === 0 || p.hidden) return false; }
      const r = e.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
    // Rechteck, beschnitten auf Fenster und auf scrollende/abschneidende Vorfahren (Chipzeile am Handy)
    const rect = (e) => { const r = e.getBoundingClientRect(); let x0 = Math.max(0, r.left), y0 = Math.max(0, r.top), x1 = Math.min(vw, r.right), y1 = Math.min(vh, r.bottom);
      for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const s = getComputedStyle(p);
        if (/(auto|scroll|hidden|clip)/.test(s.overflowX + s.overflowY)) { const q = p.getBoundingClientRect(); x0 = Math.max(x0, q.left); y0 = Math.max(y0, q.top); x1 = Math.min(x1, q.right); y1 = Math.min(y1, q.bottom); } }
      return { x0, y0, x1, y1, w: Math.max(0, x1 - x0), h: Math.max(0, y1 - y0) }; };
    // oben liegend: mindestens einer von fünf Punkten im sichtbaren Rechteck trifft das Element selbst
    // (unter dem offenen Blatt verdeckte Knöpfe sind verdeckt, nicht überlappend: Regel R5 im Beleg)
    const oben = (e, r) => [[.5, .5], [.15, .15], [.85, .15], [.15, .85], [.85, .85]].some(([a, b]) => { const t = document.elementFromPoint(r.x0 + a * r.w, r.y0 + b * r.h); return t && (t === e || e.contains(t)); });
    const kopf = document.querySelector(".kopfleiste"), kr = kopf.getBoundingClientRect();
    const kopfSichtbar = kr.bottom > 2;
    // sichtbare Kartenhöhe
    const karte = document.getElementById("karte"), mr = karte.getBoundingClientRect();
    const x = Math.round(Math.min(vw - 2, Math.max(1, mr.left + mr.width / 2)));
    let karte_px = 0;
    for (let y = 0; y < vh; y += 2) { const e = document.elementFromPoint(x, y + 1);
      if (e && e.closest("#karte, .werkzeug, .legende, .schild, .beispiel") && !e.closest(".kopfleiste")) karte_px += 2; }
    // Bedienelemente
    const SEL = [".kopfleiste", ".werkzeug .chip", ".maplibregl-ctrl-group button", ".maplibregl-ctrl-attrib-button", ".maplibregl-ctrl-attrib.maplibregl-compact-show", ".maplibregl-ctrl-scale", ".legende", "#legende-griff",
      ".seite__griff", ".j-leiste", ".beispiel"];
    const els = []; const gesehen = new Set();
    for (const s of SEL) for (const e of document.querySelectorAll(s)) { if (gesehen.has(e) || !sichtbar(e)) continue; gesehen.add(e);
      const r = rect(e); if (r.w > 1 && r.h > 1 && oben(e, r)) els.push({ e, r, name: s + (e.id ? "#" + e.id : e.getAttribute("aria-label") ? "[" + e.getAttribute("aria-label") + "]" : e.textContent.trim() ? "„" + e.textContent.trim().slice(0, 14) + "“" : "") }); }
    // Desktop-Seitenleiste (karte/planer): als Fläche mitzählen
    const seite = document.getElementById("seite");
    // ohne seinen Innenabstand oben: dort liegt gewollt die Kopfleiste (Seitenleiste reicht unter sie, R1 im Beleg)
    if (seite && sichtbar(seite) && !gesehen.has(seite)) { const r = rect(seite), pt = parseFloat(getComputedStyle(seite).paddingTop) || 0; r.y0 = Math.min(r.y1, r.y0 + pt); r.h = r.y1 - r.y0;
      if (r.w > 1 && r.h > 1 && oben(seite, r)) els.push({ e: seite, r, name: "#seite" }); }
    const paare = [];
    for (let i = 0; i < els.length; i++) for (let j = i + 1; j < els.length; j++) {
      const a = els[i], b = els[j]; if (a.e.contains(b.e) || b.e.contains(a.e)) continue;
      const w = Math.min(a.r.x1, b.r.x1) - Math.max(a.r.x0, b.r.x0), h = Math.min(a.r.y1, b.r.y1) - Math.max(a.r.y0, b.r.y0);
      if (w > 1 && h > 1) paare.push(a.name + " × " + b.name + " (" + Math.round(w) + "×" + Math.round(h) + ")");
    }
    // Tippziele (nur Touch): Hauptschalter
    const klein = [];
    if (touch) for (const s of [".werkzeug .chip", ".maplibregl-ctrl-group button", ".maplibregl-ctrl-attrib-button", ".seite__griff", "#legende-griff", ".kopf-haupt .nav", ".marke", ".j-abspielen"])
      for (const e of document.querySelectorAll(s)) { if (!sichtbar(e)) continue; const r = e.getBoundingClientRect();
        if (r.bottom < 0 || r.top > vh) continue;
        if (r.width < 43.5 || r.height < 43.5) klein.push(s + (e.getAttribute("aria-label") ? "[" + e.getAttribute("aria-label") + "]" : "„" + e.textContent.trim().slice(0, 12) + "“") + " " + Math.round(r.width) + "×" + Math.round(r.height)); }
    // Legende: ganze Höhe (nicht beschnitten) als Anteil der Fensterhöhe; auf der Bauzeiten-Seite dazu die ganze Leiste unter der Karte
    const leg = [...document.querySelectorAll(".legende, #j-legende")].find(sichtbar), lei = document.querySelector(".j-leiste");
    const hoehe = (e) => e && sichtbar(e) ? e.getBoundingClientRect().height : 0;
    return { karte_px, karte_anteil: +(karte_px / vh).toFixed(3), ueberstand: Math.max(0, document.documentElement.scrollWidth - document.documentElement.clientWidth), breite_layout: innerWidth, ueberlapp: paare, klein,
      legende: +(hoehe(leg) / vh).toFixed(3), leiste: +(hoehe(lei) / vh).toFixed(3), kopf: kopfSichtbar, kopf_px: kopfSichtbar ? Math.round(Math.min(vh, kr.bottom)) : 0, y: Math.round(scrollY) };
  }, touch);
}

// Prüft eine Seite über alle Breiten. pruef(ok, text) kommt vom aufrufenden Skript; basis ist der eigene Prüfserver.
export async function pruefeResponsiv(browser, basis, seite, pruef, { bilder = null } = {}) {
  console.log(`Responsiv ${seite} (${BREITEN.length} Breiten)`);
  for (const b of BREITEN) {
    const ctx = await browser.newContext(kontext(b, { reducedMotion: "reduce" }));
    const page = await ctx.newPage(); const fehler = [];
    await page.route("**/*", (r) => { const u = r.request().url(); return u.startsWith(basis) || /^(data|blob):/.test(u) ? r.continue() : r.fulfill(fremdAntwort(u)); });
    page.on("console", (m) => { if (m.type() === "error" && !/ERR_ABORTED/.test(m.text())) fehler.push(m.text().split("\n")[0]); });
    page.on("pageerror", (e) => fehler.push("pageerror: " + e.message));
    await page.goto(basis + seite, { waitUntil: "load" });
    const da = await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 }).then(() => true, () => false);
    await page.waitForTimeout(500);
    const s0 = await messen(page, b.touch);
    await lesen(page, seite);
    const l = await messen(page, b.touch);
    if (bilder) await bildMd5(page, path.join(bilder, `${seite.replace(".html", "")}_${b.name}_lesen.png`));
    await hoch(page, seite);
    const h = await messen(page, b.touch);
    const min = mindestKarte(b, seite), klappt = kopfKlappt(b, seite), maxL = hoechstLegende(b, seite);
    const leg = seite === "jahre.html" ? l.leiste : l.legende;
    const ov = [...new Set([...s0.ueberlapp, ...l.ueberlapp])];
    pruef(da && fehler.length === 0 && s0.ueberstand === 0 && l.ueberstand === 0 && ov.length === 0 && s0.klein.length === 0,
      `${b.name}: geladen, Konsole ${fehler.length} Fehler, Überstand ${s0.ueberstand}/${l.ueberstand} px, Überlappungen ${ov.length}${ov.length ? " (" + ov.slice(0, 2).join("; ") + ")" : ""}, Tippziele unter 44 px ${s0.klein.length}${s0.klein.length ? " (" + s0.klein.slice(0, 2).join("; ") + ")" : ""}`);
    pruef(l.karte_anteil >= min && leg <= maxL && (!klappt || (!l.kopf && h.kopf)) && (klappt || l.kopf),
      `${b.name}: Karte beim Lesen ${l.karte_px} px = ${Math.round(100 * l.karte_anteil)} % (mindestens ${Math.round(100 * min)} %), ${seite === "jahre.html" ? "Leiste" : "Legende"} ${Math.round(100 * leg)} % (höchstens ${Math.round(100 * maxL)} %), Kopfleiste beim Lesen ${l.kopf ? "da" : "eingeklappt"}, nach Hochscrollen ${h.kopf ? "da" : "weg"}${klappt ? "" : " (bleibt hier stehen)"}`);
    await ctx.close();
  }
}

export async function bildMd5(page, datei) {
  await page.screenshot({ path: datei });
  return crypto.createHash("md5").update(fs.readFileSync(datei)).digest("hex");
}

export const LEERBILD = Buffer.from("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=", "base64");
export const fremdAntwort = (u) => /\.pbf(\?|$)/.test(u) ? { status: 200, contentType: "application/x-protobuf", body: Buffer.alloc(0) } : { status: 200, contentType: "image/png", body: LEERBILD };

// ---------- eigener Aufruf: Messtabelle
if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const { chromium } = await import("playwright");
  const arg = (n, d) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : d; };
  const BASIS = arg("--basis"), BILDER = arg("--bilder"), JSONAUS = arg("--json");
  if (!BASIS) { console.error("--basis fehlt"); process.exit(2); }
  if (BILDER) fs.mkdirSync(BILDER, { recursive: true });
  const nurSeiten = (arg("--seiten", SEITEN.join(","))).split(","), nurBreiten = (arg("--breiten", BREITEN.map((b) => b.name).join(","))).split(",");
  const browser = await chromium.launch();
  const zeilen = [];
  for (const seite of nurSeiten) for (const b of BREITEN.filter((x) => nurBreiten.includes(x.name))) {
    const ctx = await browser.newContext(kontext(b, { reducedMotion: "reduce" }));
    const page = await ctx.newPage(); const fehler = [];
    await page.route("**/*", (r) => r.request().url().startsWith(BASIS) || /^(data|blob):/.test(r.request().url()) ? r.continue() : r.fulfill(fremdAntwort(r.request().url())));
    page.on("console", (m) => { if (m.type() === "error" && !/ERR_ABORTED/.test(m.text())) fehler.push(m.text().split("\n")[0]); });
    page.on("pageerror", (e) => fehler.push("pageerror: " + e.message));
    await page.goto(BASIS + seite, { waitUntil: "load" });
    await page.waitForFunction(() => window.KIEZ_BEREIT === true, null, { timeout: 90000 }).catch(() => fehler.push("KIEZ_BEREIT fehlt"));
    await page.waitForTimeout(600);
    const start = await messen(page, b.touch);
    const md5s = BILDER ? await bildMd5(page, path.join(BILDER, `${seite.replace(".html", "")}_${b.name}_start.png`)) : "";
    await lesen(page, seite);
    const lese = await messen(page, b.touch);
    const md5l = BILDER ? await bildMd5(page, path.join(BILDER, `${seite.replace(".html", "")}_${b.name}_lesen.png`)) : "";
    await hoch(page, seite);
    const zurueck = await messen(page, b.touch);
    zeilen.push({ seite, breite: b.name, start, lesen: lese, hoch: { kopf: zurueck.kopf }, fehler, md5: { start: md5s, lesen: md5l } });
    console.log(`${seite.padEnd(12)} ${b.name.padEnd(9)} Karte Start ${String(start.karte_px).padStart(4)} px, Lesen ${String(lese.karte_px).padStart(4)} px (${Math.round(100 * lese.karte_anteil)} %), Überstand ${Math.max(start.ueberstand, lese.ueberstand)}, Überlappung ${start.ueberlapp.length}/${lese.ueberlapp.length}, klein ${start.klein.length}, Legende ${Math.round(100 * lese.legende)} %, Leiste ${Math.round(100 * lese.leiste)} %, Kopf beim Lesen ${lese.kopf ? "da" : "weg"}, nach Hoch ${zurueck.kopf ? "da" : "weg"}, Fehler ${fehler.length}`);
    for (const p of new Set([...start.ueberlapp, ...lese.ueberlapp])) console.log("      Überlappung: " + p);
    for (const k of start.klein) console.log("      klein: " + k);
    for (const f of fehler) console.log("      Fehler: " + f);
    await ctx.close();
  }
  await browser.close();
  if (JSONAUS) fs.writeFileSync(JSONAUS, JSON.stringify(zeilen, null, 1));
}
