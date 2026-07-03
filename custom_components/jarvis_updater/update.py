from __future__ import annotations

from homeassistant.components.update import UpdateEntity, UpdateEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ATTR_AVAILABLE_SHA256,
    ATTR_DOWNLOAD_URL,
    ATTR_INSTALLED_SHA256,
    ATTR_LICENSE_CUSTOMER,
    ATTR_RELEASED_AT,
    DOMAIN,
)
from .coordinator import JarvisUpdaterCoordinator


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator: JarvisUpdaterCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([JarvisCardsUpdateEntity(coordinator, entry)])


class JarvisCardsUpdateEntity(CoordinatorEntity[JarvisUpdaterCoordinator], UpdateEntity):
    """Update entity for Jarvis Cards."""

    _attr_has_entity_name = True
    _attr_name = "Cards"
    _attr_supported_features = UpdateEntityFeature.INSTALL

    def __init__(self, coordinator: JarvisUpdaterCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_jarvis_cards_update"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": "Jarvis Cards Updater",
            "manufacturer": "JustSmart",
        }

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and self.coordinator.data is not None

    @property
    def installed_version(self) -> str | None:
        return self.coordinator.installed_version or "not_installed"

    @property
    def latest_version(self) -> str | None:
        return self.coordinator.data.latest_version if self.coordinator.data else None

    @property
    def release_summary(self) -> str | None:
        if not self.coordinator.data or not self.coordinator.data.changelog:
            return None
        return "\n".join(f"- {item}" for item in self.coordinator.data.changelog)

    @property
    def extra_state_attributes(self) -> dict[str, str | int | None]:
        manifest = self.coordinator.data
        attrs: dict[str, str | int | None] = {
            ATTR_INSTALLED_SHA256: self.coordinator.installed_sha256,
            "target_path": self.coordinator.target_path,
            "last_install_result": self.coordinator.last_install_result,
        }
        if manifest:
            attrs.update(
                {
                    ATTR_AVAILABLE_SHA256: manifest.sha256,
                    ATTR_DOWNLOAD_URL: manifest.download_url,
                    ATTR_LICENSE_CUSTOMER: manifest.license_customer,
                    ATTR_RELEASED_AT: manifest.released_at,
                    "file_name": manifest.file_name,
                    "size": manifest.size,
                    "channel": manifest.channel,
                }
            )
        return attrs

    async def async_update(self) -> None:
        await self.coordinator.async_request_refresh()

    async def async_install(self, version: str | None = None, backup: bool = False, **kwargs) -> None:
        await self.coordinator.async_install_update()
