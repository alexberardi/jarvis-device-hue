"""End-to-end: a spoken color name reaches the Hue bridge as a CIE xy payload.

Run with an environment that has ``jarvis_command_sdk`` (>= 0.3.5),
``jarvis_log_client`` and ``httpx`` available, e.g. the node venv:

    /path/to/jarvis-node-setup/.venv/bin/python -m pytest tests/ -q
"""

from __future__ import annotations

import asyncio
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))  # so `hue_shared` resolves

from jarvis_command_sdk import DiscoveredDevice  # noqa: E402
from hue_shared.color import rgb_to_xy  # noqa: E402

_PROTOCOL_PATH = _REPO_ROOT / "device_families" / "hue" / "protocol.py"


def _load_protocol() -> Any:
    spec = importlib.util.spec_from_file_location("hue_protocol_under_test", _PROTOCOL_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


hue_mod = _load_protocol()
HueProtocol = hue_mod.HueProtocol


class _FakeResp:
    def __init__(self, status: int = 200, payload: Any = None) -> None:
        self.status_code = status
        self._payload = payload if payload is not None else []

    def json(self) -> Any:
        return self._payload


class _FakeClient:
    """Captures the PUT body the protocol sends to the bridge."""

    last_put: dict[str, Any] = {}

    def __init__(self, *a: Any, **k: Any) -> None:
        pass

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *a: Any) -> bool:
        return False

    async def put(self, url: str, json: Any = None) -> _FakeResp:
        _FakeClient.last_put = {"url": url, "json": json}
        return _FakeResp(200, [])  # empty list => no bridge errors


@pytest.fixture(autouse=True)
def _patch(monkeypatch: pytest.MonkeyPatch) -> None:
    import httpx

    monkeypatch.setattr(httpx, "AsyncClient", _FakeClient)
    monkeypatch.setattr(HueProtocol, "_bridge_ip", lambda self: "10.0.0.5")
    monkeypatch.setattr(HueProtocol, "_username", lambda self: "api-user")
    _FakeClient.last_put = {}


def _device() -> DiscoveredDevice:
    return DiscoveredDevice(
        name="Bedroom", domain="light", manufacturer="hue",
        model="LCT001", protocol="hue", entity_id="bedroom", cloud_id="3",
    )


def test_set_color_by_name() -> None:
    result = asyncio.run(HueProtocol().control(_device(), "set_color", {"color": "green"}))
    assert result.success
    body = _FakeClient.last_put["json"]
    assert body["on"] is True
    assert body["xy"] == list(rgb_to_xy(0, 255, 0))


def test_set_color_warm_white_name() -> None:
    result = asyncio.run(HueProtocol().control(_device(), "set_color", {"color": "warm white"}))
    assert result.success
    assert _FakeClient.last_put["json"]["xy"] == list(rgb_to_xy(255, 214, 170))


def test_explicit_rgb_still_works() -> None:
    result = asyncio.run(HueProtocol().control(_device(), "set_color", {"rgb": [255, 0, 0]}))
    assert result.success
    assert _FakeClient.last_put["json"]["xy"] == list(rgb_to_xy(255, 0, 0))


def test_color_temp_still_works() -> None:
    result = asyncio.run(HueProtocol().control(_device(), "set_color", {"color_temp": 4000}))
    assert result.success
    assert "ct" in _FakeClient.last_put["json"]


def test_unknown_color_errors() -> None:
    result = asyncio.run(HueProtocol().control(_device(), "set_color", {"color": "chartreuse"}))
    assert not result.success
    assert "color" in (result.error or "").lower()
