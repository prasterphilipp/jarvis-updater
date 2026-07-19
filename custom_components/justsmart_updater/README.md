# JustSmart Cards Updater Home Assistant Integration

Custom Integration für bezahlte/proprietäre JustSmart Home Assistant Cards.

Die Integration lädt `justsmart-cards.js` von `https://updates.justsmart.at`, prüft die SHA256-Prüfsumme, erstellt ein Backup der vorhandenen lokalen Datei und installiert die neue Datei in den von Home Assistant bereitgestellten `www`-Ordner. In der Home-Assistant-Dateiansicht/Samba sieht das so aus:

```text
/www/justsmart/justsmart-cards.js
```

Technisch schreibt die Integration intern relativ zu `hass.config.path()` nach `www/justsmart/justsmart-cards.js`; das entspricht dem sichtbaren `/www/justsmart/justsmart-cards.js` und wird als `/local/justsmart/justsmart-cards.js` ausgeliefert.

## Installation beim Kunden

1. Ordner kopieren nach:

```text
/config/custom_components/justsmart_updater/
```

2. Home Assistant neu starten.

3. In Home Assistant öffnen:

```text
Einstellungen -> Geräte & Dienste -> Integration hinzufügen -> JustSmart Cards Updater
```

4. Lizenzschlüssel eingeben.

5. Nach erfolgreicher Einrichtung entstehen Entities wie:

```text
update.justsmart_cards_cards
button.justsmart_cards_update_installieren
button.justsmart_cards_update_prufen
button.justsmart_cards_rollback_ausfuhren
select.justsmart_cards_rollback_version
sensor.justsmart_cards_installierte_version
sensor.justsmart_cards_verfugbare_version
sensor.justsmart_cards_kunde
sensor.justsmart_cards_lizenzstatus
sensor.justsmart_cards_changelog
sensor.justsmart_cards_browser_cache_hinweis
```

Die exakten Entity-IDs kann Home Assistant je nach Namensschema leicht anders vergeben.

## Lovelace Resource und Browser Cache

Die Cards werden lokal installiert nach:

```text
/www/justsmart/justsmart-cards.js
```

Die Integration erstellt/aktualisiert die Lovelace Resource automatisch als JavaScript-Modul, inklusive Cache-Buster. Bestehende JustSmart Resource-Einträge werden dabei auch erkannt, wenn sie noch auf ältere versionierte `justsmart-cards...js` URLs zeigen:

```text
/local/justsmart/justsmart-cards.js?v=1.0.1
```

Nach jedem Installieren oder Rollback erzeugt die Integration außerdem eine persistente Home-Assistant-Benachrichtigung mit der aktuellen Ressourcen-URL und dem Hinweis: Wenn noch eine alte Karte sichtbar ist, Dashboard neu öffnen, Browser oder App vollständig neu laden oder Browser-Cache leeren.

## Rollback

Jedes Update legt vor dem Überschreiben ein Backup in `/www/justsmart/backups/` ab.

Rollback-Ablauf:

1. In `select.justsmart_cards_rollback_version` eine Backup-Datei auswählen.
2. `button.justsmart_cards_rollback_ausfuhren` drücken.
3. Falls nötig Browser/App neu laden oder Cache leeren.

Vor dem Rollback wird die aktuell installierte Datei zusätzlich nach `/www/justsmart/backups/pre-rollback/` kopiert.

## Funktionen

- Lizenzschlüssel speichern
- Manifest vom Update-Server abrufen
- verfügbare Version anzeigen
- installierte Version speichern
- Kundenname anzeigen
- Lizenzstatus und Ablaufdatum anzeigen, wenn vom Server geliefert
- Changelog anzeigen
- Update per Update Entity oder Button starten
- `justsmart-cards.js` herunterladen
- SHA256 gegen Manifest prüfen
- Backup der vorhandenen Datei erstellen
- Rollback auf lokale Backups ausführen
- Lovelace Resource automatisch setzen/aktualisieren
- Browser-Cache-Hinweis anzeigen
- Installationsstatus in HA Storage speichern

## Server API

Standard Update-Server:

```text
https://updates.justsmart.at
```

Manifest:

```http
GET /api/manifest
X-JustSmart-License: <license-key>
```

Download:

```http
GET /api/download/{file_name}
X-JustSmart-License: <license-key>
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
/www/justsmart/justsmart-cards.js
```

Backups:

```text
/www/justsmart/backups/
```

Persistenter Integrationsstatus:

```text
/config/.storage/justsmart_updater_data_<entry_id>
```

Lovelace Resource Storage:

```text
/config/.storage/lovelace_resources
```

## Sicherheit

- Lizenzschlüssel wird in der Home Assistant Config Entry gespeichert.
- Lizenzschlüssel wird als HTTP Header gesendet, nicht als URL-Query.
- Download wird nur installiert, wenn SHA256 exakt mit dem Manifest übereinstimmt.
- Vor Überschreiben der lokalen Card-Datei wird ein Backup angelegt.
- Das private GitHub Repo wird nicht beim Kunden verwendet.

## Entwicklung / Syntaxcheck

Im Repo:

```bash
python3 -m py_compile custom_components/justsmart_updater/*.py
```

Die Integration benötigt Home Assistant Runtime-Module und wird vollständig in Home Assistant getestet.
