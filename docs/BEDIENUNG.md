# Bedienung des Moo-RIST Hosting Managers

## Streamverwaltung

Nach dem Login ist **Server 1 – Moo Standard** als nicht löschbarer Hauptstream vorhanden. Weitere Streams über „Stream hinzufügen“ mit Anzeigename, RIST-Benutzername und RIST-Passwort erstellen. Jeder Stream nutzt ein eigenes Receiver-/Forwarder-Containerpaar und eigene UDP-Ports.

| Stream | Eingang (UDP) | Ausgang (UDP) |
| --- | ---: | ---: |
| Server 1 | 2030 | 5556 |
| Server 2 | 2031 | 5557 |
| Server 3 | 2032 | 5558 |

„Starten“ und „Stoppen“ steuern den jeweiligen Stream. Passwort- oder RIST-Benutzernamenänderungen können einen Neustart des betroffenen Streams erfordern; die Oberfläche zeigt entsprechende Hinweise.

## Live-Überwachung verstehen

- **Receiver / Forwarder:** Docker-Containerstatus, nicht der Beweis einer RIST-Verbindung.
- **RIST-Verbindung:** Status aus aktuellen libRIST-Statistiken und relevanten Receiver-Logs; erkennt auch Offline- und Wiederverbindung.
- **Receiver-Netzwerkverkehr:** Gesamter Netzwerkverkehr am Receiver, einschließlich Protokoll-Overhead; **nicht** identisch mit Videobitrate.
- **RIST-Bitrate:** Vom libRIST-Receiver gemeldete Bitrate.
- **RTT:** Round Trip Time (Hin- und Rücklaufzeit) in Millisekunden; ein kleinerer Wert ist häufig günstiger.
- **Verlorene / fehlende / wiederhergestellte Pakete:** libRIST-Zähler aus den Statistikintervallen. Sie sind nicht automatisch eine Prozentquote.
- **Qualität / Wiederholungen:** libRIST-Qualitätswert und Wiederholungsanforderungen. Qualität 100 beweist allein nicht, dass ein Videobild ankommt.

Wenn die IRLBOX offline ist, zeigt die Überwachung „Getrennt“ oder „Kein Datenempfang“; alte RTT- und Qualitätswerte werden nicht als aktuelle Werte ausgegeben.

## Angemeldet bleiben

Beim Login kann optional „30 Tage angemeldet bleiben“ aktiviert werden. Es wird kein Klartext-Administratorpasswort im Browser abgelegt. Diese Funktion nur auf eigenen, vertrauenswürdigen Geräten nutzen. „Abmelden“ beendet die Sitzung.
