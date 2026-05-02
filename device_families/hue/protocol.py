"""Philips Hue smart light protocol adapter (LAN via bridge)."""

from __future__ import annotations

import re
from typing import Any, Literal

from jarvis_command_sdk import (
    IJarvisDeviceProtocol,
    IJarvisSecret,
    DiscoveredDevice,
    DeviceControlResult,
    IJarvisButton,
    JarvisSecret,
    JarvisStorage,
)

from hue_shared.color import rgb_to_xy, xy_to_rgb

try:
    from jarvis_log_client import JarvisLogger
except ImportError:
    import logging

    class JarvisLogger:
        def __init__(self, **kw: Any) -> None:
            self._log = logging.getLogger(kw.get("service", __name__))

        def info(self, msg: str, **kw: Any) -> None:
            self._log.info(msg)

        def warning(self, msg: str, **kw: Any) -> None:
            self._log.warning(msg)

        def error(self, msg: str, **kw: Any) -> None:
            self._log.error(msg)

        def debug(self, msg: str, **kw: Any) -> None:
            self._log.debug(msg)


logger = JarvisLogger(service="device.hue")

_storage = JarvisStorage("hue")


def _slugify(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


# Hue product archetypes → HA-style domains
_HUE_TYPE_MAP: dict[str, str] = {
    "sultan_bulb": "light",
    "flood_bulb": "light",
    "spot_bulb": "light",
    "candle_bulb": "light",
    "luster_bulb": "light",
    "pendant_round": "light",
    "pendant_long": "light",
    "ceiling_round": "light",
    "ceiling_square": "light",
    "floor_shade": "light",
    "floor_lantern": "light",
    "table_shade": "light",
    "table_wash": "light",
    "wall_shade": "light",
    "wall_lantern": "light",
    "wall_spot": "light",
    "plug": "switch",
    "hue_go": "light",
    "hue_lightstrip": "light",
    "hue_iris": "light",
    "hue_bloom": "light",
    "hue_play": "light",
    "hue_signe": "light",
    "hue_centris": "light",
    "bollard": "light",
    "classic_status": "light",
    "double_spot": "light",
    "recessed_ceiling": "light",
    "recessed_floor": "light",
}


class HueProtocol(IJarvisDeviceProtocol):
    """Philips Hue LAN protocol adapter via Hue Bridge API."""

    protocol_name: str = "hue"
    friendly_name: str = "Philips Hue"
    supported_domains: list[str] = ["light"]
    connection_type: Literal["lan", "cloud", "hybrid"] = "lan"
    description: str = "Control Philips Hue lights via local bridge"
    setup_guide: str = """## Setting Up Philips Hue

### Step 1: Find Your Bridge IP

Open the **Hue** app → **Settings** → **My Hue system** → tap your bridge.
The IP address is shown at the bottom (e.g., `192.168.1.42`).

Alternatively, visit https://discovery.meethue.com in your browser.

### Step 2: Create an API Username

1. **Press the link button** on top of your Hue Bridge
2. Within 30 seconds, run this command in a terminal:

```bash
curl -X POST http://<BRIDGE_IP>/api \\
  -H "Content-Type: application/json" \\
  -d '{"devicetype": "jarvis#node"}'
```

3. Copy the `username` value from the response

### Step 3: Enter Credentials

Paste your **Bridge IP** and **Username** into the fields below.

> Tip: Your bridge IP may change if your router assigns dynamic IPs.
> Consider setting a static IP or DHCP reservation for the bridge."""

    @property
    def required_secrets(self) -> list[IJarvisSecret]:
        return [
            JarvisSecret(
                "HUE_BRIDGE_IP",
                "Local IP address of your Philips Hue Bridge (e.g., 192.168.1.42)",
                "integration",
                "string",
                friendly_name="Bridge IP",
                is_sensitive=False,
                required=True,
            ),
            JarvisSecret(
                "HUE_USERNAME",
                "Hue Bridge API username (created via link button + POST /api)",
                "integration",
                "string",
                friendly_name="API Username",
                required=True,
            ),
        ]

    def _bridge_ip(self) -> str | None:
        return _storage.get_secret("HUE_BRIDGE_IP")

    def _username(self) -> str | None:
        return _storage.get_secret("HUE_USERNAME")

    @property
    def supported_actions(self) -> list[IJarvisButton]:
        return [
            IJarvisButton(
                button_text="Turn On",
                button_action="turn_on",
                button_type="primary",
                button_icon="lightbulb-on",
            ),
            IJarvisButton(
                button_text="Turn Off",
                button_action="turn_off",
                button_type="secondary",
                button_icon="lightbulb-off",
            ),
        ]

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    async def discover(self, timeout: float = 5.0) -> list[DiscoveredDevice]:
        bridge_ip: str | None = self._bridge_ip()
        username: str | None = self._username()
        if not bridge_ip or not username:
            logger.error("HUE_BRIDGE_IP and HUE_USERNAME must be configured")
            return []

        try:
            import httpx
        except ImportError:
            logger.error("httpx is not installed. Run: pip install httpx")
            return []

        devices: list[DiscoveredDevice] = []

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(
                    f"http://{bridge_ip}/api/{username}/lights",
                )
                if resp.status_code != 200:
                    logger.error(f"Hue bridge returned {resp.status_code}")
                    return []

                lights: dict[str, Any] = resp.json()

                # Check for API error (unauthorized, etc.)
                if isinstance(lights, list):
                    for item in lights:
                        if "error" in item:
                            logger.error(f"Hue API error: {item['error'].get('description', '')}")
                    return []

                for light_id, light_data in lights.items():
                    name: str = light_data.get("name", f"Hue Light {light_id}")
                    model_id: str = light_data.get("modelid", "")
                    product_name: str = light_data.get("productname", model_id)
                    light_type: str = light_data.get("type", "")
                    archetype: str = (
                        light_data.get("config", {})
                        .get("archetype", "")
                        .lower()
                    )

                    domain: str = _HUE_TYPE_MAP.get(archetype, "light")

                    # Determine capabilities from type string
                    capabilities: dict[str, bool] = {
                        "color": "color" in light_type.lower(),
                        "color_temp": "temperature" in light_type.lower()
                        or "color" in light_type.lower(),
                        "dimmable": True,
                    }

                    devices.append(
                        DiscoveredDevice(
                            entity_id=_slugify(name) or f"hue_light_{light_id}",
                            name=name,
                            domain=domain,
                            protocol=self.protocol_name,
                            model=product_name or model_id,
                            manufacturer="Philips",
                            local_ip=bridge_ip,
                            cloud_id=light_id,
                            extra={
                                "light_id": light_id,
                                "type": light_type,
                                "capabilities": capabilities,
                                "uniqueid": light_data.get("uniqueid", ""),
                            },
                        )
                    )

                logger.info(f"Hue discovery found {len(devices)} light(s)")

        except Exception as e:
            logger.error(f"Hue discovery failed: {e}")

        return devices

    # ------------------------------------------------------------------
    # Control
    # ------------------------------------------------------------------

    async def control(
        self,
        ip: str,
        action: str,
        data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> DeviceControlResult:
        bridge_ip: str | None = self._bridge_ip()
        username: str | None = self._username()
        entity_id: str = kwargs.get("entity_id", "")

        # Extract light_id from kwargs or cloud_id
        light_id: str = kwargs.get("light_id", "")
        if not light_id:
            cloud_id: str = kwargs.get("cloud_id", "")
            if cloud_id:
                light_id = cloud_id

        if not bridge_ip or not username:
            return DeviceControlResult(
                success=False, entity_id=entity_id, action=action,
                error="HUE_BRIDGE_IP and HUE_USERNAME not configured",
            )
        if not light_id:
            return DeviceControlResult(
                success=False, entity_id=entity_id, action=action,
                error="No light ID available",
            )

        try:
            import httpx
        except ImportError:
            return DeviceControlResult(
                success=False, entity_id=entity_id, action=action,
                error="httpx is not installed",
            )

        data = data or {}
        state_body: dict[str, Any] = {}

        if action == "turn_on":
            state_body = {"on": True}
        elif action == "turn_off":
            state_body = {"on": False}
        elif action == "toggle":
            current: dict[str, Any] | None = await self.get_state(
                ip, light_id=light_id, entity_id=entity_id,
            )
            is_on: bool = (current or {}).get("state") == "on"
            state_body = {"on": not is_on}
        elif action == "set_brightness":
            pct: int = int(data.get("brightness", 100))
            pct = max(0, min(100, pct))
            bri: int = max(1, int(pct / 100.0 * 254))
            state_body = {"on": True, "bri": bri}
        elif action == "set_color":
            if "rgb" in data:
                rgb = data["rgb"]
                r, g, b = int(rgb[0]), int(rgb[1]), int(rgb[2])
                xy: tuple[float, float] = rgb_to_xy(r, g, b)
                state_body = {"on": True, "xy": list(xy)}
            elif "color_temp" in data:
                kelvin: int = int(data["color_temp"])
                # Hue uses mirek (micro reciprocal degree): mirek = 1_000_000 / kelvin
                mirek: int = max(153, min(500, 1_000_000 // max(kelvin, 1)))
                state_body = {"on": True, "ct": mirek}
            elif "xy" in data:
                state_body = {"on": True, "xy": data["xy"]}
            else:
                return DeviceControlResult(
                    success=False, entity_id=entity_id, action=action,
                    error="set_color requires 'rgb', 'color_temp', or 'xy' param",
                )
        elif action == "set_color_temp":
            kelvin = int(data.get("color_temp", data.get("temperature", 4000)))
            mirek = max(153, min(500, 1_000_000 // max(kelvin, 1)))
            state_body = {"on": True, "ct": mirek}
        elif action == "alert":
            state_body = {"alert": data.get("alert_type", "select")}
        else:
            return DeviceControlResult(
                success=False, entity_id=entity_id, action=action,
                error=f"Unsupported action: {action}",
            )

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.put(
                    f"http://{bridge_ip}/api/{username}/lights/{light_id}/state",
                    json=state_body,
                )
                if resp.status_code == 200:
                    result_list: list[dict[str, Any]] = resp.json()
                    errors: list[str] = [
                        item["error"]["description"]
                        for item in result_list
                        if "error" in item
                    ]
                    if errors:
                        return DeviceControlResult(
                            success=False, entity_id=entity_id, action=action,
                            error="; ".join(errors),
                        )
                    return DeviceControlResult(
                        success=True, entity_id=entity_id, action=action,
                    )
                else:
                    return DeviceControlResult(
                        success=False, entity_id=entity_id, action=action,
                        error=f"Bridge returned {resp.status_code}",
                    )
        except Exception as e:
            return DeviceControlResult(
                success=False, entity_id=entity_id, action=action,
                error=f"Control failed: {e}",
            )

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------

    async def get_state(self, ip: str, **kwargs: Any) -> dict[str, Any] | None:
        bridge_ip: str | None = self._bridge_ip()
        username: str | None = self._username()

        light_id: str = kwargs.get("light_id", "")
        if not light_id:
            cloud_id: str = kwargs.get("cloud_id", "")
            if cloud_id:
                light_id = cloud_id

        if not bridge_ip or not username or not light_id:
            return {"error": "Configuration incomplete or light_id missing"}

        try:
            import httpx
        except ImportError:
            return {"error": "httpx is not installed"}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"http://{bridge_ip}/api/{username}/lights/{light_id}",
                )
                if resp.status_code != 200:
                    return {"error": f"Bridge returned {resp.status_code}"}

                light_data: dict[str, Any] = resp.json()

                # Check for API error
                if isinstance(light_data, list):
                    for item in light_data:
                        if "error" in item:
                            return {"error": item["error"].get("description", "Unknown error")}
                    return {"error": "Unexpected response format"}

                raw_state: dict[str, Any] = light_data.get("state", {})

                state: dict[str, Any] = {
                    "state": "on" if raw_state.get("on") else "off",
                    "brightness": int(raw_state.get("bri", 0) / 254.0 * 100),
                    "reachable": raw_state.get("reachable", False),
                }

                # Color XY
                if "xy" in raw_state:
                    xy = raw_state["xy"]
                    state["xy"] = xy
                    bri_norm: float = raw_state.get("bri", 254) / 254.0
                    state["rgb"] = list(xy_to_rgb(xy[0], xy[1], bri_norm))

                # Color temperature
                if "ct" in raw_state:
                    mirek_val: int = raw_state["ct"]
                    state["color_temp_mirek"] = mirek_val
                    if mirek_val > 0:
                        state["color_temp"] = 1_000_000 // mirek_val

                # Hue/Sat (legacy)
                if "hue" in raw_state:
                    state["hue"] = raw_state["hue"]
                if "sat" in raw_state:
                    state["saturation"] = raw_state["sat"]

                state["name"] = light_data.get("name", "")
                state["type"] = light_data.get("type", "")

                return state

        except Exception as e:
            return {"error": f"Failed to get state: {e}"}
