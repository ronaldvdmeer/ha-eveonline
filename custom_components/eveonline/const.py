"""Constants for the Eve Online integration."""

from typing import Final

DOMAIN: Final = "eveonline"
DEFAULT_SCAN_INTERVAL: Final = 60  # seconds

# Eve SSO OAuth2
SSO_AUTHORIZE_URL: Final = "https://login.eveonline.com/v2/oauth/authorize"
SSO_TOKEN_URL: Final = "https://login.eveonline.com/v2/oauth/token"

# Scopes for authenticated endpoints
SCOPES: Final[list[str]] = [
    "esi-location.read_online.v1",
    "esi-wallet.read_character_wallet.v1",
    "esi-skills.read_skillqueue.v1",
    "esi-location.read_location.v1",
    "esi-location.read_ship_type.v1",
]
