# Jarvis Cards Updater Home Assistant Integration

MVP Custom Integration für bezahlte/proprietäre Jarvis Home Assistant Cards.

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
sensor.jarvis_cards_installierte_version
sensor.jarvis_cards_verfugbare_version
```

Die exakten Entity-IDs kann Home Assistant je nach Namensschema leicht anders vergeben.

## Lovelace Resource

Die Cards werden lokal installiert nach:

```text
/www/jarvis/jarvis-cards.js
```

Die Lovelace Resource sollte auf diese Datei zeigen:

```text
/local/jarvis/jarvis-cards.js?v=1.0.1
```

Wichtig: Nach einem Update Dashboard/Browser neu laden. Home Assistant und Browser cachen JavaScript-Dateien aggressiv.

## MVP Funktionen

- Lizenz-Key speichern
- Manifest vom Update Server abrufen
- verfügbare Version anzeigen
- installierte Version speichern
- Update per Update Entity oder Button starten
- `jarvis-cards.js` herunterladen
- SHA256 gegen Manifest prüfen
- Backup der vorhandenen Datei erstellen
- Datei nach `/www/jarvis/jarvis-cards.js` schreiben
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

## Sicherheit

- Lizenz-Key wird in der Home Assistant Config Entry gespeichert.
- Lizenz-Key wird als HTTP Header gesendet, nicht als URL-Query.
- Download wird nur installiert, wenn SHA256 exakt mit dem Manifest übereinstimmt.
- Vor Überschreiben der lokalen Card-Datei wird ein Backup angelegt.
- Das private GitHub Repo wird nicht beim Kunden verwendet.

## Bekannte MVP-Grenzen

Noch nicht enthalten:

- automatischer Lovelace Resource Eintrag
- Rollback Button
- Auto-Update
- Beta-Kanal UI
- Changelog als eigene UI-Karte
- Diagnose-Export
- Kundenportal/Lizenzverwaltung

## Entwicklung / Syntaxcheck

Im Repo:

```bash
python3 -m py_compile custom_components/jarvis_updater/*.py
```

Die Integration benötigt Home Assistant Runtime-Module und wird vollständig in Home Assistant getestet.
