# Moo-RIST Hosting Manager — Version 1.0

Ein deutschsprachiger, browserbasierter Manager für mehrere Moo-RIST-Streams auf **einem Linux-Docker-Server**. Mit dunklem Dashboard, automatischer Portvergabe und Live-Statistiken für Bitrate, RTT, Paketverlust und Verbindungsstatus.

> **Wichtig:** Dies ist ein Community-Projekt, keine offizielle Software des Moo-RIST-Teams. Die Anwendung wurde auf einem ZimaBlade mit Moo-RIST 0.0.39 praktisch getestet. Eine breite Kompatibilitätsprüfung auf anderen Linux-Servern steht noch aus.

## 🚀 Neu hier? Hier anfangen!

**➡️ [Vollständige Schritt-für-Schritt-Installationsanleitung](docs/INSTALLATION.md)**

Die Anleitung erklärt alles von Anfang an: Linux-Voraussetzungen, **Docker Engine**, **Docker Compose v2**, **Python 3**, **Git**, GitHub-Download, Installation, Freigabe im Heimnetz, Ersteinrichtung und IRLBOX-Verbindung.

**Bereits alles installiert?** Für einen *neuen, leeren* Linux-Docker-Host:

```bash
git clone https://github.com/mikeauftour/moo-rist-manager.git
cd moo-rist-manager
sudo bash install.sh install
```

**Repository:** https://github.com/mikeauftour/moo-rist-manager

Die Weboberfläche ist standardmäßig nur auf `127.0.0.1:3000` des Servers erreichbar. **Das gilt auch für einen externen VPS bei IONOS oder anderen Hostern:** Die öffentliche IP ist damit zunächst nicht erreichbar. Für Zugriff von außerhalb nutze vorzugsweise VPN oder eine HTTPS-Domain mit Reverse-Proxy und zusätzlicher Zugriffskontrolle. Eine bewusste Freigabe per `MANAGER_BIND_IP=0.0.0.0` ist technisch möglich, darf aber nicht als sichere öffentliche Bereitstellung über HTTP verstanden werden. Siehe [Installationsanleitung](docs/INSTALLATION.md).

## Funktionen

- Fester, nicht löschbarer Hauptstream und zusätzliche unabhängige Streams
- Automatische UDP-Ports: Eingang `2030`, `2031`, … und Ausgang `5556`, `5557`, …
- Eigene RIST-Zugangsdaten pro Stream
- Starten, Stoppen, Bearbeiten und Löschen zusätzlicher Streams
- Docker-Containerstatus und tatsächlicher RIST-Empfang getrennt dargestellt
- libRIST-Messwerte aus Receiver-JSON-Logs: Bitrate, RTT, Paketstatistiken, Qualitätswert
- Offline-/Wiederverbindungserkennung, kompakte Live-Kacheln
- Optionale Anmeldung „30 Tage angemeldet bleiben“
- Backup beim Upgrade

## Voraussetzungen

- Linux-Server (Debian/Ubuntu sind in der Anleitung beschrieben)
- Docker Engine, Docker Compose **v2** (`docker compose`), Python 3 und Git auf dem Host
- Internetzugang für Container-Images und GitHub-Download
- Ein freier TCP-Port 3000 für die Weboberfläche sowie UDP-Ports für die Streams
- Root-/sudo-Zugang; ausreichende Rechte für Docker

**Nicht zugesagt:** Installation auf Windows/macOS mit Docker Desktop, alle CPU-Architekturen oder beliebige Linux-Distributionen. Das Moo-RIST-Image muss für die Architektur des Servers verfügbar sein.

## Portfreigaben für externe Streams

Für **10 Streams** in der Cloud-/Provider-Firewall die eingehenden UDP-Bereiche **`2030-2039`** (IRLBOX → Receiver) und **`5556-5565`** (Relay/Empfänger) freigeben. Die tatsächlich verwendeten Ports im Manager kontrollieren. Eine [Schritt-für-Schritt-Anleitung für IONOS und andere Anbieter](docs/INSTALLATION.md#firewall-und-portfreigaben-für-moo-rist-ionos-und-andere-vps) erklärt die Einrichtung und Fehlersuche. **TCP 3000 ist kein RIST-Port und darf nicht ungeschützt öffentlich geöffnet werden.**

## Sicherheit und Dokumentation

- [Installation für Anfänger](docs/INSTALLATION.md)
- [Bedienung und Streaming](docs/BEDIENUNG.md)
- [Updates, Backups und Fehlerbehebung](docs/WARTUNG.md)
- [Sicherheitshinweise](SECURITY.md)
- [Projekt auf GitHub veröffentlichen](docs/GITHUB-VEROEFFENTLICHUNG.md)

**Sicherheit:** Der Manager hat Zugriff auf `/var/run/docker.sock` und damit weitreichende Host-Rechte. RIST-Passwörter sind im lokalen Zustand und in Container-Startparametern sichtbar. **Port 3000 niemals ungeschützt ins öffentliche Internet weiterleiten.** Für Zugriff von außen VPN oder einen korrekt eingerichteten HTTPS-Zugang verwenden.

## Bestehende Installation aktualisieren

Nicht `install` über eine bestehende Installation ausführen! Siehe [Updateanleitung](docs/WARTUNG.md). Der Upgrade-Modus erstellt vorher ein Backup und aktualisiert nur den Manager-Service.

## Lizenz

Dieses Projekt steht unter der [MIT-Lizenz](LICENSE). Copyright © 2026 mikeauftour.
