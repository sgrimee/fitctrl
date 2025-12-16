"""
Async wrapper around pyftms client for FTMS fitness equipment control.

This module provides a clean interface to the FTMS protocol, handling
connection management, command execution, and event callbacks.
"""

import asyncio
import logging
from typing import Any, AsyncGenerator, Callable, Optional

import json
import os
import platform
from pathlib import Path

from bleak import BleakScanner
from pyftms import (
    FitnessMachine,
    FtmsEvents,
    MachineType,
    ResultCode,
    UpdateEvent,
    get_client,
    get_client_from_address,
)

from .core import FTMS_SERVICE_UUID, SPEED_MIN, SPEED_MAX, SPEED_STEP

logger = logging.getLogger(__name__)


class TreadmillController:
    """Manages connection and control of FTMS-compatible treadmills."""

    # Speed constraints (device-dependent, WalkingPad R3 as reference)
    SPEED_MIN = SPEED_MIN
    SPEED_MAX = SPEED_MAX
    SPEED_STEP = SPEED_STEP

    # FTMS service UUID for device discovery
    FTMS_SERVICE_UUID = FTMS_SERVICE_UUID

    @classmethod
    def _get_cache_file(cls) -> Path:
        """Get the standard cache file location for device address."""
        # Check XDG_CACHE_HOME first (Linux/Unix standard)
        cache_dir = os.environ.get("XDG_CACHE_HOME")
        if cache_dir:
            cache_path = Path(cache_dir) / "fitctrl"
        else:
            # Platform-specific fallbacks
            system = platform.system()
            if system == "Darwin":  # macOS
                cache_path = Path.home() / "Library" / "Caches" / "fitctrl"
            elif system == "Windows":
                # Use LOCALAPPDATA if available, otherwise APPDATA
                local_appdata = os.environ.get("LOCALAPPDATA")
                if local_appdata:
                    cache_path = Path(local_appdata) / "fitctrl"
                else:
                    appdata = os.environ.get(
                        "APPDATA", str(Path.home() / "AppData" / "Roaming")
                    )
                    cache_path = Path(appdata) / "fitctrl"
            else:  # Linux/Unix fallback
                cache_path = Path.home() / ".cache" / "fitctrl"

        # Ensure directory exists
        cache_path.mkdir(parents=True, exist_ok=True)
        return cache_path / "device_address.json"

    def __init__(self) -> None:
        """Initialize controller with no device connection."""
        self._client: Optional[FitnessMachine] = None
        self._update_queue: asyncio.Queue = asyncio.Queue(maxsize=10)
        self._is_running = False

        # Callbacks
        self._on_update: Optional[Callable] = None
        self._on_disconnect: Optional[Callable] = None

    @property
    def is_connected(self) -> bool:
        """Check if currently connected to device."""
        return self._client is not None and self._client.is_connected

    @property
    def device_info(self) -> Any:
        """Get device information if connected."""
        if not self.is_connected or self._client is None:
            return None
        return self._client.device_info

    @property
    def current_speed(self) -> float:
        """Get last known speed in km/h."""
        if not self.is_connected or self._client is None:
            return 0.0
        return float(self._client.speed_instant or 0.0)

    @property
    def training_status(self) -> Any:
        """Get current training status code."""
        if not self.is_connected or self._client is None:
            return None
        return self._client.training_status

    def set_on_update(self, callback: Callable) -> None:
        """Set callback for sensor data updates.

        Args:
            callback: Function called with UpdateEventData dict when sensor data changes
        """
        self._on_update = callback

    def set_on_disconnect(self, callback: Callable) -> None:
        """Set callback for disconnect events.

        Args:
            callback: Function called when device disconnects
        """
        self._on_disconnect = callback

    def _load_cached_address(self) -> str | None:
        """Load cached device address from file.

        Returns:
            Cached address string if available, None otherwise
        """
        try:
            cache_file = self._get_cache_file()
            if cache_file.exists():
                with open(cache_file, "r") as f:
                    data = json.load(f)
                    return data.get("address")
        except Exception as e:
            logger.warning(f"Failed to load cached address: {e}")
        return None

    def _save_cached_address(self, address: str) -> None:
        """Save device address to cache file.

        Args:
            address: Bluetooth address to cache
        """
        try:
            cache_file = self._get_cache_file()
            data = {"address": address}
            with open(cache_file, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Cached device address: {address}")
        except Exception as e:
            logger.warning(f"Failed to save cached address: {e}")

    def clear_address_cache(self) -> None:
        """Clear the cached device address.

        This will force rediscovery on next connection attempt.
        """
        try:
            cache_file = self._get_cache_file()
            if cache_file.exists():
                cache_file.unlink()
                logger.info("Cleared cached device address")
        except Exception as e:
            logger.warning(f"Failed to clear cached address: {e}")

    async def discover(self) -> bool:
        """Discover FTMS-compatible devices on BLE.

        Returns:
            True if device found, False otherwise
        """
        try:
            logger.info("Scanning for FTMS-compatible devices...")
            scanner = BleakScanner()
            devices = await scanner.discover(timeout=10.0)

            for device in devices:
                # Primary: check for known FTMS device names
                if device.name and (
                    "KS-AP-RQ3" in device.name
                    or "WalkingPad" in device.name.upper()
                    or "TREADMILL" in device.name.upper()
                ):
                    logger.info(f"Found FTMS device: {device.name} ({device.address})")
                    self._device = device
                    return True

                # Secondary: check if device advertises FTMS service (for future devices)
                service_uuids = (
                    getattr(device, "service_uuids", None)
                    or getattr(device, "advertisement", {}).get("service_uuids", [])
                    or device.metadata.get("uuids", [])
                    if hasattr(device, "metadata")
                    else []
                )

                if self.FTMS_SERVICE_UUID in service_uuids:
                    logger.info(
                        f"Found FTMS device by service: {device.name or 'Unknown'} ({device.address})"
                    )
                    self._device = device
                    return True

            logger.warning("No FTMS-compatible devices found")
            return False
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return False
        except Exception as e:
            logger.error(f"Discovery failed: {e}")
            return False

    async def connect(self) -> bool:
        """Connect to FTMS-compatible device.

        First tries to connect using cached address, then falls back to scanning.

        Returns:
            True if connected successfully, False otherwise
        """
        if self._client is not None and self.is_connected:
            logger.warning("Already connected")
            return True

        # First try cached address
        cached_address = self._load_cached_address()
        if cached_address:
            logger.info(f"Trying cached address: {cached_address}")
            try:
                self._client = await get_client_from_address(
                    cached_address,
                    scan_timeout=5.0,  # Quick timeout for cached address
                    timeout=5.0,
                    on_ftms_event=self._on_ftms_event,
                    on_disconnect=self._on_device_disconnect,
                )

                await self._client.connect()
                self._is_running = True
                logger.info(f"Connected to {self._client.name} (cached)")
                logger.info(f"Device info: {self._client.device_info}")

                # Cache the address for future use
                self._save_cached_address(cached_address)
                return True

            except Exception as e:
                logger.warning(f"Cached address failed: {e}")
                self._client = None

        # Fall back to scanning
        logger.info("Scanning for device...")
        if not await self.discover():
            logger.error("Device discovery failed")
            return False

        try:
            logger.info("Connecting to discovered device...")
            self._client = get_client(
                self._device,
                MachineType.TREADMILL,
                timeout=5.0,
                on_ftms_event=self._on_ftms_event,
                on_disconnect=self._on_device_disconnect,
            )

            await self._client.connect()
            self._is_running = True
            logger.info(f"Connected to {self._client.name}")
            logger.info(f"Device info: {self._client.device_info}")

            # Cache the address for future use
            if hasattr(self._device, "address"):
                self._save_cached_address(self._device.address)
            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self._client = None
            return False

    async def disconnect(self) -> None:
        """Disconnect from device."""
        if self._client is None:
            return

        try:
            logger.info("Disconnecting...")
            self._is_running = False
            await self._client.disconnect()
            self._client = None
            logger.info("Disconnected")
        except Exception as e:
            logger.error(f"Disconnect failed: {e}")

    async def start(self) -> ResultCode:
        """Start or resume treadmill.

        Returns:
            ResultCode enum indicating success or failure
        """
        if not self.is_connected:
            logger.error("Not connected")
            return ResultCode.FAILED

        try:
            result = await self._client.start_resume()  # type: ignore
            logger.info(f"Start command result: {result.name}")
            return result
        except Exception as e:
            logger.error(f"Start failed: {e}")
            return ResultCode.FAILED

    async def stop(self) -> ResultCode:
        """Stop treadmill.

        Returns:
            ResultCode enum indicating success or failure
        """
        if not self.is_connected:
            logger.error("Not connected")
            return ResultCode.FAILED

        try:
            result = await self._client.stop()  # type: ignore  # type: ignore
            logger.info(f"Stop command result: {result.name}")
            return result
        except Exception as e:
            logger.error(f"Stop failed: {e}")
            return ResultCode.FAILED

    async def pause(self) -> ResultCode:
        """Pause treadmill.

        Returns:
            ResultCode enum indicating success or failure
        """
        if not self.is_connected:
            logger.error("Not connected")
            return ResultCode.FAILED

        try:
            result = await self._client.pause()  # type: ignore  # type: ignore
            logger.info(f"Pause command result: {result.name}")
            return result
        except Exception as e:
            logger.error(f"Pause failed: {e}")
            return ResultCode.FAILED

    async def set_speed(self, km_h: float) -> ResultCode:
        """Set target speed in km/h.

        Args:
            km_h: Speed in km/h (1.0 to 12.0)

        Returns:
            ResultCode enum indicating success or failure
        """
        if not self.is_connected:
            logger.error("Not connected")
            return ResultCode.FAILED

        # Validate range
        if km_h < self.SPEED_MIN or km_h > self.SPEED_MAX:
            logger.error(
                f"Speed {km_h} out of range [{self.SPEED_MIN}, {self.SPEED_MAX}]"
            )
            return ResultCode.INVALID_PARAMETER

        try:
            result = await self._client.set_target_speed(km_h)  # type: ignore  # type: ignore
            logger.info(f"Set speed to {km_h} km/h: {result.name}")
            return result
        except Exception as e:
            logger.error(f"Set speed failed: {e}")
            return ResultCode.FAILED

    def get_status(self) -> dict:
        """Get current sensor values without waiting for update.

        Returns:
            Dictionary with current sensor values
        """
        if not self.is_connected:
            return {
                "status": "DISCONNECTED",
                "speed": 0.0,
                "distance": 0,
                "time": 0,
                "steps": 0,
                "calories": 0,
            }

        status_str = (
            self._client.training_status.name  # type: ignore  # type: ignore
            if self._client.training_status  # type: ignore  # type: ignore
            else "UNKNOWN"
        )

        return {
            "status": status_str,
            "speed": self._client.speed_instant or 0.0,  # type: ignore[union-attr]
            "distance": self._client.distance_total or 0,  # type: ignore[union-attr]
            "time": self._client.time_elapsed or 0,  # type: ignore[union-attr]
            "steps": self._client.step_count or 0,  # type: ignore[union-attr]
            "calories": self._client.energy_total or 0,  # type: ignore[union-attr]
        }

    def _on_ftms_event(self, event: FtmsEvents) -> None:
        """Handle FTMS events from device.

        Called synchronously from BLE thread - must not block.

        Args:
            event: FtmsEvents union (UpdateEvent, SetupEvent, ControlEvent, etc.)
        """
        try:
            if isinstance(event, UpdateEvent):
                # Queue update for async processing
                if self._is_running:
                    self._update_queue.put_nowait(event.event_data)
        except asyncio.QueueFull:
            # Drop if backed up - live display can skip a frame
            pass
        except Exception as e:
            logger.error(f"Event handler error: {e}")

    def _on_device_disconnect(self, client: FitnessMachine) -> None:
        """Handle device disconnect.

        Args:
            client: The FitnessMachine client that disconnected
        """
        logger.warning("Device disconnected")
        self._client = None
        self._is_running = False
        if self._on_disconnect:
            try:
                self._on_disconnect()
            except Exception as e:
                logger.error(f"Disconnect callback error: {e}")

    async def get_updates(self) -> AsyncGenerator[Any, None]:
        """Async generator that yields sensor updates.

        Yields:
            UpdateEventData dicts as they arrive from the device
        """
        while self._is_running:
            try:
                data = await asyncio.wait_for(
                    self._update_queue.get(),
                    timeout=0.5,
                )
                yield data
            except asyncio.TimeoutError:
                # Continue - device may be idle
                continue
            except Exception as e:
                logger.error(f"Update queue error: {e}")
                break
