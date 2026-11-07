/* Kiezatlas Potsdam: gemeinsamer Kopf der vier Kartenseiten (index, karte, planer, jahre).
   1. Gestapelt oder nebeneinander: eine Abfrage für CSS und JS (Karte oben und Text darunter nur am Handy hoch).
   2. Kopfleiste klappt beim Lesen (Scrollen nach unten) ein und kommt beim Hochscrollen wieder (Andre 07.11.2026).
   3. Kopfzahlen sofort füllen, bevor die großen Datendateien da sind (gegen Layoutsprünge, nur Startseite). */
// Muss wörtlich mit den @media-Abfragen „Gestapelt“ in atlas.css, karte.css und jahre.css übereinstimmen (pruefen/seiten.mjs prüft das)
window.KIEZ_GESTAPELT = "(max-width:599px),(max-width:699px) and (orientation:portrait)";
(function () {
  var html = document.documentElement, kopf = document.querySelector(".kopfleiste");
  if (!kopf || !document.body) return;
  // Karte und Planer haben keinen Seitenscroll: dort wird im Blatt gelesen, und eingeklappt wird nur schmal oder niedrig
  var kartenseite = document.body.classList.contains("kartenseite");
  var erlaubt = kartenseite ? matchMedia("(max-width:860px),(max-height:500px)") : null;
  var OBEN = 60, SCHWELLE = 12, merk = 0;
  function setze(weg) { if (html.classList.contains("kopf-weg") !== weg) html.classList.toggle("kopf-weg", weg); }
  // Richtung mit Schwelle: kleine Zitterbewegungen (Gummiband am Seitenende, Adressleiste) schalten nichts um
  function lage(y) {
    if (erlaubt && !erlaubt.matches) { setze(false); merk = y; return; }
    if (y < OBEN) { setze(false); merk = y; return; }
    if (y > merk + SCHWELLE) { setze(true); merk = y; }
    else if (y < merk - SCHWELLE) { setze(false); merk = y; }
  }
  if (kartenseite) {
    document.addEventListener("scroll", function (e) {
      var t = e.target; if (t && t.nodeType === 1 && t.closest("#seite")) lage(t.scrollTop);
    }, { capture: true, passive: true });
    // Blatt zu (Handy): die Kopfleiste ist wieder da
    var griff = document.getElementById("seite-griff");
    if (griff) new MutationObserver(function () { if (griff.getAttribute("aria-expanded") === "false") { setze(false); merk = 0; } })
      .observe(griff, { attributes: true, attributeFilter: ["aria-expanded"] });
    if (erlaubt.addEventListener) erlaubt.addEventListener("change", function () { if (!erlaubt.matches) setze(false); });
  } else {
    addEventListener("scroll", function () { lage(scrollY); }, { passive: true });
  }
  // Tastatur: wer in die Kopfleiste springt, sieht sie
  kopf.addEventListener("focusin", function () { setze(false); });
})();
(function () {
  var K = window.KIEZ_KENNZAHLEN; if (!K) return;
  var fmt = new Intl.NumberFormat("de-DE"), fmt1 = new Intl.NumberFormat("de-DE", { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  function setze(f, w) { document.querySelectorAll('[data-feld="' + f + '"]').forEach(function (n) { n.textContent = w; }); }
  var nrs = Object.keys(K.stadtteile).sort(function (a, b) { return a - b; });
  setze("anzahl-teile", String(nrs.length)); setze("nr-erste", nrs[0]); setze("nr-letzte", nrs[nrs.length - 1]);
  setze("stand", new Date(K.stand_auswertung).toLocaleDateString("de-DE"));
  setze("flaeche-stadt", fmt1.format(K.stadt.flaeche_km2)); setze("zellen-stadt", fmt.format(K.stadt.zellen));
  var box = document.getElementById("stadtzahlen"); if (!box || box.children.length) return;
  K.stadt.kacheln.forEach(function (k) {
    var d = document.createElement("div"), dd = document.createElement("dd"), dt = document.createElement("dt");
    dt.textContent = k.titel; dd.title = k.quelle;
    if (k.anzeige === "summe") dd.textContent = "rund " + fmt.format(k.wert >= 1000 ? Math.round(k.wert / 100) * 100 : Math.round(k.wert / 10) * 10);
    else { dd.textContent = fmt1.format(k.wert); var s = document.createElement("small"); s.textContent = "%"; dd.appendChild(s); }
    d.appendChild(dt); d.appendChild(dd); box.appendChild(d);
  });
})();
