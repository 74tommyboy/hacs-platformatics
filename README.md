# Platformatics Home Assistant Integration

A custom Home Assistant integration that connects to a **Platformatics PoE lighting controller** and exposes your lighting zones as `light` entities and environmental sensor readings as `sensor` entities — all installable via HACS.

---

## Requirements

- Home Assistant 2024.1 or later
- [HACS](https://hacs.xyz/) installed
- A Platformatics controller accessible on your local network (default port 8080)

---

## Installation

1. In Home Assistant, open **HACS → Integrations**
2. Click **⋮ → Custom repositories**
3. Add `https://github.com/TommyboyDesigns/hacs-platformatics` with category **Integration**
4. Click **Install** on "Platformatics"
5. Restart Home Assistant
6. Go to **Settings → Integrations → Add Integration** and search for **Platformatics**
7. Enter your controller's IP address, username (`admin` by default), and password

---

## Entities

### Light entities

One `light` entity is created per zone. Each entity supports:
- On / Off
- Brightness (0–100%, mapped to Home Assistant's 0–255 scale)

### Sensor entities

For each device that reports environmental data, the following `sensor` entities are created (when the device has a non-null reading):

| Sensor | Unit | Device Class |
|---|---|---|
| Temperature | °C | `temperature` |
| Humidity | % | `humidity` |
| PM2.5 | µg/m³ | `pm25` |
| PM10 | µg/m³ | `pm10` |
| VOC Index | — | `volatile_organic_compounds_parts` |
| Daylight Level | % | — |

---

## Limitations

- **Polling only** — state updates every 30 seconds; no push/webhook support in v1
- **Read-only sensors** — sensor entities report values only; no write-back
- **No scene/clip/playlist control** — zone on/off and brightness only in v1
- SSL certificate verification is disabled for controller connections (self-signed cert)
