# Installation für Anfänger – von Null bis zum ersten Stream

Diese Anleitung richtet sich an Einsteiger mit einem **neuen Linux-Server** und Terminal-/SSH-Zugang. Die Schritte für Docker gelten für **Ubuntu oder Debian**. Bei anderen Distributionen die offiziellen Docker-Anleitungen verwenden.

> **Bereits Docker installiert?** Springe zu [Schritt 4](#schritt-4-versionen-prüfen). **Bestehender Moo-RIST-Manager?** Nicht neu installieren, sondern die [Updateanleitung](WARTUNG.md) lesen.

## Schritt 1 – Am Server anmelden

Auf dem Server direkt ein Terminal öffnen oder von einem anderen Computer per SSH verbinden:

```bash
ssh BENUTZER@SERVER-IP
```

`BENUTZER` ist dein Linux-Benutzer, `SERVER-IP` die IP des Servers, beispielsweise `192.168.1.50`. Die IP deines Servers erfährst du mit `hostname -I`. Der Beispielwert ist **nicht** die IP, die du übernehmen musst.

## Schritt 2 – Linux-System erkennen und Hilfsprogramme installieren

```bash
cat /etc/os-release
sudo apt update
sudo apt install -y ca-certificates curl git python3
```

Falls `sudo` nicht vorhanden ist und du als `root` angemeldet bist, kannst du die Befehle ohne `sudo` ausführen. Die weiteren Beispiele verwenden `sudo`.

## Schritt 3 – Docker Engine und Docker Compose v2 installieren

**Nur auf einem neuen Server ohne vorhandene Docker-Installation durchführen.** Eine bereits funktionierende Docker-Installation mit anderen Projekten nicht entfernen oder überschreiben.

Die folgenden Befehle richten das **offizielle Docker-APT-Repository** ein. Unterstützt werden hier Ubuntu und Debian. Docker empfiehlt den Paketmanager für reguläre Installationen und nicht das schnelle `get.docker.com`-Skript für Produktionsserver.

**3a. Docker-Repository einrichten** (ganzen Block kopieren):

```bash
set -e
. /etc/os-release
case "$ID" in
  ubuntu) DOCKER_DIST=ubuntu; DOCKER_CODENAME="${UBUNTU_CODENAME:-$VERSION_CODENAME}" ;;
  debian) DOCKER_DIST=debian; DOCKER_CODENAME="$VERSION_CODENAME" ;;
  *) echo "Nur Ubuntu oder Debian: gefunden $ID"; exit 1 ;;
esac
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL "https://download.docker.com/linux/${DOCKER_DIST}/gpg" -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
printf 'Types: deb\nURIs: https://download.docker.com/linux/%s\nSuites: %s\nComponents: stable\nArchitectures: %s\nSigned-By: /etc/apt/keyrings/docker.asc\n' \
  "$DOCKER_DIST" "$DOCKER_CODENAME" "$(dpkg --print-architecture)" | sudo tee /etc/apt/sources.list.d/docker.sources
sudo apt update
```

Falls `apt` Konflikte mit älteren Docker-Paketen meldet, **nicht blind Pakete entfernen**: zuerst die Hinweise der offiziellen Docker-Dokumentation lesen. Bestehende Docker-Projekte könnten betroffen sein.

**3b. Docker und Compose installieren:**

```bash
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

Compose v2 wird als Plugin installiert. Der richtige Befehl lautet **`docker compose`** mit Leerzeichen, nicht `docker-compose`.

Offizielle Quellen: [Docker für Ubuntu](https://docs.docker.com/engine/install/ubuntu/), [Docker für Debian](https://docs.docker.com/engine/install/debian/), [Compose-Plugin](https://docs.docker.com/compose/install/linux/).

## Schritt 4 – Versionen prüfen

```bash
sudo docker --version
sudo docker compose version
python3 --version
git --version
sudo docker info >/dev/null && echo "Docker läuft"
```

Optionaler Docker-Funktionstest:

```bash
sudo docker run --rm hello-world
```

Wenn `hello-world` eine Erfolgsmeldung ausgibt, funktioniert Docker. Die Anwendung verwendet Python im Container; **Python 3 auf dem Host** benötigt das Installationsskript für die Vorprüfung.

## Schritt 5 – Projekt von GitHub herunterladen

Öffne das veröffentlichte GitHub-Repository. Dort auf den grünen Button **Code → HTTPS** klicken und die URL kopieren. Sie endet auf `.git`.

```bash
cd ~
git clone https://github.com/mikeauftour/moo-rist-manager.git
cd moo-rist-manager
```

Der Repository-Besitzer ist bereits `mikeauftour`; die URL kann unverändert verwendet werden. Alternative ohne Git: Auf GitHub **Code → Download ZIP**, ZIP auf den Server übertragen, entpacken und in den entpackten Ordner wechseln.

## Schritt 6 – Manager installieren

**Nur für eine Neuinstallation.** Der Standardpfad ist `/opt/moo-rist-single-manager`.

```bash
sudo bash install.sh install
```

Das Skript prüft Docker, Compose und Python, legt die Konfiguration an und startet den Manager. Es bricht ab, wenn bereits eine Installation oder Moo-RIST-Streamcontainer erkannt werden.

Prüfen:

```bash
cd /opt/moo-rist-single-manager
sudo docker compose ps
sudo docker compose logs --tail=30 manager
```

## Schritt 7 – Weboberfläche im Heimnetz oder auf einem externen Server öffnen

**Aus Sicherheitsgründen** lauscht der Manager zunächst nur auf `127.0.0.1:3000`. Das gilt **auch auf einem externen Server (VPS)**: `http://ÖFFENTLICHE-IP:3000` funktioniert mit dieser Standardeinstellung nicht.

**Empfehlung bei externen Servern:** Belasse `MANAGER_BIND_IP=127.0.0.1` und verwende für den Zugriff einen SSH-Tunnel, ein VPN oder eine HTTPS-Domain mit Reverse-Proxy und zusätzlicher Authentisierung/Zugriffsbeschränkung. Einen offenen HTTP-Zugang auf Port 3000 im Internet vermeiden: Der Manager hat Docker-Socket-Zugriff.

**Nur im vertrauenswürdigen Heimnetz:** Wenn du ihn direkt von einem PC im selben Netz öffnen möchtest, trage die **LAN-IP des Linux-Servers** ein:

```bash
hostname -I
sudo nano /opt/moo-rist-single-manager/.env
```

Dort zum Beispiel (nur ein Beispiel!):

```ini
MANAGER_BIND_IP=192.168.1.50
MANAGER_PORT=3000
```

In `nano`: `Strg+O`, Enter, `Strg+X` zum Speichern und Schließen.

Dann den **Manager-Service** mit neuer Portbindung erstellen:

```bash
cd /opt/moo-rist-single-manager
sudo docker compose up -d --no-deps --force-recreate manager
```

Nun im Browser eines Geräts im **gleichen Heimnetz** öffnen:

```text
http://SERVER-IP:3000
```

Ersetze `SERVER-IP` durch deine echte Server-IP. Bei einer Server-IP `192.168.1.50` wäre das `http://192.168.1.50:3000`. Ist die Seite nicht erreichbar, prüfe Server-Firewall, LAN-IP und `sudo docker compose ps`. **Port 3000 nicht ungeschützt öffentlich freigeben!**

### Externer IONOS-/VPS-Server

Die Bindung lässt sich über `/opt/moo-rist-single-manager/.env` ändern. `MANAGER_BIND_IP=0.0.0.0` bindet den TCP-Port an alle Netzwerkschnittstellen, **auch an die öffentliche Adresse**. Das ist kein Schutzmechanismus und **keine empfohlene Standardkonfiguration**. Eine Freigabe darf nur hinter geeigneten Netzwerkschutzmaßnahmen erfolgen. Für einen dauerhaften externen Zugang wird eine HTTPS-Domain mit Reverse-Proxy und zusätzlichem Zugriffsschutz oder ein VPN empfohlen. RIST-UDP-Ports werden getrennt von der Manager-Weboberfläche konfiguriert.

## Schritt 8 – Ersteinrichtung

Im Browser:

1. Ein **Administratorpasswort** mit mindestens 12 Zeichen festlegen.
2. Einen **RIST-Benutzernamen** für den Hauptstream wählen.
3. Ein **RIST-Passwort** mit mindestens 12 Zeichen festlegen.
4. Einrichtung abschließen und anmelden. Optional „30 Tage angemeldet bleiben“ aktivieren – nur auf eigenen Geräten.

Die Passwörter sicher verwahren. Keine Passwörter in Screenshots, Support-Tickets oder öffentliche GitHub-Issues kopieren.

## Schritt 9 – Ersten Stream starten

Im Dashboard **Server 1 – Moo Standard → Starten** klicken. Die Standardports sind:

| Richtung | Protokoll | Port |
| --- | --- | --- |
| Eingang IRLBOX → Server | UDP / RIST | `2030` |
| Ausgang Server → Empfänger | UDP / RIST | `5556` |

Weitere Streams erhalten beispielsweise `2031`/`5557`, `2032`/`5558` usw. In der IRLBOX die **tatsächlich erreichbare Serveradresse** sowie den im Manager festgelegten RIST-Benutzernamen und das Passwort eintragen. **`192.168.x.x` funktioniert nur im passenden LAN/VPN.** Für mobile Übertragung von unterwegs muss der RIST-Eingangsport per VPN oder geeigneter UDP-Portweiterleitung erreichbar sein. Beachte Router, Firewall und öffentliche IPv4-/CGNAT-Situation.

Im Dashboard sollten nach Verbindungsaufbau **Aktiver RIST-Empfang**, Bitrate und RTT erscheinen. Die laufenden Container allein beweisen noch keine aktive Übertragung.


### Firewall und Portfreigaben für Moo-RIST (IONOS und andere VPS)

**Wichtig:** Die Weboberfläche (TCP 3000) und der eigentliche RIST-Datenverkehr (UDP) sind unabhängig. Damit eine IRLBOX von außen senden kann, muss der jeweilige **UDP-Eingangsport** in der Firewall des Hosting-Anbieters freigegeben sein. Für den RIST-Ausgang zu einem externen Empfänger muss auch dessen verwendeter **UDP-Ausgangs-/Relay-Port** erreichbar sein. Bei einem VPS sind Regeln der Anbieter-Firewall oft zusätzlich zu Linux-Firewall und Docker nötig.

**Ein einzelner Stream:**

| Richtung | Protokoll | Port | Zweck |
| --- | --- | --- | --- |
| Eingehend | UDP | `2030` | IRLBOX → Receiver (Server 1) |
| Eingehend | UDP | `5556` | Empfänger/OBS → RIST-Relay (Server 1), falls verwendet |

**Bis zu 10 Streams vorbereiten (empfohlene Portbereiche bei dieser Portvergabe):**

| Richtung | Protokoll | Portbereich | Zweck |
| --- | --- | --- | --- |
| Eingehend | UDP | `2030-2039` | RIST-Eingänge (IRLBOX) |
| Eingehend | UDP | `5556-5565` | RIST-Ausgänge/Relay für Empfänger |

| Stream | RIST-Eingang UDP | RIST-Ausgang UDP |
| --- | --- | --- |
| 1 | 2030 | 5556 |
| 2 | 2031 | 5557 |
| 3 | 2032 | 5558 |
| 4 | 2033 | 5559 |
| 5 | 2034 | 5560 |
| 6 | 2035 | 5561 |
| 7 | 2036 | 5562 |
| 8 | 2037 | 5563 |
| 9 | 2038 | 5564 |
| 10 | 2039 | 5565 |

Die Tabelle zeigt die fortlaufende Standardvergabe. **Maßgeblich sind immer die tatsächlich im Manager angezeigten Ports** – etwa nach dem Löschen oder Neu-Anlegen von Streams.

#### IONOS Cloud Panel: Schritt für Schritt

1. Im **IONOS Cloud Panel** anmelden und unter **Netzwerk → Firewall-Richtlinien** (Bezeichnung kann je nach IONOS-Produkt variieren) die dem Server zugewiesene Richtlinie öffnen.
2. Bei **eingehenden Regeln** eine Regel mit **Protokoll UDP**, **Portbereich `2030-2039`** und **Aktion Zulassen** erstellen.
3. Eine weitere eingehende Regel mit **Protokoll UDP**, **Portbereich `5556-5565`** und **Aktion Zulassen** erstellen.
4. Als Quelle nach Möglichkeit die bekannten öffentlichen IP-Adressen der Encoder bzw. Empfänger einschränken; bei wechselnden mobilen IPs muss die erforderliche Erreichbarkeit berücksichtigt werden.
5. **Speichern/Übernehmen**, sicherstellen, dass die Firewall-Richtlinie dem richtigen Server zugewiesen ist, und den Aktivierungsstatus kontrollieren. Ein Neustart von Ubuntu/Docker ist für reine Anbieter-Firewall-Regeln normalerweise nicht nötig.
6. Wenn die neuen Bereichsregeln aktiv sind, können überflüssige gleichwertige Einzelregeln für `2030` und `5556` entfernt werden.

**Andere Hoster:** Sinngemäß dieselben eingehenden UDP-Regeln in der Netzwerk-/Cloud-Firewall des Providers anlegen. Auf einem Heimserver zusätzlich nötige Router-Portweiterleitungen zum Linux-Rechner einrichten.

#### Auf Ubuntu und in Docker prüfen

```bash
sudo ufw status verbose
sudo docker ps --format 'table {{.Names}}\t{{.Ports}}'
sudo ss -lunp | grep -E ':(2030|5556)\\b' || true
```

Ein inaktives UFW bedeutet **nicht automatisch**, dass keine andere Firewall (z. B. nftables/iptables oder die Anbieter-Firewall) filtert. Docker veröffentlicht nur die Ports **laufender** Streamcontainer. Eine Freigabe eines Portbereichs startet nicht automatisch weitere Streams.

Zum Testen bei **aktiv sendender IRLBOX**:

```bash
sudo tcpdump -ni any 'udp dst port 2030'
```

Falls `tcpdump` fehlt: `sudo apt install -y tcpdump`. **0 erfasste Pakete** während eines tatsächlichen Sendeversuchs deuten auf falsche Ziel-IP/Port, fehlende Weiterleitung oder eine vorgelagerte Firewall hin; auch die Encoder-Konfiguration prüfen. Bei sichtbaren Paketen anschließend die RIST-Anmeldedaten und Receiver-Logs kontrollieren.

**Sicherheit:** Nur benötigte UDP-Portbereiche öffnen. **TCP 3000 nicht ungeschützt öffentlich freigeben**: Der Manager kann über Docker weitreichende Host-Rechte ausüben. Für die Verwaltung von außen VPN oder HTTPS mit zusätzlicher Zugangskontrolle verwenden. SSH-Zugang bei Änderungen an Linux-Firewalls unbedingt erhalten.

## Fertig!

Für Bedienung siehe [BEDIENUNG.md](BEDIENUNG.md), für Updates/Fehler siehe [WARTUNG.md](WARTUNG.md).
