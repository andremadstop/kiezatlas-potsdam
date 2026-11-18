/* Kiezatlas: Rahmen der erzeugten Seiten (skripte/30_seiten.py, vorlagen/_rahmen.html), neben kopf.js.
   1. Sprachschalter (a[data-sprache]): wechselt den Sprachordner und nimmt den Hash mit (Zustand, geteilte Links).
   2. Einmaliger Sprachhinweis (#sprachhinweis), wenn die Browsersprache eine andere angebotene Sprache ist; keine Umleitung.
   3. Kennzeichnung Beispieldaten (#beispieldaten): sichtbar, sobald eine geladene Datendatei fixture: true trägt;
      Seiten, die Daten nachladen, rufen danach window.KIEZ_BEISPIEL_PRUEFEN() auf. Kommen alle Beispieldaten erst
      nachgeladen dazu (etwa eine Ebene der Karte), zeigt der Hinweis die zweite Fassung aus data-nachgeladen
      (kern.beispieldaten_nachgeladen): Beispieldaten nur in einem Teil der Seite. */
(function () {
  // 1. Sprachschalter: der Hash wird beim Klick gelesen, nicht beim Laden (er ändert sich mit jeder Auswahl)
  function mitHash(a) { a.setAttribute("href", a.getAttribute("href").split("#")[0] + location.hash); }
  function alle() { document.querySelectorAll("a[data-sprache]").forEach(mitHash); }
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a[data-sprache]") : null;
    if (a) mitHash(a);
  }, true);
  addEventListener("hashchange", alle);
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", alle); else alle();

  // 2. Sprachhinweis: einmal, gemerkt im Browser (ohne Speicher: jedes Mal, aber nie automatisch umleiten)
  var h = document.getElementById("sprachhinweis"), ORT = window.KIEZ_ORT;
  if (h && ORT && ORT.sprachen.length > 1) {
    var seite = (document.documentElement.getAttribute("lang") || "").slice(0, 2), MERK = "kiez_sprachhinweis";
    var wunsch = (navigator.languages || [navigator.language || ""]).map(function (s) { return String(s).slice(0, 2).toLowerCase(); })
      .filter(function (s) { return ORT.sprachen.indexOf(s) >= 0; })[0];
    var gesehen = false;
    try { gesehen = localStorage.getItem(MERK) === "1"; } catch (e) { /* kein Speicher (privates Fenster, file://) */ }
    var link = wunsch && wunsch !== seite ? h.querySelector('a[data-sprache="' + wunsch + '"]') : null;
    if (link && !gesehen) {
      h.querySelectorAll("a[data-sprache]").forEach(function (a) { a.hidden = a !== link; });
      h.hidden = false;
      var zu = h.querySelector("button");
      // Schließen in beiden Sprachen benennen: Seitensprache und angebotene Sprache („Zamknij / Schließen“)
      var name2 = link.getAttribute("data-schliessen"), name1 = zu && zu.getAttribute("aria-label");
      if (zu && name2 && name2 !== name1) { zu.setAttribute("aria-label", name1 + " / " + name2); zu.title = name1 + " / " + name2; }
      if (zu) zu.addEventListener("click", function () { h.hidden = true; try { localStorage.setItem(MERK, "1"); } catch (e) { /* s. o. */ } });
    }
  }

  // 3. Beispieldaten: jede Datendatei (window.KIEZ_*), die fixture: true trägt, macht den Hinweis sichtbar. Der erste
  // Aufruf merkt sich die Dateien, die mit der Seite geladen wurden (die Datenskripte stehen vor rahmen.js).
  var anfang = null, voll = null;
  function beispiel() {
    var b = document.getElementById("beispieldaten"); if (!b) return;
    var namen = Object.keys(window).filter(function (k) {
      var v = k.indexOf("KIEZ_") === 0 ? window[k] : null;
      return v && typeof v === "object" && v.fixture === true;
    });
    if (anfang === null) { anfang = namen.slice(); voll = b.textContent; }
    var nachgeladen = namen.length > 0 && namen.every(function (k) { return anfang.indexOf(k) < 0; });
    var zweite = b.getAttribute("data-nachgeladen");
    b.textContent = nachgeladen && zweite ? zweite : voll;
    b.hidden = !namen.length;
    b.setAttribute("data-dateien", namen.sort().join(" "));
    b.setAttribute("data-fassung", nachgeladen && zweite ? "nachgeladen" : "seite");
  }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", beispiel); else beispiel();
  window.KIEZ_BEISPIEL_PRUEFEN = beispiel;   // für Seiten, die Daten nachladen
})();
