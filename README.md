# Eve Online for Home Assistant

Custom Home Assistant integration for [Eve Online](https://www.eveonline.com/) using the ESI API.

## Features (MVP)

- **Server Status** — Shows whether the Tranquility server is online
- **Players Online** — Current player count as a measurement sensor
- **Server Version** — Current build version (disabled by default)

All data is refreshed every 60 seconds using public ESI endpoints (no API key required).

## Installation

### HACS (recommended)

1. Open HACS in Home Assistant
2. Go to **Integrations** → **⋮** → **Custom repositories**
3. Add `https://github.com/ronaldvdmeer/ha-eveonline` as **Integration**
4. Search for "Eve Online" and install
5. Restart Home Assistant
6. Go to **Settings** → **Devices & Services** → **Add Integration** → **Eve Online**

### Manual

1. Copy `custom_components/eveonline/` to your Home Assistant `custom_components/` directory
2. Restart Home Assistant
3. Go to **Settings** → **Devices & Services** → **Add Integration** → **Eve Online**

## Requirements

- Home Assistant 2024.12.0+
- [python-eveonline](https://github.com/ronaldvdmeer/python-eveonline) (installed automatically)

## Roadmap

- [ ] OAuth2 authentication for character-specific data
- [ ] Wallet balance sensor
- [ ] Character online status (binary sensor)
- [ ] Character location sensor
- [ ] Skill queue sensor
- [ ] Ship type sensor

## License

MIT
