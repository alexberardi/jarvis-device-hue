# Philips Hue RGB Lights

Jarvis device protocol and voice command for controlling Philips Hue smart lights via the local Bridge API.

## Features

- **Device Discovery** — Automatically finds all lights connected to your Hue Bridge
- **On/Off Control** — Turn lights on and off by name or all at once
- **RGB Color** — Set any color by name (24 built-in colors) or RGB values
- **Brightness** — Dim or brighten lights (0–100%)
- **Color Temperature** — Warm (2000K) to cool (6500K) white
- **Fuzzy Matching** — Say "bedroom" to match "Bedroom Lamp" automatically
- **Multi-Light** — Control all lights or target specific ones by name

## Components

| Type | Name | Description |
|------|------|-------------|
| Device Protocol | `hue` | Bridge API integration for discovery, control, and state |
| Voice Command | `control_hue_lights` | Natural language light control |

## Setup

### 1. Find Your Bridge IP

Open the **Hue** app on your phone:
**Settings** → **My Hue system** → tap your bridge → note the IP address.

Or visit `https://discovery.meethue.com` in your browser.

### 2. Create an API Username

1. Press the **link button** on top of your Hue Bridge
2. Within 30 seconds, run:

```bash
curl -X POST http://<BRIDGE_IP>/api \
  -H "Content-Type: application/json" \
  -d '{"devicetype": "jarvis#node"}'
```

3. Copy the `username` value from the response

### 3. Configure Secrets

In the Jarvis mobile app, go to **Settings** and enter:

| Secret | Description |
|--------|-------------|
| **Bridge IP** | Your Hue Bridge local IP (e.g., `192.168.1.42`) |
| **API Username** | The username from step 2 |

## Voice Commands

| Say | What Happens |
|-----|-------------|
| "Turn on the living room lights" | Turns on lights matching "living room" |
| "Turn off all the lights" | Turns off every light on the bridge |
| "Set the bedroom to blue" | Changes bedroom lights to blue |
| "Make the kitchen red" | Changes kitchen lights to red |
| "Dim the hallway to 30 percent" | Sets hallway lights to 30% brightness |
| "Set the lights to warm white" | Sets color temperature to 2700K |
| "Set the desk lamp to cool white" | Sets color temperature to 6500K |

### Supported Colors

red, green, blue, yellow, orange, purple, violet, pink, cyan, teal, magenta, white, warm white, cool white, lavender, coral, turquoise, gold, lime, indigo, salmon, mint, peach, sky blue

You can also use RGB values: "set the lights to 255,100,50"

## Supported Actions

| Action | Parameters | Description |
|--------|-----------|-------------|
| `turn_on` | `light_name` (optional) | Turn light(s) on |
| `turn_off` | `light_name` (optional) | Turn light(s) off |
| `set_brightness` | `brightness` (0–100) | Set brightness percentage |
| `set_color` | `color` (name or r,g,b) | Set RGB color |
| `set_color_temp` | `color_temp` (Kelvin) | Set color temperature |

## Requirements

- Philips Hue Bridge (v2 recommended)
- Bridge and Jarvis node on the same local network
- Python package: `httpx`

## License

MIT
