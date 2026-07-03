from __future__ import annotations

from homeassistant.components.button import ButtonEntity
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
            JarvisInstallButton(coordinator, entry),
            JarvisCheckButton(coordinator, entry),
        ]
    )


class _JarvisButton(CoordinatorEntity[JarvisUpdaterCoordinator], ButtonEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Jarvis Cards Updater",
            "manufacturer": "JustSmart",
        }


class JarvisInstallButton(_JarvisButton):
    _attr_name = "Update installieren"

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "install_update_button")

    async def async_press(self) -> None:
        await self.coordinator.async_install_update()


class JarvisCheckButton(_JarvisButton):
    _attr_name = "Update prüfen"

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "check_update_button")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
