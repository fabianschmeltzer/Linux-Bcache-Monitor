# 🚀 Linux Bcache Monitor

A lightweight and fast **Linux bcache monitoring tool** for real-time performance analysis, IO statistics, and cache diagnostics.

> Perfect for homelabs, servers, and SSD + HDD cache setups.

---

## ✨ Features

- 📊 Real-time bcache statistics
- ⚡ Monitor SSD cache performance
- 💾 Analyze HDD + SSD hybrid setups
- 🧠 Simple CLI interface (no dependencies)
- 🔍 Detect IO bottlenecks
- 🐧 Works on all major Linux distributions

---

## 📸 Preview

![Demo](./assets/demo.png)

---

## 🧩 What is bcache?

**bcache** is a Linux kernel block layer that allows using an SSD as a cache for slower HDDs.

This tool helps you monitor:

- Cache hit ratio
- IO throughput
- Device performance
- System bottlenecks

---

## 🚀 Installation

Dieses `curl` lädt die Datei in den **aktuellen Pfad** und macht sie direkt ausführbar:

```bash
curl -fsSL https://raw.githubusercontent.com/fabianschmeltzer/Linux-Bcache-Monitor/main/bcache-monitor -o ./bcache-monitor && chmod +x ./bcache-monitor
```

---

## ℹ️ Info, Credits und rechtliche Hinweise

- **Version:** 0.5.10
- **Credits:** by Fabian Schmeltzer
- **KI-Hinweis:** Dieses Programm wurde mit KI-Unterstützung geschrieben und kann Fehler enthalten. Bitte prüfe kritische Ausgaben und verwende das Tool auf eigene Verantwortung.
- **Bugreports:** Bitte Fehler und Verbesserungsvorschläge über die GitHub-Issues melden: <https://github.com/fabianschmeltzer/Linux-Bcache-Monitor/issues>
- **Rechtlicher Hinweis:** Dies ist keine Rechtsberatung. Ohne explizite Open-Source-Lizenz gelten grundsätzlich die üblichen Urheberrechte; GitHub weist in seiner Dokumentation darauf hin, dass öffentliche Repositories ohne Lizenz zwar angesehen und innerhalb GitHub geforkt werden können, weitergehende Nutzung, Verteilung oder abgeleitete Werke aber eine passende Lizenz bzw. Erlaubnis benötigen. Für verbindliche Einschätzungen bitte juristischen Rat einholen.

## 📖 Was bedeuten die Werte?

- **EFF:** Cache-Effizienz aus `Total Hits / (Total Hits + Total Misses)`. Niedrige Werte zeigen, dass viele Zugriffe nicht aus dem SSD-Cache bedient werden.
- **DIRTY:** Datenmenge, die im Cache liegt und noch auf die HDD bzw. das Backing Device geschrieben werden muss. Besonders im Writeback-Modus wichtig.
- **MISS/HIT:** Verhältnis aktueller Misses pro Sekunde zu Hits pro Sekunde. Werte ab etwa `1.0` bedeuten, dass mindestens so viele Anfragen am Cache vorbeigehen wie aus dem Cache bedient werden.
- **LIVE HIT/s und MISS/s:** Live-Änderungsrate der bcache-Zähler pro Sekunde.
- **GRAPH:** Rot zeigt `MISS/s`, grün zeigt `HIT/s`; `◆` markiert den neuesten Punkt, `•` ältere Punkte.
- **H/M current/avg/peak:** Aktueller Wert, Fensterdurchschnitt und Spitzenwert.
- **MIX:** Prozentualer Anteil der aktuellen bcache-Ereignisse. `M` steht für Miss-Anteil, `H` für Hit-Anteil. Bei keiner Last zeigt das Tool `MIX idle`, weil Prozentwerte sonst irreführend wären.
- **Δ / DELTA:** Vergleich des aktuellen Werts mit dem Fensterdurchschnitt. Ist der Durchschnitt `0`, wird `n/a` angezeigt.
- **HEALTH:** Ampelbewertung aus Effizienz, Miss/Hit-Verhältnis und Miss-Trend.
- **SSD cache / Avail WB:** Cache-Größe und potentiell für Writeback verfügbarer Cache-Anteil, soweit über sysfs auslesbar.
- **HDD/backing:** Größe des bcache-Blockdevices und, falls gemountet, genutzter/freier Dateisystemplatz.
- **WB rate:** Von bcache gemeldete Hintergrund-Writeback-Rate (`writeback_rate`) als Bytes/s. Das ist die bcache-Drossel-/Zielrate und nicht zwingend identisch mit physischer HDD-IO.
- **Docker DISK:** Read- und Write-Rate aus Docker `BlockIO`-Deltas seit der letzten Aktualisierung.

Quellen zur Einordnung: Die [Linux-Kernel-Dokumentation](https://docs.kernel.org/admin-guide/bcache.html) beschreibt die bcache-sysfs-Werte wie `dirty_data`, `writeback_percent`, `writeback_rate`, `cache_available_percent`, `bucket_size` und `nbuckets`. [GitHub Docs](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) und [Choose a License](https://choosealicense.com/no-permission/) erläutern die rechtliche Ausgangslage bei Repositories ohne Lizenz.
