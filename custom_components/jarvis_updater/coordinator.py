from __future__ import annotations

import hashlib
import logging
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import JarvisAuthError, JarvisManifest, JarvisUpdateClient, JarvisUpdaterError
from .const import (
    ATTR_INSTALLED_SHA256,
    BACKUP_DIR,
    CONF_LICENSE_KEY,
    DOMAIN,
    STORAGE_KEY,
    STORAGE_VERSION,
    TARGET_DIR,
    TARGET_FILE,
)

_LOGGER = logging.getLogger(__name__)


class JarvisUpdaterCoordinator(DataUpdateCoordinator[JarvisManifest]):
    """Fetch manifest and install Jarvis card releases."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        super().__init__(hass, _LOGGER, name=DOMAIN)
        self.entry = entry
        self.client = JarvisUpdateClient(async_get_clientsession(hass), entry.data)
        self.store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, f"{STORAGE_KEY}_{entry.entry_id}")
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
    def target_path(self) -> str:
        return self.hass.config.path(TARGET_DIR, TARGET_FILE)

    @property
    def backup_dir(self) -> str:
        return self.hass.config.path(BACKUP_DIR)

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
        self.storage.update(
            {
                "installed_version": manifest.latest_version,
                ATTR_INSTALLED_SHA256: digest,
                "installed_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
                "target_path": self.target_path,
                "last_backup_path": str(backup_path) if backup_path else None,
                "last_manifest": asdict(manifest),
            }
        )
        await self.store.async_save(self.storage)
        self.last_install_result = f"Jarvis Cards {manifest.latest_version} installiert"
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

    async def async_current_file_sha256(self) -> str | None:
        return await self.hass.async_add_executor_job(self._current_file_sha256)

    def _current_file_sha256(self) -> str | None:
        path = Path(self.target_path)
        if not path.exists():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()
