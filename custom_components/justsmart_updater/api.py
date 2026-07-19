from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiohttp import ClientError, ClientResponseError, ClientSession

from .const import CONF_LICENSE_KEY, CONF_UPDATE_URL


class JustSmartUpdaterError(Exception):
    """Base error for JustSmart updater."""


class JustSmartAuthError(JustSmartUpdaterError):
    """License/authentication failed."""


class JustSmartConnectionError(JustSmartUpdaterError):
    """Update server could not be reached."""


@dataclass(slots=True)
class JustSmartLicenseInfo:
    """License metadata returned by the update server."""

    customer: str | None
    status: str | None
    expires_at: str | None
    product: str | None
    raw: dict[str, Any]

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "JustSmartLicenseInfo":
        return cls(
            customer=_optional_str(data.get("customer") or data.get("customer_name")),
            status=_optional_str(data.get("status") or data.get("state")),
            expires_at=_optional_str(data.get("expires_at") or data.get("valid_until")),
            product=_optional_str(data.get("product")),
            raw=data,
        )


@dataclass(slots=True)
class JustSmartManifest:
    product: str
    channel: str
    latest_version: str
    file_name: str
    download_url: str
    sha256: str
    size: int | None
    released_at: str | None
    min_ha_version: str | None
    changelog: list[str]
    license: JustSmartLicenseInfo
    raw: dict[str, Any]

    @property
    def license_customer(self) -> str | None:
        """Backward-compatible shortcut for existing entity attributes."""
        return self.license.customer

    @classmethod
    def from_json(cls, data: dict[str, Any]) -> "JustSmartManifest":
        license_data = data.get("license") or {}
        changelog = data.get("changelog") or []
        if not isinstance(changelog, list):
            changelog = [str(changelog)]
        return cls(
            product=str(data.get("product") or "justsmart-cards"),
            channel=str(data.get("channel") or "stable"),
            latest_version=str(data["latest_version"]),
            file_name=str(data["file_name"]),
            download_url=str(data["download_url"]),
            sha256=str(data["sha256"]),
            size=int(data["size"]) if data.get("size") is not None else None,
            released_at=_optional_str(data.get("released_at")),
            min_ha_version=_optional_str(data.get("min_ha_version")),
            changelog=[str(item) for item in changelog],
            license=JustSmartLicenseInfo.from_json(license_data),
            raw=data,
        )


class JustSmartUpdateClient:
    """Small async client for the JustSmart Updates API."""

    def __init__(self, session: ClientSession, config: dict[str, Any]) -> None:
        self._session = session
        self._license_key = str(config[CONF_LICENSE_KEY])
        self._base_url = str(config[CONF_UPDATE_URL]).rstrip("/")

    @property
    def headers(self) -> dict[str, str]:
        return {"X-JustSmart-License": self._license_key}

    async def async_get_manifest(self) -> JustSmartManifest:
        url = f"{self._base_url}/api/manifest"
        try:
            async with self._session.get(url, headers=self.headers, timeout=30) as response:
                if response.status in (401, 403):
                    detail = await _response_detail(response)
                    raise JustSmartAuthError(detail)
                response.raise_for_status()
                data = await response.json()
        except JustSmartAuthError:
            raise
        except (ClientResponseError, ClientError, TimeoutError) as err:
            raise JustSmartConnectionError(str(err)) from err
        except Exception as err:
            raise JustSmartUpdaterError(str(err)) from err
        try:
            return JustSmartManifest.from_json(data)
        except Exception as err:
            raise JustSmartUpdaterError(f"Ungültiges Manifest: {err}") from err

    async def async_download(self, manifest: JustSmartManifest) -> bytes:
        try:
            async with self._session.get(manifest.download_url, headers=self.headers, timeout=120) as response:
                if response.status in (401, 403):
                    detail = await _response_detail(response)
                    raise JustSmartAuthError(detail)
                response.raise_for_status()
                return await response.read()
        except JustSmartAuthError:
            raise
        except (ClientResponseError, ClientError, TimeoutError) as err:
            raise JustSmartConnectionError(str(err)) from err
        except Exception as err:
            raise JustSmartUpdaterError(str(err)) from err


async def _response_detail(response) -> str:
    try:
        data = await response.json()
        return str(data.get("detail") or data)
    except Exception:
        return await response.text()


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    value = str(value)
    return value or None
