DOMAIN = "justsmart_updater"

CONF_LICENSE_KEY = "license_key"
CONF_UPDATE_URL = "update_url"
CONF_CHANNEL = "channel"

DEFAULT_UPDATE_URL = "https://updates.justsmart.at"
DEFAULT_CHANNEL = "stable"

PLATFORMS = ["update", "button", "sensor", "select"]

STORAGE_VERSION = 1
STORAGE_KEY = "justsmart_updater_data"
LOVELACE_RESOURCES_STORAGE_KEY = "lovelace_resources"

# Home Assistant exposes /config/www as /www in the File Editor/Samba UI and
# as /local in Lovelace. Internally integrations must write relative to
# hass.config.path(), otherwise an absolute /www directory is created inside
# the HA container and the file is not served by Home Assistant.
TARGET_DIR = "www/justsmart"
TARGET_FILE = "justsmart-cards.js"
BACKUP_DIR = "www/justsmart/backups"
LOVELACE_RESOURCE_BASE_URL = "/local/justsmart/justsmart-cards.js"
LOVELACE_RESOURCE_TYPE = "module"
LOVELACE_RESOURCE_ID = "justsmart_cards_updater"

ATTR_INSTALLED_SHA256 = "installed_sha256"
ATTR_AVAILABLE_SHA256 = "available_sha256"
ATTR_DOWNLOAD_URL = "download_url"
ATTR_LICENSE_CUSTOMER = "license_customer"
ATTR_LICENSE_STATUS = "license_status"
ATTR_LICENSE_EXPIRES_AT = "license_expires_at"
ATTR_RELEASED_AT = "released_at"
ATTR_RESOURCE_URL = "lovelace_resource_url"
ATTR_CACHE_HINT = "browser_cache_hint"
