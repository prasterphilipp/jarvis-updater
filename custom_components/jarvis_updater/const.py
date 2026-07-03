DOMAIN = "jarvis_updater"

CONF_LICENSE_KEY = "license_key"
CONF_UPDATE_URL = "update_url"
CONF_CHANNEL = "channel"

DEFAULT_UPDATE_URL = "https://updates.justsmart.at"
DEFAULT_CHANNEL = "stable"

PLATFORMS = ["update", "button", "sensor"]

STORAGE_VERSION = 1
STORAGE_KEY = "jarvis_updater_data"

# Home Assistant exposes /config/www as /www in the File Editor/Samba UI and
# as /local in Lovelace. Internally integrations must write relative to
# hass.config.path(), otherwise an absolute /www directory is created inside
# the HA container and the file is not served by Home Assistant.
TARGET_DIR = "www/jarvis"
TARGET_FILE = "jarvis-cards.js"
BACKUP_DIR = "www/jarvis/backups"

ATTR_INSTALLED_SHA256 = "installed_sha256"
ATTR_AVAILABLE_SHA256 = "available_sha256"
ATTR_DOWNLOAD_URL = "download_url"
ATTR_LICENSE_CUSTOMER = "license_customer"
ATTR_RELEASED_AT = "released_at"
