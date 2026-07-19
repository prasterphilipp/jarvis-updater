# JustSmart Cards Updater

<p align="center">
  <img src="custom_components/justsmart_updater/brand/icon@2x.png" alt="JustSmart Cards Updater" width="144">
</p>

Public HACS repository for the JustSmart Cards Updater Home Assistant integration.

This repository contains only the updater integration. The premium JustSmart Cards bundle is not shipped in this repository. After setup, the integration downloads licensed releases from the JustSmart update server and installs the card bundle locally in Home Assistant.

## Install via HACS

1. Open HACS in Home Assistant.
2. Open the three-dot menu and choose "Custom repositories".
3. Add this repository URL:

   ```text
   https://github.com/prasterphilipp/justsmart-updater
   ```

4. Select category "Integration".
5. Install "JustSmart Cards Updater".
6. Restart Home Assistant.
7. Go to Settings -> Devices and services -> Add integration -> JustSmart Cards Updater.
8. Enter your license key.

## Versionierung

Der Updater und das Kartenpaket haben getrennte Versionsnummern. Die Updater-Version beschreibt die Home-Assistant-Integration; die in Home Assistant angezeigte verfügbare Version stammt aus dem Karten-Manifest des Update-Servers.

## What it installs

The updater writes the licensed card bundle to the Home Assistant `www` folder:

```text
/www/justsmart/justsmart-cards.js
```

Home Assistant serves that file as:

```text
/local/justsmart/justsmart-cards.js
```

The integration creates/updates the Lovelace module resource automatically with a cache-busting version. It updates both Home Assistant's live Lovelace resource collection and the persistent `.storage/lovelace_resources` data so the entry survives reloads/restarts. Existing JustSmart resource entries are recognized when they point to old local, GitHub/jsDelivr, or other `justsmart-cards...js` URLs, for example:

```text
/local/justsmart/justsmart-cards.js?v=1.0.1
```

If a browser still shows an older card after update or rollback, reopen the dashboard, hard-reload the browser/app, or clear the browser cache. Home Assistant also gets a persistent notification with the current resource URL after each install/rollback.

## Entities

After setup Home Assistant creates entities similar to:

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

Exact entity IDs can vary depending on your Home Assistant naming scheme.

## Rollback

Every update backs up the previously installed `/www/justsmart/justsmart-cards.js` into `/www/justsmart/backups`.

To roll back:

1. Select the desired backup in `select.justsmart_cards_rollback_version`.
2. Press `button.justsmart_cards_rollback_ausfuhren`.
3. Reload the dashboard/browser if Home Assistant still shows the old cached JavaScript.

Before rollback, the currently installed file is copied to `/www/justsmart/backups/pre-rollback` so it can still be recovered.

## License and changelog display

The update entity and sensors expose metadata returned by the update server:

- Customer name
- License status and expiry date if supplied by the server
- Available version, release date, checksum and file size
- Changelog entries
- Current Lovelace resource URL and browser-cache hint

## Security

- The license key is stored in the Home Assistant config entry.
- The license key is sent as an HTTP header, not as a URL query parameter.
- Downloads are verified against the SHA256 checksum from the manifest before installation.
- Existing local card files are backed up before replacement.

## Development check

```bash
python3 -m py_compile custom_components/justsmart_updater/*.py
```
