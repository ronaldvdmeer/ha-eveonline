"""Config flow for Eve Online integration."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN


class EveOnlineConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Eve Online."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step.

        MVP: No configuration needed for public endpoints.
        Just create an entry with a fixed unique ID.
        """
        # Only allow one instance
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        if user_input is not None:
            return self.async_create_entry(
                title="Eve Online",
                data={},
            )

        return self.async_show_form(step_id="user")
