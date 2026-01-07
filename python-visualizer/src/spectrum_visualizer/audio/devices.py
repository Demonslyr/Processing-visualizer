"""
Audio device enumeration and management.

Provides functionality to discover and select audio devices,
with special support for WASAPI loopback devices on Windows.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

import sounddevice as sd

logger = logging.getLogger(__name__)


@dataclass
class AudioDevice:
    """Represents an audio device."""
    
    index: int
    name: str
    channels: int
    sample_rate: float
    is_loopback: bool
    is_input: bool
    is_output: bool
    hostapi: str
    
    def __str__(self) -> str:
        device_type = "loopback" if self.is_loopback else ("input" if self.is_input else "output")
        return f"[{self.index}] {self.name} ({device_type}, {self.hostapi})"


class DeviceManager:
    """
    Manages audio device discovery and selection.
    
    Supports WASAPI loopback devices on Windows for capturing
    system audio without interrupting playback.
    """
    
    def __init__(self) -> None:
        self._devices: list[AudioDevice] = []
        self._current_device: Optional[AudioDevice] = None
        self._refresh_devices()
    
    def _refresh_devices(self) -> None:
        """Refresh the list of available audio devices."""
        self._devices = []
        
        try:
            devices = sd.query_devices()
            hostapis = sd.query_hostapis()
            
            for i, device in enumerate(devices):
                hostapi_name = hostapis[device["hostapi"]]["name"]
                
                is_input = device["max_input_channels"] > 0
                is_output = device["max_output_channels"] > 0
                
                # A device is loopback-capable if it's a WASAPI output device
                # (we can capture from it using WASAPI loopback mode)
                is_loopback = (
                    "loopback" in device["name"].lower() or
                    "stereo mix" in device["name"].lower() or
                    (hostapi_name == "Windows WASAPI" and is_output)
                )
                
                audio_device = AudioDevice(
                    index=i,
                    name=device["name"],
                    channels=max(device["max_input_channels"], device["max_output_channels"]),
                    sample_rate=device["default_samplerate"],
                    is_loopback=is_loopback,
                    is_input=is_input,
                    is_output=is_output,
                    hostapi=hostapi_name,
                )
                self._devices.append(audio_device)
                
            logger.info(f"Found {len(self._devices)} audio devices")
            
        except Exception as e:
            logger.error(f"Failed to enumerate audio devices: {e}")
    
    @property
    def devices(self) -> list[AudioDevice]:
        """Get all available audio devices."""
        return self._devices
    
    @property
    def input_devices(self) -> list[AudioDevice]:
        """Get devices that support audio input."""
        return [d for d in self._devices if d.is_input]
    
    @property
    def loopback_devices(self) -> list[AudioDevice]:
        """Get WASAPI loopback devices for system audio capture."""
        return [d for d in self._devices if d.is_loopback]
    
    @property
    def current_device(self) -> Optional[AudioDevice]:
        """Get the currently selected device."""
        return self._current_device
    
    def get_device_by_name(self, name: str) -> Optional[AudioDevice]:
        """Find a device by name (partial match)."""
        name_lower = name.lower()
        for device in self._devices:
            if name_lower in device.name.lower():
                return device
        return None
    
    def get_device_by_index(self, index: int) -> Optional[AudioDevice]:
        """Get a device by its index."""
        for device in self._devices:
            if device.index == index:
                return device
        return None
    
    def select_device(self, device: AudioDevice | int | str) -> AudioDevice:
        """
        Select an audio device for capture.
        
        Args:
            device: AudioDevice instance, device index, or device name
            
        Returns:
            The selected AudioDevice
            
        Raises:
            ValueError: If device not found
        """
        if isinstance(device, AudioDevice):
            self._current_device = device
        elif isinstance(device, int):
            found = self.get_device_by_index(device)
            if found is None:
                raise ValueError(f"No device found with index {device}")
            self._current_device = found
        elif isinstance(device, str):
            if device.lower() == "default":
                # Try to find a suitable default device
                self._current_device = self._find_default_device()
            else:
                found = self.get_device_by_name(device)
                if found is None:
                    raise ValueError(f"No device found matching '{device}'")
                self._current_device = found
        else:
            raise TypeError(f"Expected AudioDevice, int, or str, got {type(device)}")
        
        logger.info(f"Selected audio device: {self._current_device}")
        return self._current_device
    
    def _find_default_device(self) -> AudioDevice:
        """Find the best default device for audio capture."""
        # First, try to find a loopback device
        loopback = self.loopback_devices
        if loopback:
            # Prefer WASAPI loopback
            wasapi_loopback = [d for d in loopback if "WASAPI" in d.hostapi]
            if wasapi_loopback:
                return wasapi_loopback[0]
            return loopback[0]
        
        # Fall back to any input device
        inputs = self.input_devices
        if inputs:
            return inputs[0]
        
        # Last resort: any device
        if self._devices:
            return self._devices[0]
        
        raise RuntimeError("No audio devices found")
    
    def get_default_loopback(self) -> Optional[AudioDevice]:
        """Get the default loopback device for system audio capture."""
        loopback = self.loopback_devices
        if loopback:
            # Prefer WASAPI
            wasapi = [d for d in loopback if "WASAPI" in d.hostapi]
            return wasapi[0] if wasapi else loopback[0]
        return None
    
    def list_devices(self) -> str:
        """Get a formatted string listing all devices."""
        lines = ["Available Audio Devices:", "=" * 60]
        
        # Group by type - prefer WASAPI output devices for loopback
        wasapi_outputs = [d for d in self._devices 
                         if d.hostapi == "Windows WASAPI" and d.is_output]
        inputs = [d for d in self.input_devices]
        
        if wasapi_outputs:
            lines.append("\n🔊 Output Devices (WASAPI Loopback - captures system audio):")
            for d in wasapi_outputs:
                lines.append(f"  [{d.index}] {d.name}")
        
        if inputs:
            lines.append("\n🎤 Input Devices:")
            for d in inputs:
                lines.append(f"  [{d.index}] {d.name} ({d.hostapi})")
        
        lines.append("\n💡 Tip: Use a WASAPI output device to capture system audio")
        lines.append("   Example: --device \"Speakers (Realtek\"")
        
        return "\n".join(lines)
    
    def cycle_device(self) -> AudioDevice:
        """Cycle to the next input/loopback device."""
        candidates = self.loopback_devices + [d for d in self.input_devices if not d.is_loopback]
        
        if not candidates:
            raise RuntimeError("No suitable audio devices found")
        
        if self._current_device is None:
            return self.select_device(candidates[0])
        
        # Find current index and move to next
        try:
            current_idx = next(
                i for i, d in enumerate(candidates) 
                if d.index == self._current_device.index
            )
            next_idx = (current_idx + 1) % len(candidates)
        except StopIteration:
            next_idx = 0
        
        return self.select_device(candidates[next_idx])
