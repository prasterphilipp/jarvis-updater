from __future__ import annotations

import hashlib
import logging
import re
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit

from homeassistant.components import persistent_notification
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JarvisAuthError, JarvisManifest, JarvisUpdateClient, JarvisUpdaterError
from .const import (
    ATTR_CACHE_HINT,
    ATTR_INSTALLED_SHA256,
    ATTR_RESOURCE_URL,
    BACKUP_DIR,
    DOMAIN,
    LOVELACE_RESOURCE_BASE_URL,
    LOVELACE_RESOURCE_ID,
    LOVELACE_RESOURCE_TYPE,
    LOVELACE_RESOURCES_STORAGE_KEY,
    STORAGE_KEY,
    STORAGE_VERSION,
    TARGET_DIR,
    TARGET_FILE,
)

_LOGGER = logging.getLogger(__name__)
_BACKUP_RE = re.compile(r"^jarvis-cards-(?P<version>.+)-(?P<stamp>\d{8}-\d{6})\.js$")


class JarvisUpdaterCoordinator(DataUpdateCoordinator[JarvisManifest]):
    """Fetch manifest, install releases and manage local Jarvis card resources."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry = entry
        self.client = JarvisUpdateClient(async_get_clientsession(hass), entry.data)
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
        self.resource_store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, LOVELACE_RESOURCES_STORAGE_KEY)
        self.storage: dict[str, Any] = {}
        self.last_install_result: str | None = None

    async def async_load_storage(self) -> None:
        self.storage = await self.store.async_load() or {}

    @property
    def installed_version(self) -> str | None:
        return self.storage.get("installed_version")

    @property
    def installed_sha256(self) -> str | None:
        return self.storage.get(ATTR_INSTALLED_SHA256)

    @property
    def resource_url(self) -> str:
        return str(self.storage.get(ATTR_RESOURCE_URL) or self._resource_url(self.installed_version))

    @property
    def cache_hint(self) -> str:
        return str(
            self.storage.get(ATTR_CACHE_HINT)
            or "Wenn eine alte Oberfläche sichtbar bleibt: Browser/App komplett neu laden oder den Cache leeren."
        )

    @property
    def target_path(self) -> str:
        return self.hass.config.path(TARGET_DIR, TARGET_FILE)

    @property
    def backup_dir(self) -> str:
        return self.hass.config.path(BACKUP_DIR)

    @property
    def selected_backup(self) -> str | None:
        selected = self.storage.get("selected_rollback_backup")
        if selected and selected in self.rollback_options:
            return str(selected)
        options = self.rollback_options
        return options[0] if options else None

    @property
    def rollback_options(self) -> list[str]:
        return [str(backup["file_name"]) for backup in self.backups if backup.get("file_name")]

    @property
    def backups(self) -> list[dict[str, str | int | None]]:
        return self._list_backups()

    async def _async_update_data(self) -> JarvisManifest:
        try:
            return await self.client.async_get_manifest()
        except JarvisAuthError as err:
            raise UpdateFailed(f"Lizenz ungültig: {err}") from err
        except JarvisUpdaterError as err:
            raise UpdateFailed(f"Manifest konnte nicht geladen werden: {err}") from err

    async def async_install_update(self) -> None:
        """Download, verify, back up and install the current release."""
        manifest = self.data or await self.client.async_get_manifest()
        content = await self.client.async_download(manifest)
        digest = hashlib.sha256(content).hexdigest()
        if digest != manifest.sha256:
            raise JarvisUpdaterError(
                f"SHA256 stimmt nicht: Download {digest}, Manifest {manifest.sha256}"
            )

        backup_path = await self.hass.async_add_executor_job(self._write_release, content, manifest, digest)
        resource_url = await self.async_ensure_lovelace_resource(manifest.latest_version)
        cache_hint = self._cache_hint(resource_url)
        self.storage.update(
            {
                "installed_version": manifest.latest_version,
                ATTR_INSTALLED_SHA256: digest,
                "installed_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "target_path": self.target_path,
                "last_backup_path": str(backup_path) if backup_path else None,
                "last_manifest": asdict(manifest),
                ATTR_RESOURCE_URL: resource_url,
                ATTR_CACHE_HINT: cache_hint,
            }
        )
        await self.store.async_save(self.storage)
        self.last_install_result = f"Jarvis Cards {manifest.latest_version} installiert"
        self._create_cache_notification("Jarvis Cards aktualisiert", self.last_install_result, resource_url)
        await self.async_request_refresh()

    def _write_release(self, content: bytes, manifest: JarvisManifest, digest: str) -> Path | None:
        target = Path(self.target_path)
        backup_dir = Path(self.backup_dir)
        target.parent.mkdir(parents=True, exist_ok=True)
        backup_dir.mkdir(parents=True, exist_ok=True)

        backup_path: Path | None = None
        if target.exists():
            stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            previous = self.installed_version or "unknown"
            backup_path = backup_dir / f"jarvis-cards-{previous}-{stamp}.js"
            shutil.copy2(target, backup_path)

        tmp_path = target.with_suffix(".js.tmp")
        tmp_path.write_bytes(content)
        if hashlib.sha256(tmp_path.read_bytes()).hexdigest() != digest:
            tmp_path.unlink(missing_ok=True)
            raise JarvisUpdaterError("SHA256 stimmt nach dem Schreiben nicht")
        tmp_path.replace(target)
        return backup_path

    async def async_select_backup(self, file_name: str) -> None:
        if file_name not in self.rollback_options:
            raise JarvisUpdaterError(f"Rollback-Datei nicht gefunden: {file_name}")
        self.storage["selected_rollback_backup"] = file_name
        await self.store.async_save(self.storage)
        self.async_update_listeners()

    async def async_rollback_selected(self) -> None:
        selected = self.selected_backup
        if not selected:
            raise JarvisUpdaterError("Kein Rollback-Backup verfügbar")
        backup_path = Path(self.backup_dir) / selected
        version = self._backup_version(backup_path) or "rollback"
        digest = await self.hass.async_add_executor_job(self._restore_backup, backup_path)
        resource_url = await self.async_ensure_lovelace_resource(version)
        cache_hint = self._cache_hint(resource_url)
        self.storage.update(
            {
                "installed_version": version,
                ATTR_INSTALLED_SHA256: digest,
                "installed_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "target_path": self.target_path,
                "last_rollback_path": str(backup_path),
                ATTR_RESOURCE_URL: resource_url,
                ATTR_CACHE_HINT: cache_hint,
            }
        )
        await self.store.async_save(self.storage)
        self.last_install_result = f"Rollback auf Jarvis Cards {version} ausgeführt"
        self._create_cache_notification("Jarvis Cards Rollback", self.last_install_result, resource_url)
        await self.async_request_refresh()

    def _restore_backup(self, backup_path: Path) -> str:
        if not backup_path.exists() or not backup_path.is_file():
            raise JarvisUpdaterError(f"Rollback-Datei nicht gefunden: {backup_path.name}")
        target = Path(self.target_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        content = backup_path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        pre_rollback_dir = Path(self.backup_dir) / "pre-rollback"
        pre_rollback_dir.mkdir(parents=True, exist_ok=True)
        if target.exists():
            stamp = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
            current = self.installed_version or "unknown"
            shutil.copy2(target, pre_rollback_dir / f"jarvis-cards-{current}-{stamp}.js")
        tmp_path = target.with_suffix(".js.tmp")
        tmp_path.write_bytes(content)
        tmp_path.replace(target)
        return digest

    async def async_ensure_lovelace_resource(self, version: str | None = None) -> str:
        """Create or update the Lovelace module resource with cache busting."""
        url = self._resource_url(version)
        # Update both paths deliberately:
        # - the live collection updates HA immediately when available
        # - the storage file keeps the change persistent across reload/restart
        # Some HA versions report a live collection update as successful while the
        # visible dashboard resource list is still backed by .storage/lovelace_resources.
        await self._async_update_lovelace_resource_collection(url)
        await self._async_update_lovelace_resource_storage(url)
        await self._async_reload_lovelace_resources()
        return url

    async def _async_update_lovelace_resource_storage(self, url: str) -> None:
        """Update the Lovelace resource storage as a fallback for HA versions without a live collection."""
        resources = await self.resource_store.async_load() or {}
        items = resources.get("items")
        if not isinstance(items, list):
            items = []

        new_item = {"id": LOVELACE_RESOURCE_ID, "type": LOVELACE_RESOURCE_TYPE, "url": url}
        updated_items: list[dict[str, Any]] = []
        matched = False
        for item in items:
            if not isinstance(item, dict):
                updated_items.append(item)
                continue
            if self._is_jarvis_lovelace_resource(item):
                if not matched:
                    updated = dict(item)
                    updated["id"] = item.get("id") or LOVELACE_RESOURCE_ID
                    updated["type"] = LOVELACE_RESOURCE_TYPE
                    updated["url"] = url
                    updated_items.append(updated)
                    matched = True
                continue
            updated_items.append(item)

        if not matched:
            updated_items.append(new_item)

        resources["items"] = updated_items
        await self.resource_store.async_save(resources)

    async def _async_update_lovelace_resource_collection(self, url: str) -> bool:
        """Update HA's in-memory Lovelace resource collection when available."""
        collection = self._find_lovelace_resource_collection()
        if collection is None:
            return False

        try:
            items = await self._async_collection_items(collection)
        except Exception as err:  # noqa: BLE001 - HA internals vary between versions
            _LOGGER.debug("Could not read Lovelace resource collection: %s", err)
            return False

        matched_items = [item for item in items if self._is_jarvis_lovelace_resource(item)]

        if matched_items:
            primary = matched_items[0]
            primary_id = primary.get("id")
            if primary_id is None:
                return False
            if not await self._async_update_collection_item(collection, str(primary_id), url):
                return False
            for duplicate in matched_items[1:]:
                duplicate_id = duplicate.get("id")
                if duplicate_id is None:
                    continue
                await self._async_delete_collection_item(collection, str(duplicate_id))
            return True

        return await self._async_create_collection_item(collection, url)

    def _find_lovelace_resource_collection(self) -> Any | None:
        lovelace_data = self.hass.data.get("lovelace") if hasattr(self.hass, "data") else None
        if lovelace_data is None:
            return None

        # Current Home Assistant stores a LovelaceData dataclass at
        # hass.data["lovelace"] and exposes the live resources as its
        # .resources attribute. Older/custom builds may still use a dict-like
        # shape, so support both. The previous dict-only lookup never found the
        # live collection on modern HA, which left only the .storage fallback and
        # made the resource/cache-buster appear unchanged until restart.
        candidates: list[Any] = []
        direct_resources = getattr(lovelace_data, "resources", None)
        if direct_resources is not None:
            candidates.append(direct_resources)
        if isinstance(lovelace_data, dict):
            candidates.extend(
                value for key, value in lovelace_data.items() if "resource" in str(key).lower()
            )

        for value in candidates:
            if all(hasattr(value, attr) for attr in ("async_get_info", "async_create_item", "async_update_item")):
                return value
        return None

    async def _async_collection_items(self, collection: Any) -> list[dict[str, Any]]:
        """Return live Lovelace resource items from a HA collection."""
        # ResourceStorageCollection.async_get_info() ensures the collection is loaded,
        # but it only returns a count (e.g. {"resources": 2}), not the item list.
        info = await collection.async_get_info()
        async_items = getattr(collection, "async_items", None)
        if async_items is not None:
            items = async_items()
            if isinstance(items, list):
                return [item for item in items if isinstance(item, dict)]

        return self._extract_resource_items(info)

    def _extract_resource_items(self, info: Any) -> list[dict[str, Any]]:
        if isinstance(info, list):
            return [item for item in info if isinstance(item, dict)]
        if not isinstance(info, dict):
            return []
        for key in ("resources", "items"):
            value = info.get(key)
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    async def _async_update_collection_item(self, collection: Any, item_id: str, url: str) -> bool:
        for payload in self._resource_payloads(url):
            try:
                await collection.async_update_item(item_id, payload)
                return True
            except Exception as err:  # noqa: BLE001 - HA versions accept different payload names
                _LOGGER.debug("Could not update Lovelace resource with payload %s: %s", payload, err)
        return False

    async def _async_create_collection_item(self, collection: Any, url: str) -> bool:
        for payload in self._resource_payloads(url):
            try:
                await collection.async_create_item(payload)
                return True
            except Exception as err:  # noqa: BLE001 - HA versions accept different payload names
                _LOGGER.debug("Could not create Lovelace resource with payload %s: %s", payload, err)
        return False

    async def _async_delete_collection_item(self, collection: Any, item_id: str) -> None:
        delete = getattr(collection, "async_delete_item", None)
        if delete is None:
            return
        try:
            await delete(item_id)
        except Exception as err:  # noqa: BLE001 - duplicate cleanup is best effort
            _LOGGER.debug("Could not remove duplicate Lovelace resource %s: %s", item_id, err)

    async def _async_reload_lovelace_resources(self) -> None:
        services = getattr(self.hass, "services", None)
        if services is None or not hasattr(services, "async_call"):
            return
        try:
            await services.async_call("lovelace", "reload_resources", blocking=False)
        except Exception as err:  # noqa: BLE001 - service is not present in all HA versions
            _LOGGER.debug("Could not reload Lovelace resources after Jarvis update: %s", err)

    def _resource_payloads(self, url: str) -> tuple[dict[str, str], ...]:
        return (
            {"url": url, "type": LOVELACE_RESOURCE_TYPE},
            {"url": url, "res_type": LOVELACE_RESOURCE_TYPE},
        )

    def _is_jarvis_lovelace_resource(self, item: dict[str, Any]) -> bool:
        if item.get("id") == LOVELACE_RESOURCE_ID:
            return True
        item_url = str(item.get("url") or "")
        if not item_url:
            return False
        path = urlsplit(item_url).path
        return (
            path.startswith(LOVELACE_RESOURCE_BASE_URL)
            or path.startswith("/local/jarvis/jarvis-cards")
            or "jarvis-cards" in path
        )

    async def async_current_file_sha256(self) -> str | None:
        return await self.hass.async_add_executor_job(self._current_file_sha256)

    def _current_file_sha256(self) -> str | None:
        path = Path(self.target_path)
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def _list_backups(self) -> list[dict[str, str | int | None]]:
        backup_dir = Path(self.backup_dir)
        if not backup_dir.exists():
            return []
        backups: list[dict[str, str | int | None]] = []
        for path in backup_dir.glob("jarvis-cards-*.js"):
            if not path.is_file():
                continue
            stat = path.stat()
            backups.append(
                {
                    "file_name": path.name,
                    "path": str(path),
                    "version": self._backup_version(path),
                    "size": stat.st_size,
                    "created_at": datetime.utcfromtimestamp(stat.st_mtime).replace(microsecond=0).isoformat() + "Z",
                }
            )
        backups.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return backups

    def _backup_version(self, path: Path) -> str | None:
        match = _BACKUP_RE.match(path.name)
        if not match:
            return None
        return match.group("version")

    def _resource_url(self, version: str | None) -> str:
        cache_key = version or datetime.utcnow().strftime("%Y%m%d%H%M%S")
        return f"{LOVELACE_RESOURCE_BASE_URL}?v={quote(str(cache_key), safe='.-_')}"

    def _cache_hint(self, resource_url: str) -> str:
        return (
            f"Lovelace Resource automatisch gesetzt: {resource_url}. "
            "Falls noch eine alte Karte sichtbar ist: Dashboard neu öffnen, Browser/App hart neu laden "
            "oder den Browser-Cache leeren."
        )

    def _create_cache_notification(self, title: str, result: str, resource_url: str) -> None:
        persistent_notification.async_create(
            self.hass,
            f"{result}\n\nResource: {resource_url}\n\n"
            "Hinweis: Wenn der Browser noch eine alte Jarvis Cards Version zeigt, bitte Dashboard neu öffnen, "
            "Browser/App hart neu laden oder den Cache leeren.",
            title=title,
            notification_id=f"{DOMAIN}_cache_hint",
        )
