# Wartung, Updates, Backups und Fehlerbehebung

## Aktuellen Status prüfen

```bash
cd /opt/moo-rist-single-manager
sudo docker compose ps
sudo docker compose logs --tail=100 manager
```

Bei einer benutzerdefinierten Installation `/opt/moo-rist-single-manager` durch den tatsächlichen Pfad ersetzen.

## Update einer bestehenden Installation

**Vorher ein eigenes externes Backup erstellen**, insbesondere von `data/` und `.env`. Das Skript erstellt zusätzlich ein lokales Backup.

```bash
cd ~
git clone https://github.com/mikeauftour/moo-rist-manager.git moo-rist-manager-update
cd moo-rist-manager-update
sudo bash install.sh upgrade
```

`mikeauftour` ist der GitHub-Benutzername. Für eine **benutzerdefinierte Installation**:

```bash
sudo env INSTALL_DIR=/PFAD/ZUR/BESTEHENDEN/INSTALLATION bash install.sh upgrade
```

Das Skript sichert Dateien und `data/` im Unterordner `backups/` und baut nur den Manager neu. Die RIST-Streamcontainer werden dabei nicht gezielt neu gestartet. Der Manager ist kurz nicht erreichbar.

**Besonderheit bei bestehenden ZimaBlade-Installationen:** Der frühere Pfad war `/media/MeinNAS/docker-projects/moo-rist-single-manager`. Diesen Pfad nur verwenden, wenn er auf deinem Gerät tatsächlich stimmt.

## Backup von Hand

```bash
sudo tar -czf "$HOME/moo-rist-backup-$(date +%Y%m%d).tar.gz" -C /opt moo-rist-single-manager
```

Das Archiv enthält sensible Zugangsdaten! Sicher und nicht öffentlich aufbewahren. Das Beispiel gilt für den Standard-Installationspfad.

## Fehlerbehebung

**Weboberfläche nicht erreichbar:** `sudo docker compose ps`, `.env`, IP-Adresse (`hostname -I`) und TCP-Port 3000 prüfen. Bei Änderungen an `.env` den Manager-Service mit `sudo docker compose up -d --no-deps --force-recreate manager` neu erstellen.

**Docker Compose fehlt:** `sudo docker compose version` ausführen. Auf Ubuntu/Debian mit eingerichtetem Docker-Repository `sudo apt install docker-compose-plugin` installieren.

**Ein Stream startet nicht:** UDP-Portkonflikte und `sudo docker ps -a` prüfen. Andere Docker-Projekte nicht pauschal stoppen.

**Kein Empfang von unterwegs:** LAN-IP ist aus dem Mobilfunknetz normalerweise nicht erreichbar. Prüfe öffentliche IP, CGNAT, UDP-Portweiterleitung oder VPN sowie Zugangsdaten.

**„Keine Messdaten“:** Der Receiver erhält möglicherweise keinen aktuellen RIST-Datenstrom. Logs im Manager aufklappen und Verbindungsstatus prüfen.

## Niemals bei laufenden Fremdprojekten verwenden

Keine globalen Befehle wie `docker system prune -a`, `docker stop $(docker ps -q)` oder das Entfernen aller Docker-Volumes ausführen. Diese könnten andere Anwendungen beschädigen.
