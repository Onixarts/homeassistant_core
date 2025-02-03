import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .bridge import HapcanBridge
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# Definiowanie schematu konfiguracji
CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.Schema(
            {
                vol.Required("host"): cv.string,
                vol.Required("port"): cv.port,
                vol.Optional("log_frames", default=False): cv.boolean,
            }
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: ConfigType):
    """Set up the hapcan component."""
    hapcan_config = config[DOMAIN]
    _LOGGER.info("Starting hapcan integration with config: %s", hapcan_config)

    # Przechowywanie konfiguracji w słowniku danych
    hass.data[DOMAIN] = hapcan_config

    bridge = HapcanBridge(
        host=hapcan_config["host"],
        port=hapcan_config["port"],
        log_frames=hapcan_config["log_frames"],
    )
    await bridge.connect()

    hass.data[DOMAIN] = bridge

    frame = bytearray(
        [
            0xAA,
            0x30,
            0x30,
            0x03,
            0x02,
            0xFF,
            0xFF,
            0x07,
            0x40,
            0x04,
            0xFF,
            0xFF,
            0xFF,
            0xAB,
            0xA5,
        ]
    )
    bridge.send({"payload": frame})
    bridge.send({"payload": frame})

    # Dodatkowe kroki inicjalizacji można dodać tutaj

    return True


async def async_setup_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Set up hapcan from a config entry."""
    _LOGGER.info("Setting up hapcan integration from entry")

    bridge = HapcanBridge(
        host=entry.data["host"],
        port=entry.data["port"],
        log_frames=entry.options.get("log_frames", False),
    )
    await bridge.connect()

    hass.data[DOMAIN] = bridge

    return True


async def async_unload_entry(hass: HomeAssistant, entry: config_entries.ConfigEntry):
    """Unload a config entry."""
    _LOGGER.info("Unloading hapcan integration entry")
    bridge = hass.data.pop(DOMAIN)
    bridge.close()
    return True
