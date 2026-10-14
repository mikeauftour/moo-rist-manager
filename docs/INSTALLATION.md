# Installation – Schritt für Schritt (Ubuntu/Debian)

> **Status:** Der vollständige Installer und Quellcode werden noch veröffentlicht. Diese Anleitung ist bis dahin eine Vorbereitung; den abschließenden Installationsbefehl erst ausführen, wenn `install.sh` im Repository vorhanden ist.

## 1. Voraussetzungen

Ein Linux-Server mit Ubuntu oder Debian, Internetverbindung und einem Benutzer mit `sudo`-Rechten. Alle Befehle im Terminal des Servers ausführen. Für andere Distributionen gelten andere Installationsbefehle.

## 2. System aktualisieren

```bash
sudo apt update
sudo apt upgrade -y
```

## 3. Docker Engine und Docker Compose v2 installieren

Die folgenden Befehle gelten für **Ubuntu**. Für Debian die offizielle Debian-Anleitung verwenden:
https://docs.docker.com/engine/install/debian/

```bash
sudo apt install -y ca-certificates curl
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
sudo tee /etc/apt/sources.list.d/docker.sources > /dev/null <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}")
Components: stable
Signed-By: /etc/apt/keyrings/docker.asc
EOF
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Docker prüfen:

```bash
sudo systemctl enable --now docker
sudo docker run --rm hello-world
docker compose version
```

Docker-Dokumentation: https://docs.docker.com/engine/install/ubuntu/

**Hinweis:** `docker compose` mit Leerzeichen ist Compose v2. Das ältere `docker-compose` wird nicht benötigt.

## 4. Python 3 und Git installieren

```bash
sudo apt install -y python3 git
python3 --version
git --version
```

## 5. Projekt von GitHub herunterladen

```bash
git clone https://github.com/mikeauftour/moo-rist-manager.git
cd moo-rist-manager
ls -la
```

## 6. Manager installieren (erst nach Freigabe des vollständigen Codes)

Wenn die Datei `install.sh` vorhanden ist und der Release als installierbar gekennzeichnet wurde:

```bash
sudo bash install.sh install
```

**Nicht auf einer bestehenden Installation mit `install` überschreiben.** Für vorhandene Systeme wird ein separater Upgrade-Weg dokumentiert.

## 7. Erster Start und Netzwerk

Die Weboberfläche soll aus Sicherheitsgründen zunächst nur lokal erreichbar sein. Die konkrete Adresse und eine optionale Freigabe im Heimnetz werden nach Prüfung des finalen Installers ergänzt. Den Manager-Port niemals direkt ins öffentliche Internet weiterleiten.

Für RIST-Streams müssen die zugewiesenen UDP-Ports erreichbar sein. Router- und Firewallregeln nur für tatsächlich benötigte Ports öffnen.

## 8. Fehlerbehebung

```bash
sudo docker ps
docker compose version
sudo systemctl status docker
```

Bei Problemen keine Passwörter, RIST-URLs mit Zugangsdaten oder `.env` öffentlich posten.
