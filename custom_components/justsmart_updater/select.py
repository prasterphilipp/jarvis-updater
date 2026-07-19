from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import JustSmartUpdaterCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: JustSmartUpdaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JustSmartRollbackSelect(coordinator, entry)])


class JustSmartRollbackSelect(CoordinatorEntity[JustSmartUpdaterCoordinator], SelectEntity):
    """Select a local backup that should be restored by the rollback button."""

    _attr_has_entity_name = True
    _attr_name = "Rollback-Version"
    _attr_icon = "mdi:history"

    def __init__(self, coordinator: JustSmartUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rollback_version"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "JustSmart Cards Updater",
            "manufacturer": "JustSmart",
        }

    @property
    def available(self) -> bool:
        return bool(self.coordinator.rollback_options)

    @property
    def options(self) -> list[str]:
        return self.coordinator.rollback_options

    @property
    def current_option(self) -> str | None:
        return self.coordinator.selected_backup

    @property
    def extra_state_attributes(self) -> dict[str, list[dict]]:
        return {"backups": self.coordinator.backups}

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_select_backup(option)
