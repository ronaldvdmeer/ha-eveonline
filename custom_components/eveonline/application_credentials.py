"""Application credentials for Eve Online."""

from homeassistant.components.application_credentials import AuthorizationServer
from homeassistant.core import HomeAssistant

from .const import SSO_AUTHORIZE_URL, SSO_TOKEN_URL


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the Eve Online authorization server."""
    return AuthorizationServer(
        authorize_url=SSO_AUTHORIZE_URL,
        token_url=SSO_TOKEN_URL,
    )
