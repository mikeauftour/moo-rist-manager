# Moo-RIST Hosting Manager – V1.0 (Veröffentlichung in Vorbereitung)

Deutschsprachiger Web-Manager für mehrere Moo-RIST-Streams unter Linux mit Docker. Community-Projekt, keine offizielle Moo-RIST-Software.

## Für Einsteiger

➡️ [Vollständige Installationsanleitung](docs/INSTALLATION.md) – von Docker Engine über Docker Compose v2 und Python 3 bis zum ersten Start.

**Wichtig:** Der Quellcode und Installer werden noch ergänzt. Bitte vorerst keine Installationsbefehle aus diesem Repository ausführen.

## Geplante Funktionen der V1.0

- Mehrere unabhängige RIST-Streams und automatische UDP-Portvergabe
- Web-Dashboard zum Starten, Stoppen und Verwalten
- Live-Statistiken für Bitrate, RTT und Paketverlust
- Erkennung von Verbindungsabbrüchen und Wiederverbindungen
- Option „30 Tage angemeldet bleiben“
- Backup vor Updates

## Sicherheit

Der Manager benötigt Zugriff auf den Docker-Socket und damit weitreichende Rechte auf dem Host. Die Oberfläche nicht öffentlich über HTTP freigeben. Keine lokalen Zugangsdaten, `.env` oder `data/` hochladen.

## Kompatibilität

Zunächst Linux mit Docker Engine und Compose v2. Die Anwendung wurde auf einem ZimaBlade getestet; weitere Plattformen stehen noch aus.

## Lizenz

Eine Lizenz wird vor dem offiziellen Release festgelegt. Ohne Lizenz ist das Projekt nicht automatisch Open Source.
