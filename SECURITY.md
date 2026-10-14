# Sicherheitshinweise

Dieses Projekt steuert Docker über den Docker-Socket (`/var/run/docker.sock`). Wer den Manager kompromittiert, kann dadurch weitreichende Kontrolle über den Host erhalten. Die Anwendung ist **nicht** für eine ungeschützte Veröffentlichung im Internet vorgesehen.

- Port 3000 nur im vertrauenswürdigen LAN zugänglich machen; für Fernzugriff VPN oder HTTPS mit zusätzlichem Zugriffsschutz nutzen.
- Administratorpasswort lang und einzigartig wählen. Remember Me nur auf eigenen Geräten verwenden.
- RIST-Passwörter liegen in `data/state.json` und Docker-Startparametern im Klartext. Host und Backups schützen.
- `.env`, `data/`, Backups, Logdateien und Zugangsdaten nicht auf GitHub hochladen.
- Images und Server regelmäßig aktualisieren; Änderungen zuerst auf einem Testsystem prüfen.
- Bekannte Einschränkung: HTTP-Verbindungen im LAN sind nicht verschlüsselt. Remember-Me-Cookies können ohne HTTPS auf dem Transportweg abgefangen werden.

Sicherheitslücken bitte nicht mit geheimen Zugangsdaten in öffentlichen Issues melden. Vor der Veröffentlichung sollte der Repository-Besitzer einen privaten Meldeweg festlegen.
