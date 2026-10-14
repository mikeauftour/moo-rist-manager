#!/usr/bin/env bash
set -Eeuo pipefail
SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-/opt/moo-rist-single-manager}"
MODE="${1:-install}"
if [[ "$MODE" != install && "$MODE" != upgrade ]]; then
  echo 'Usage: sudo bash install.sh [install|upgrade]'; exit 2
fi
if [[ $EUID -ne 0 ]]; then echo 'Bitte mit sudo/root starten.'; exit 1; fi
for c in docker python3; do command -v "$c" >/dev/null || { echo "$c fehlt."; exit 1; }; done
docker info >/dev/null || { echo 'Docker-Daemon nicht erreichbar.'; exit 1; }
docker compose version >/dev/null || { echo 'Docker Compose Plugin fehlt.'; exit 1; }
python3 -m py_compile "$SOURCE_DIR/manager.py"
if [[ "$MODE" == install ]]; then
  if [[ -e "$INSTALL_DIR" ]]; then echo "Ziel existiert: $INSTALL_DIR; Abbruch."; exit 1; fi
  if docker ps -a --format '{{.Names}}' | grep -Eq '^moo-rist-single-manager-manager-1$'; then
    echo 'Ein Moo-RIST Manager läuft/existiert bereits. Keine zweite Installation mit demselben Projektnamen.'; exit 1
  fi
  if docker ps -a --format '{{.Names}}' | grep -Eq '^moo-single-[0-9]+-(rx|tx)$'; then
    echo 'Vorhandene Moo-RIST Streamcontainer entdeckt. Keine neue Installation; nutze Upgrade der bestehenden Installation.'; exit 1
  fi
  mkdir -p "$INSTALL_DIR/data"
  chmod 700 "$INSTALL_DIR/data"
  cp "$SOURCE_DIR/manager.py" "$SOURCE_DIR/Dockerfile" "$SOURCE_DIR/compose.yaml" "$INSTALL_DIR/"
  cp "$SOURCE_DIR/.env.example" "$INSTALL_DIR/.env"
  chmod 600 "$INSTALL_DIR/.env"
  echo "Installationsordner: $INSTALL_DIR"
  echo 'Standardmäßig nur lokal (127.0.0.1:3000). Für LAN die .env anpassen.'
else
  [[ -f "$INSTALL_DIR/compose.yaml" && -f "$INSTALL_DIR/manager.py" ]] || { echo "Keine bestehende Installation: $INSTALL_DIR"; exit 1; }
  [[ "$SOURCE_DIR" != "$INSTALL_DIR" ]] || { echo 'Updatepaket bitte außerhalb des Zielordners entpacken.'; exit 1; }
  PROJECT="$(cd "$INSTALL_DIR" && docker compose config --format json | python3 -c 'import json,sys;print(json.load(sys.stdin)["name"])')"
  [[ "$PROJECT" == moo-rist-single-manager ]] || { echo "Unerwartetes Compose-Projekt: $PROJECT"; exit 1; }
  BACKUP="$INSTALL_DIR/backups/$(date +%Y%m%d-%H%M%S)"
  mkdir -p "$BACKUP"
  chmod 700 "$INSTALL_DIR/backups" "$BACKUP"
  cp -a "$INSTALL_DIR/manager.py" "$INSTALL_DIR/compose.yaml" "$INSTALL_DIR/Dockerfile" "$BACKUP/"
  [[ ! -f "$INSTALL_DIR/.env" ]] || cp -a "$INSTALL_DIR/.env" "$BACKUP/"
  if [[ -d "$INSTALL_DIR/data" ]]; then
    cp -a "$INSTALL_DIR/data" "$BACKUP/data"
    chmod -R go-rwx "$BACKUP/data"
  fi
  cp "$SOURCE_DIR/manager.py" "$SOURCE_DIR/Dockerfile" "$SOURCE_DIR/compose.yaml" "$INSTALL_DIR/"
  if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    # Preserve prior LAN accessibility for upgrades of the original 3000:3000 configuration.
    printf 'MANAGER_BIND_IP=0.0.0.0\nMANAGER_PORT=3000\n' > "$INSTALL_DIR/.env"
    chmod 600 "$INSTALL_DIR/.env"
  fi
  echo "Sicherung: $BACKUP"
fi
cd "$INSTALL_DIR"
docker compose config --quiet
docker compose up -d --build --no-deps manager
docker compose ps manager
echo 'Fertig. RIST-Streamcontainer wurden nicht gezielt neu gestartet.'
