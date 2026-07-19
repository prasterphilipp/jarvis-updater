from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JustSmartUpdaterCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: JustSmartUpdaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JustSmartInstalledVersionSensor(coordinator, entry),
            JustSmartAvailableVersionSensor(coordinator, entry),
            JustSmartCustomerSensor(coordinator, entry),
            JustSmartLicenseStatusSensor(coordinator, entry),
            JustSmartChangelogSensor(coordinator, entry),
            JustSmartCacheHintSensor(coordinator, entry),
        ]
    )


class _JustSmartSensor(CoordinatorEntity[JustSmartUpdaterCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "JustSmart Cards Updater",
            "manufacturer": "JustSmart",
        }

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()


class JustSmartInstalledVersionSensor(_JustSmartSensor):
    _attr_name = "Installierte Version"
    _attr_icon = "mdi:package-check"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "installed_version")

    @property
    def native_value(self) -> str:
        return self.coordinator.installed_version or "nicht installiert"

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        return {
            "sha256": self.coordinator.installed_sha256,
            "resource_url": self.coordinator.resource_url,
        }


class JustSmartAvailableVersionSensor(_JustSmartSensor):
    _attr_name = "Verfügbare Version"
    _attr_icon = "mdi:package-up"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "available_version")

    @property
    def native_value(self) -> str | None:
        return self.coordinator.data.latest_version if self.coordinator.data else None

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        manifest = self.coordinator.data
        if not manifest:
            return {}
        return {
            "file_name": manifest.file_name,
            "sha256": manifest.sha256,
            "size": manifest.size,
            "released_at": manifest.released_at,
            "license_customer": manifest.license.customer,
            "license_status": manifest.license.status,
            "license_expires_at": manifest.license.expires_at,
            "changelog": "\n".join(manifest.changelog),
        }


class JustSmartCustomerSensor(_JustSmartSensor):
    _attr_name = "Kunde"
    _attr_icon = "mdi:account-badge"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "customer")

    @property
    def native_value(self) -> str:
        if self.coordinator.data and self.coordinator.data.license.customer:
            return self.coordinator.data.license.customer
        return "unbekannt"


class JustSmartLicenseStatusSensor(_JustSmartSensor):
    _attr_name = "Lizenzstatus"
    _attr_icon = "mdi:license"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "license_status")

    @property
    def native_value(self) -> str:
        if self.coordinator.data and self.coordinator.data.license.status:
            return self.coordinator.data.license.status
        if self.coordinator.last_update_success and self.coordinator.data:
            return "aktiv"
        return "unbekannt"

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        license_info = self.coordinator.data.license if self.coordinator.data else None
        return {
            "customer": license_info.customer if license_info else None,
            "expires_at": license_info.expires_at if license_info else None,
            "product": license_info.product if license_info else None,
        }


class JustSmartChangelogSensor(_JustSmartSensor):
    _attr_name = "Changelog"
    _attr_icon = "mdi:text-box-outline"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "changelog")

    @property
    def native_value(self) -> str:
        if not self.coordinator.data:
            return "nicht verfügbar"
        return self.coordinator.data.latest_version

    @property
    def extra_state_attributes(self) -> dict[str, str | list[str] | None]:
        manifest = self.coordinator.data
        if not manifest:
            return {}
        return {
            "released_at": manifest.released_at,
            "items": manifest.changelog,
            "text": "\n".join(f"- {item}" for item in manifest.changelog),
        }


class JustSmartCacheHintSensor(_JustSmartSensor):
    _attr_name = "Browser-Cache-Hinweis"
    _attr_icon = "mdi:cached"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "cache_hint")

    @property
    def native_value(self) -> str:
        return "Resource gesetzt" if self.coordinator.resource_url else "nicht gesetzt"

    @property
    def extra_state_attributes(self) -> dict[str, str]:
        return {
            "resource_url": self.coordinator.resource_url,
            "hint": self.coordinator.cache_hint,
        }
