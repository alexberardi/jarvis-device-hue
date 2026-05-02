"""CIE XY color conversion and named color lookup for Philips Hue."""

from __future__ import annotations


# Named colors → RGB for voice commands like "set the lights to blue"
NAMED_COLORS: dict[str, tuple[int, int, int]] = {
    "red": (255, 0, 0),
    "green": (0, 255, 0),
    "blue": (0, 0, 255),
    "yellow": (255, 255, 0),
    "orange": (255, 165, 0),
    "purple": (128, 0, 128),
    "violet": (148, 0, 211),
    "pink": (255, 105, 180),
    "cyan": (0, 255, 255),
    "teal": (0, 128, 128),
    "magenta": (255, 0, 255),
    "white": (255, 255, 255),
    "warm white": (255, 214, 170),
    "cool white": (200, 220, 255),
    "lavender": (200, 162, 200),
    "coral": (255, 127, 80),
    "turquoise": (64, 224, 208),
    "gold": (255, 215, 0),
    "lime": (0, 255, 0),
    "indigo": (75, 0, 130),
    "salmon": (250, 128, 114),
    "mint": (152, 255, 152),
    "peach": (255, 218, 185),
    "sky blue": (135, 206, 235),
}


def _gamma_correct(value: float) -> float:
    """Apply gamma correction for sRGB to linear conversion."""
    if value > 0.04045:
        return pow((value + 0.055) / 1.055, 2.4)
    return value / 12.92


def rgb_to_xy(r: int, g: int, b: int) -> tuple[float, float]:
    """Convert RGB (0-255) to CIE 1931 xy chromaticity coordinates.

    Uses the Wide RGB D65 conversion matrix recommended by Philips.
    """
    # Normalize to 0-1 and apply gamma correction
    r_lin: float = _gamma_correct(r / 255.0)
    g_lin: float = _gamma_correct(g / 255.0)
    b_lin: float = _gamma_correct(b / 255.0)

    # Wide RGB D65 conversion matrix
    x: float = r_lin * 0.664511 + g_lin * 0.154324 + b_lin * 0.162028
    y: float = r_lin * 0.283881 + g_lin * 0.668433 + b_lin * 0.047685
    z: float = r_lin * 0.000088 + g_lin * 0.072310 + b_lin * 0.986039

    total: float = x + y + z
    if total == 0:
        return (0.3127, 0.3290)  # D65 white point

    cx: float = x / total
    cy: float = y / total
    return (round(cx, 4), round(cy, 4))


def xy_to_rgb(x: float, y: float, brightness: float = 1.0) -> tuple[int, int, int]:
    """Convert CIE xy + brightness back to approximate RGB (0-255)."""
    if y == 0:
        return (0, 0, 0)

    z: float = 1.0 - x - y
    yy: float = brightness
    xx: float = (yy / y) * x
    zz: float = (yy / y) * z

    # Reverse Wide RGB D65 matrix
    r_lin: float = xx * 1.656492 - yy * 0.354851 - zz * 0.255038
    g_lin: float = -xx * 0.707196 + yy * 1.655397 + zz * 0.036152
    b_lin: float = xx * 0.051713 - yy * 0.121364 + zz * 1.011530

    def reverse_gamma(v: float) -> float:
        if v <= 0.0031308:
            return 12.92 * v
        return (1.0 + 0.055) * pow(v, 1.0 / 2.4) - 0.055

    r_out: int = max(0, min(255, int(reverse_gamma(max(0.0, r_lin)) * 255)))
    g_out: int = max(0, min(255, int(reverse_gamma(max(0.0, g_lin)) * 255)))
    b_out: int = max(0, min(255, int(reverse_gamma(max(0.0, b_lin)) * 255)))
    return (r_out, g_out, b_out)


def resolve_color_name(name: str) -> tuple[int, int, int] | None:
    """Look up a named color, returning RGB tuple or None."""
    return NAMED_COLORS.get(name.lower().strip())
