# Jarvis Cards Updater Home Assistant Integration

Custom Integration für bezahlte/proprietäre Jarvis Home Assistant Cards.

Die Integration lädt `jarvis-cards.js` von `https://updates.justsmart.at`, prüft die SHA256-Prüfsumme, erstellt ein Backup der vorhandenen lokalen Datei und installiert die neue Datei in den von Home Assistant bereitgestellten `www`-Ordner. In der Home-Assistant-Dateiansicht/Samba sieht das so aus:

```text
/www/jarvis/jarvis-cards.js
```

Technisch schreibt die Integration intern relativ zu `hass.config.path()` nach `www/jarvis/jarvis-cards.js`; das entspricht dem sichtbaren `/www/jarvis/jarvis-cards.js` und wird als `/local/jarvis/jarvis-cards.js` ausgeliefert.

## Installation beim Kunden

1. Ordner kopieren nach:

```text
/config/custom_components/jarvis_updater/
```

2. Home Assistant neu starten.

3. In Home Assistant öffnen:

```text
Einstellungen -> Geräte & Dienste -> Integration hinzufügen -> Jarvis Cards Updater
```

4. Lizenz-Key eingeben.

5. Nach erfolgreicher Einrichtung entstehen Entities wie:

```text
update.jarvis_cards_cards
button.jarvis_cards_update_installieren
button.jarvis_cards_update_prufen
button.jarvis_cards_rollback_ausfuhren
select.jarvis_cards_rollback_version
sensor.jarvis_cards_installierte_version
sensor.jarvis_cards_verfugbare_version
sensor.jarvis_cards_kunde
sensor.jarvis_cards_lizenzstatus
sensor.jarvis_cards_changelog
sensor.jarvis_cards_browser_cache_hinweis
```

Die exakten Entity-IDs kann Home Assistant je nach Namensschema leicht anders vergeben.

## Lovelace Resource und Browser Cache

Die Cards werden lokal installiert nach:

```text
/www/jarvis/jarvis-cards.js
```

Die Integration erstellt/aktualisiert die Lovelace Resource automatisch als JavaScript-Modul, inklusive Cache-Buster:

```text
/local/jarvis/jarvis-cards.js?v=1.0.1
```

Nach jedem Installieren oder Rollback erzeugt die Integration außerdem eine persistente Home-Assistant-Benachrichtigung mit der aktuellen Resource URL und dem Hinweis: Wenn noch eine alte Karte sichtbar ist, Dashboard neu öffnen, Browser/App hart neu laden oder Browser-Cache leeren.

## Rollback

Jedes Update legt vor dem Überschreiben ein Backup in `/www/jarvis/backups/` ab.

Rollback-Ablauf:

1. In `select.jarvis_cards_rollback_version` eine Backup-Datei auswählen.
2. `button.jarvis_cards_rollback_ausfuhren` drücken.
3. Falls nötig Browser/App neu laden oder Cache leeren.

Vor dem Rollback wird die aktuell installierte Datei zusätzlich nach `/www/jarvis/backups/pre-rollback/` kopiert.

## Funktionen

- Lizenz-Key speichern
- Manifest vom Update Server abrufen
- verfügbare Version anzeigen
- installierte Version speichern
- Kundenname anzeigen
- Lizenzstatus und Ablaufdatum anzeigen, wenn vom Server geliefert
- Changelog anzeigen
- Update per Update Entity oder Button starten
- `jarvis-cards.js` herunterladen
- SHA256 gegen Manifest prüfen
- Backup der vorhandenen Datei erstellen
- Rollback auf lokale Backups ausführen
- Lovelace Resource automatisch setzen/aktualisieren
- Browser-Cache-Hinweis anzeigen
- Installationsstatus in HA Storage speichern

## Server API

Standard Update Server:

```text
https://updates.justsmart.at
```

Manifest:

```http
GET /api/manifest
X-Jarvis-License: <license-key>
```

Download:

```http
GET /api/download/{file_name}
X-Jarvis-License: <license-key>
```

Das Manifest kann optional Lizenzmetadaten enthalten:

```json
{
  "license": {
    "customer": "Musterkunde",
    "status": "active",
    "expires_at": "2027-01-01T00:00:00Z"
  }
}
```

## Lokale Dateien auf Home Assistant

Ziel-Datei:

```text
/www/jarvis/jarvis-cards.js
```

Backups:

```text
/www/jarvis/backups/
```

Persistenter Integrationsstatus:

```text
/config/.storage/jarvis_updater_data_<entry_id>
```

Lovelace Resource Storage:

```text
/config/.storage/lovelace_resources
```

## Sicherheit

- Lizenz-Key wird in der Home Assistant Config Entry gespeichert.
- Lizenz-Key wird als HTTP Header gesendet, nicht als URL-Query.
- Download wird nur installiert, wenn SHA256 exakt mit dem Manifest übereinstimmt.
- Vor Überschreiben der lokalen Card-Datei wird ein Backup angelegt.
- Das private GitHub Repo wird nicht beim Kunden verwendet.

## Entwicklung / Syntaxcheck

Im Repo:

```bash
python3 -m py_compile custom_components/jarvis_updater/*.py
```

Die Integration benötigt Home Assistant Runtime-Module und wird vollständig in Home Assistant getestet.
