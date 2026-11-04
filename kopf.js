/* Kiezatlas Potsdam: Kopfzahlen sofort füllen, bevor die großen Datendateien da sind (gegen Layoutsprünge). */
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
