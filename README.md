# Linux-Bcache-Monitor

## Installation (einfach)

Dieses `curl` lädt die Datei in den **aktuellen Pfad** und macht sie direkt ausführbar:

```bash
curl -fsSL https://raw.githubusercontent.com/fabianschmeltzer/Linux-Bcache-Monitor/main/bcache-monitor -o ./bcache-monitor && chmod +x ./bcache-monitor
```

Danach starten mit:

```bash
./bcache-monitor
```


## Auto-Update

Der Auto-Update-Check ist standardmäßig aktiv. Beim Start wird immer geprüft, ob eine neue Version verfügbar ist:

```bash
export BCACHE_MONITOR_VERSION_URL="https://raw.githubusercontent.com/fabianschmeltzer/Linux-Bcache-Monitor/main/VERSION"
export BCACHE_MONITOR_SCRIPT_URL="https://raw.githubusercontent.com/fabianschmeltzer/Linux-Bcache-Monitor/main/bcache-monitor"
export BCACHE_MONITOR_SHA256_URL="https://raw.githubusercontent.com/fabianschmeltzer/Linux-Bcache-Monitor/main/bcache-monitor.sha256"
./bcache-monitor
```

Sicherheits-/Stabilitätschecks im Update-Prozess:
- Update nur bei gültiger Versionsnummer (`x.y.z`) und nur wenn neuer als lokal.
- Script muss mit Python-Shebang starten.
- Optionale SHA-256 Integritätsprüfung über `BCACHE_MONITOR_SHA256_URL`.
- Größenlimit für Payload (zu klein/zu groß wird abgelehnt).
- Atomarer Austausch über temporäre Datei (`os.replace`) statt Direkt-Overwrite.
