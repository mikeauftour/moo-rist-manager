# Dateien auf GitHub hochladen

Repository: https://github.com/mikeauftour/moo-rist-manager

1. ZIP-Datei lokal entpacken.
2. Im GitHub-Repository **Add file → Upload files** auswählen.
3. **Inhalt des entpackten Ordners** hochladen (einschließlich versteckter Dateien wie `.gitignore` und `.github/workflows/tests.yml`).
4. **Commit changes** wählen.
5. Prüfen, dass `manager.py`, `install.sh`, `compose.yaml`, `Dockerfile`, `.env.example` und die Dokumentation im Hauptverzeichnis stehen.
6. Erst nach einem erfolgreichen Installationstest einen Release `v1.0.0` anlegen.

**Niemals** `.env`, `data/`, `backups/`, Passwortdateien oder persönliche RIST-Zugangsdaten hochladen.
