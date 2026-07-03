# Jarvis Cards Updater

Public HACS repository for the Jarvis Cards Updater Home Assistant integration.

This repository contains only the updater integration. The premium Jarvis Cards bundle is not shipped in this repository. After setup, the integration downloads licensed releases from the JustSmart/Jarvis update server and installs the card bundle locally in Home Assistant.

## Install via HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and choose "Custom repositories".
3. Add this repository URL:

   ```text
   https://github.com/prasterphilipp/jarvis-updater
   ```

4. Select category "Integration".
5. Install "Jarvis Cards Updater".
6. Restart Home Assistant.
7. Go to Settings -> Devices and services -> Add integration -> Jarvis Cards Updater.
8. Enter your license key.

## What it installs

The updater writes the licensed card bundle to the Home Assistant `www` folder:

```text
/www/jarvis/jarvis-cards.js
```

Home Assistant serves that file as:

```text
/local/jarvis/jarvis-cards.js
```

Use this Lovelace resource URL, updating the cache-busting version after card updates if needed:

```text
/local/jarvis/jarvis-cards.js?v=1.0.1
```

## Entities

After setup Home Assistant creates entities similar to:

```text
update.jarvis_cards_cards
button.jarvis_cards_update_installieren
button.jarvis_cards_update_prufen
sensor.jarvis_cards_installierte_version
sensor.jarvis_cards_verfugbare_version
```

Exact entity IDs can vary depending on your Home Assistant naming scheme.

## Security

- The license key is stored in the Home Assistant config entry.
- The license key is sent as an HTTP header, not as a URL query parameter.
- Downloads are verified against the SHA256 checksum from the manifest before installation.
- Existing local card files are backed up before replacement.

## Development check

```bash
python3 -m py_compile custom_components/jarvis_updater/*.py
```
