from __future__ import annotations

import asyncio
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def _install_homeassistant_stubs() -> None:
    modules = {
        "aiohttp": types.ModuleType("aiohttp"),
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.persistent_notification": types.ModuleType(
            "homeassistant.components.persistent_notification"
        ),
        "homeassistant.config_entries": types.ModuleType("homeassistant.config_entries"),
        "homeassistant.core": types.ModuleType("homeassistant.core"),
        "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.aiohttp_client": types.ModuleType("homeassistant.helpers.aiohttp_client"),
        "homeassistant.helpers.storage": types.ModuleType("homeassistant.helpers.storage"),
        "homeassistant.helpers.update_coordinator": types.ModuleType(
            "homeassistant.helpers.update_coordinator"
        ),
    }
    for name, module in modules.items():
        sys.modules.setdefault(name, module)

    setattr(sys.modules["aiohttp"], "ClientError", Exception)
    setattr(sys.modules["aiohttp"], "ClientResponseError", Exception)
    setattr(sys.modules["aiohttp"], "ClientSession", object)
    setattr(
        sys.modules["homeassistant.components"],
        "persistent_notification",
        sys.modules["homeassistant.components.persistent_notification"],
    )
    setattr(sys.modules["homeassistant.components.persistent_notification"], "async_create", lambda *a, **k: None)
    setattr(sys.modules["homeassistant.config_entries"], "ConfigEntry", object)
    setattr(sys.modules["homeassistant.core"], "HomeAssistant", object)
    setattr(sys.modules["homeassistant.helpers.aiohttp_client"], "async_get_clientsession", lambda hass: None)

    class Store:  # minimal constructor only; tests bypass real storage
        def __init__(self, *args, **kwargs):
            pass

    class DataUpdateCoordinator:
        def __init__(self, *args, **kwargs):
            pass

        def __class_getitem__(cls, item):
            return cls

    class UpdateFailed(Exception):
        pass

    setattr(sys.modules["homeassistant.helpers.storage"], "Store", Store)
    uc = sys.modules["homeassistant.helpers.update_coordinator"]
    setattr(uc, "DataUpdateCoordinator", DataUpdateCoordinator)
    setattr(uc, "UpdateFailed", UpdateFailed)


_install_homeassistant_stubs()

from custom_components.justsmart_updater.coordinator import JustSmartUpdaterCoordinator  # noqa: E402


class FakeResourceCollection:
    def __init__(self, items):
        self.items = list(items)
        self.updated = []
        self.created = []
        self.deleted = []

    async def async_get_info(self):
        return {"resources": len(self.items)}

    def async_items(self):
        return self.items

    async def async_update_item(self, item_id, payload):
        if "res_type" not in payload:
            raise ValueError("Home Assistant websocket schema requires res_type")
        self.updated.append((item_id, payload))
        for item in self.items:
            if item.get("id") == item_id:
                item.update({"url": payload["url"], "type": payload["res_type"]})
                return item
        raise KeyError(item_id)

    async def async_create_item(self, payload):
        if "res_type" not in payload:
            raise ValueError("Home Assistant websocket schema requires res_type")
        item = {"id": "new", "url": payload["url"], "type": payload["res_type"]}
        self.created.append(payload)
        self.items.append(item)
        return item

    async def async_delete_item(self, item_id):
        self.deleted.append(item_id)
        self.items = [item for item in self.items if item.get("id") != item_id]


def _coordinator_with_collection(collection):
    coord = JustSmartUpdaterCoordinator.__new__(JustSmartUpdaterCoordinator)
    coord.hass = types.SimpleNamespace(data={"lovelace": types.SimpleNamespace(resources=collection)})
    return coord


def test_finds_modern_lovelace_dataclass_resource_collection():
    collection = FakeResourceCollection([])
    coord = _coordinator_with_collection(collection)

    assert coord._find_lovelace_resource_collection() is collection


def test_updates_live_collection_items_not_resource_count_only():
    collection = FakeResourceCollection(
        [
            {"id": "justsmart-old", "url": "/local/justsmart/justsmart-cards.js?v=1.0.1", "type": "module"},
            {"id": "duplicate", "url": "https://cdn.example/justsmart-cards.js", "type": "module"},
            {"id": "other", "url": "/local/other-card.js", "type": "module"},
        ]
    )
    coord = _coordinator_with_collection(collection)

    ok = asyncio.run(coord._async_update_lovelace_resource_collection("/local/justsmart/justsmart-cards.js?v=1.0.25"))

    assert ok is True
    assert collection.updated == [("justsmart-old", {"url": "/local/justsmart/justsmart-cards.js?v=1.0.25", "res_type": "module"})]
    assert collection.deleted == ["duplicate"]
    assert [item["id"] for item in collection.items] == ["justsmart-old", "other"]
    assert collection.items[0]["url"] == "/local/justsmart/justsmart-cards.js?v=1.0.25"


def test_creates_resource_when_no_justsmart_entry_exists():
    collection = FakeResourceCollection([{"id": "other", "url": "/local/other-card.js", "type": "module"}])
    coord = _coordinator_with_collection(collection)

    ok = asyncio.run(coord._async_update_lovelace_resource_collection("/local/justsmart/justsmart-cards.js?v=1.0.25"))

    assert ok is True
    assert collection.created == [{"url": "/local/justsmart/justsmart-cards.js?v=1.0.25", "res_type": "module"}]
