from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JarvisUpdaterCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: JarvisUpdaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            JarvisInstalledVersionSensor(coordinator, entry),
            JarvisAvailableVersionSensor(coordinator, entry),
        ]
    )


class _JarvisVersionSensor(CoordinatorEntity[JarvisUpdaterCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Jarvis Cards Updater",
            "manufacturer": "JustSmart",
        }

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()


class JarvisInstalledVersionSensor(_JarvisVersionSensor):
    _attr_name = "Installierte Version"
    _attr_icon = "mdi:package-check"

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "installed_version")

    @property
    def native_value(self) -> str:
        return self.coordinator.installed_version or "nicht installiert"


class JarvisAvailableVersionSensor(_JarvisVersionSensor):
    _attr_name = "Verfügbare Version"
    _attr_icon = "mdi:package-up"

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry) -> None:
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
            "license_customer": manifest.license_customer,
            "changelog": "\n".join(manifest.changelog),
        }
