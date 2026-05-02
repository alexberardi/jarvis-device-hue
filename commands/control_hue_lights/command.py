"""Voice command for controlling Philips Hue RGB lights."""

from __future__ import annotations

from typing import Any

from jarvis_command_sdk import (
    IJarvisCommand,
    CommandResponse,
    CommandExample,
    JarvisParameter,
    JarvisSecret,
    IJarvisSecret,
    RequestInformation,
    JarvisStorage,
)

from hue_shared.color import NAMED_COLORS, resolve_color_name

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


logger = JarvisLogger(service="cmd.control_hue_lights")

_storage = JarvisStorage("hue")


class ControlHueLightsCommand(IJarvisCommand):
    """Control Philips Hue lights — color, brightness, on/off."""

    command_name: str = "control_hue_lights"
    description: str = (
        "Control Philips Hue lights. Supports turning on/off, setting brightness, "
        "changing color by name (e.g., blue, red, warm white) or RGB values, "
        "and adjusting color temperature."
    )

    @property
    def keywords(self) -> list[str]:
        return [
            "hue", "light", "lights", "color", "brightness",
            "dim", "rgb", "lamp", "bulb", "philips",
        ]

    @property
    def parameters(self) -> list[JarvisParameter]:
        return [
            JarvisParameter(
                name="action",
                param_type="string",
                required=True,
                description="The action to perform: turn_on, turn_off, set_color, set_brightness, set_color_temp",
                enum_values=["turn_on", "turn_off", "set_color", "set_brightness", "set_color_temp"],
            ),
            JarvisParameter(
                name="light_name",
                param_type="string",
                required=False,
                description="Name of the light to control (e.g., 'bedroom', 'kitchen', 'desk lamp'). Omit to control all lights.",
            ),
            JarvisParameter(
                name="color",
                param_type="string",
                required=False,
                description="Color name (red, blue, green, purple, warm white, etc.) or RGB as 'r,g,b'",
            ),
            JarvisParameter(
                name="brightness",
                param_type="integer",
                required=False,
                description="Brightness percentage 0-100",
            ),
            JarvisParameter(
                name="color_temp",
                param_type="integer",
                required=False,
                description="Color temperature in Kelvin (2000=warm, 4000=neutral, 6500=cool)",
            ),
        ]

    @property
    def required_secrets(self) -> list[IJarvisSecret]:
        return [
            JarvisSecret(
                "HUE_BRIDGE_IP",
                "Local IP address of your Philips Hue Bridge",
                "integration",
                "string",
                friendly_name="Bridge IP",
                is_sensitive=False,
                required=True,
            ),
            JarvisSecret(
                "HUE_USERNAME",
                "Hue Bridge API username",
                "integration",
                "string",
                friendly_name="API Username",
                required=True,
            ),
        ]

    @property
    def setup_guide(self) -> str | None:
        return """## Setting Up Philips Hue

### Step 1: Find Your Bridge IP

Open the **Hue** app → **Settings** → **My Hue system** → tap your bridge.

### Step 2: Create an API Username

1. Press the **link button** on top of your Hue Bridge
2. Within 30 seconds, run:
```
curl -X POST http://<BRIDGE_IP>/api -d '{"devicetype":"jarvis#node"}'
```
3. Copy the `username` from the response"""

    def generate_prompt_examples(self) -> list[CommandExample]:
        return [
            CommandExample(
                voice_command="turn on the living room lights",
                expected_parameters={"action": "turn_on", "light_name": "living room"},
                is_primary=True,
            ),
            CommandExample(
                voice_command="set the bedroom lights to blue",
                expected_parameters={"action": "set_color", "light_name": "bedroom", "color": "blue"},
            ),
            CommandExample(
                voice_command="dim the kitchen lights to 30 percent",
                expected_parameters={"action": "set_brightness", "light_name": "kitchen", "brightness": 30},
            ),
            CommandExample(
                voice_command="turn off all the lights",
                expected_parameters={"action": "turn_off"},
            ),
            CommandExample(
                voice_command="set the desk lamp to warm white",
                expected_parameters={"action": "set_color", "light_name": "desk lamp", "color": "warm white"},
            ),
        ]

    def generate_adapter_examples(self) -> list[CommandExample]:
        return [
            CommandExample(
                voice_command="turn on the living room lights",
                expected_parameters={"action": "turn_on", "light_name": "living room"},
            ),
            CommandExample(
                voice_command="turn off the bedroom light",
                expected_parameters={"action": "turn_off", "light_name": "bedroom"},
            ),
            CommandExample(
                voice_command="set the kitchen to red",
                expected_parameters={"action": "set_color", "light_name": "kitchen", "color": "red"},
            ),
            CommandExample(
                voice_command="change the lights to purple",
                expected_parameters={"action": "set_color", "color": "purple"},
            ),
            CommandExample(
                voice_command="make the office green",
                expected_parameters={"action": "set_color", "light_name": "office", "color": "green"},
            ),
            CommandExample(
                voice_command="dim the hallway lights to 20 percent",
                expected_parameters={"action": "set_brightness", "light_name": "hallway", "brightness": 20},
            ),
            CommandExample(
                voice_command="set brightness to 75",
                expected_parameters={"action": "set_brightness", "brightness": 75},
            ),
            CommandExample(
                voice_command="turn on the desk lamp",
                expected_parameters={"action": "turn_on", "light_name": "desk lamp"},
            ),
            CommandExample(
                voice_command="set the bathroom to warm white",
                expected_parameters={"action": "set_color_temp", "light_name": "bathroom", "color_temp": 2700},
            ),
            CommandExample(
                voice_command="make the bedroom lights orange",
                expected_parameters={"action": "set_color", "light_name": "bedroom", "color": "orange"},
            ),
            CommandExample(
                voice_command="turn everything off",
                expected_parameters={"action": "turn_off"},
            ),
            CommandExample(
                voice_command="set the living room to 50 percent brightness",
                expected_parameters={"action": "set_brightness", "light_name": "living room", "brightness": 50},
            ),
            CommandExample(
                voice_command="change the garage light to cyan",
                expected_parameters={"action": "set_color", "light_name": "garage", "color": "cyan"},
            ),
            CommandExample(
                voice_command="set the lights to cool white",
                expected_parameters={"action": "set_color_temp", "color_temp": 6500},
            ),
            CommandExample(
                voice_command="make the nursery pink",
                expected_parameters={"action": "set_color", "light_name": "nursery", "color": "pink"},
            ),
        ]

    async def run(self, request_info: RequestInformation, **kwargs: Any) -> CommandResponse:
        action: str = kwargs.get("action", "")
        light_name: str | None = kwargs.get("light_name")
        color: str | None = kwargs.get("color")
        brightness: int | None = kwargs.get("brightness")
        color_temp: int | None = kwargs.get("color_temp")

        if not action:
            return CommandResponse.error_response("No action specified. Try 'turn on the lights' or 'set the lights to blue'.")

        bridge_ip: str | None = _storage.get_secret("HUE_BRIDGE_IP")
        username: str | None = _storage.get_secret("HUE_USERNAME")

        if not bridge_ip or not username:
            return CommandResponse.error_response(
                "Philips Hue is not configured. Please set your Bridge IP and API Username in Settings."
            )

        try:
            import httpx
        except ImportError:
            return CommandResponse.error_response("httpx package is not installed.")

        # Find matching lights
        target_lights: list[dict[str, Any]] = await self._find_lights(
            bridge_ip, username, light_name,
        )

        if not target_lights:
            if light_name:
                return CommandResponse.error_response(
                    f"No Hue light matching '{light_name}' was found. Check the light name in your Hue app."
                )
            return CommandResponse.error_response(
                "No Hue lights were found. Check your bridge connection."
            )

        # Build the state payload
        state_body: dict[str, Any] = {}

        if action == "turn_on":
            state_body = {"on": True}
        elif action == "turn_off":
            state_body = {"on": False}
        elif action == "set_brightness":
            pct: int = max(0, min(100, int(brightness or 100)))
            bri: int = max(1, int(pct / 100.0 * 254))
            state_body = {"on": True, "bri": bri}
        elif action == "set_color":
            rgb: tuple[int, int, int] | None = self._resolve_color(color)
            if rgb is None:
                available: str = ", ".join(sorted(NAMED_COLORS.keys())[:10])
                return CommandResponse.error_response(
                    f"Unknown color '{color}'. Try one of: {available}"
                )
            from hue_shared.color import rgb_to_xy
            xy: tuple[float, float] = rgb_to_xy(*rgb)
            state_body = {"on": True, "xy": list(xy)}
        elif action == "set_color_temp":
            kelvin: int = int(color_temp or 4000)
            mirek: int = max(153, min(500, 1_000_000 // max(kelvin, 1)))
            state_body = {"on": True, "ct": mirek}
        else:
            return CommandResponse.error_response(f"Unknown action: {action}")

        # Send to all matched lights
        results: list[str] = []
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=10) as client:
            for light in target_lights:
                light_id: str = light["id"]
                name: str = light["name"]
                try:
                    resp = await client.put(
                        f"http://{bridge_ip}/api/{username}/lights/{light_id}/state",
                        json=state_body,
                    )
                    if resp.status_code == 200:
                        resp_data: list[dict[str, Any]] = resp.json()
                        errs: list[str] = [
                            item["error"]["description"]
                            for item in resp_data
                            if isinstance(item, dict) and "error" in item
                        ]
                        if errs:
                            errors.append(f"{name}: {'; '.join(errs)}")
                        else:
                            results.append(name)
                    else:
                        errors.append(f"{name}: HTTP {resp.status_code}")
                except Exception as e:
                    errors.append(f"{name}: {e}")

        # Build response message
        message: str = self._build_response_message(
            action, results, errors, color, brightness, color_temp,
        )

        if errors and not results:
            return CommandResponse.error_response(message)

        return CommandResponse.success_response({"message": message})

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def _find_lights(
        self, bridge_ip: str, username: str, light_name: str | None,
    ) -> list[dict[str, Any]]:
        """Query bridge for lights, optionally filtering by name."""
        try:
            import httpx
        except ImportError:
            return []

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"http://{bridge_ip}/api/{username}/lights")
                if resp.status_code != 200:
                    return []

                all_lights: dict[str, Any] = resp.json()
                if isinstance(all_lights, list):
                    return []  # Error response from bridge

                lights: list[dict[str, Any]] = [
                    {"id": lid, "name": ldata.get("name", f"Light {lid}"), **ldata}
                    for lid, ldata in all_lights.items()
                ]

                if not light_name:
                    return lights

                # Fuzzy name matching
                query: str = light_name.lower().strip()
                exact: list[dict[str, Any]] = [
                    lt for lt in lights if lt["name"].lower() == query
                ]
                if exact:
                    return exact

                partial: list[dict[str, Any]] = [
                    lt for lt in lights if query in lt["name"].lower()
                ]
                if partial:
                    return partial

                # Word-level matching
                query_words: set[str] = set(query.split())
                word_matches: list[dict[str, Any]] = [
                    lt for lt in lights
                    if query_words & set(lt["name"].lower().split())
                ]
                return word_matches

        except Exception as e:
            logger.error(f"Failed to query lights: {e}")
            return []

    def _resolve_color(self, color: str | None) -> tuple[int, int, int] | None:
        """Resolve a color name or 'r,g,b' string to an RGB tuple."""
        if not color:
            return None

        # Try named color first
        rgb: tuple[int, int, int] | None = resolve_color_name(color)
        if rgb:
            return rgb

        # Try 'r,g,b' format
        parts: list[str] = color.replace(" ", "").split(",")
        if len(parts) == 3:
            try:
                r, g, b = int(parts[0]), int(parts[1]), int(parts[2])
                if all(0 <= v <= 255 for v in (r, g, b)):
                    return (r, g, b)
            except ValueError:
                pass

        return None

    def _build_response_message(
        self,
        action: str,
        successes: list[str],
        errors: list[str],
        color: str | None,
        brightness: int | None,
        color_temp: int | None,
    ) -> str:
        if not successes and errors:
            return f"Failed to control lights: {'; '.join(errors)}"

        names: str = ", ".join(successes)
        count: int = len(successes)
        label: str = names if count <= 3 else f"{count} lights"

        if action == "turn_on":
            msg: str = f"Turned on {label}"
        elif action == "turn_off":
            msg = f"Turned off {label}"
        elif action == "set_brightness":
            msg = f"Set {label} to {brightness}% brightness"
        elif action == "set_color":
            msg = f"Set {label} to {color}"
        elif action == "set_color_temp":
            msg = f"Set {label} to {color_temp}K color temperature"
        else:
            msg = f"Updated {label}"

        if errors:
            msg += f" (errors: {'; '.join(errors)})"

        return msg
