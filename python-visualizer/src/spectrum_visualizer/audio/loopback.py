"""
Audio capture using PyAudioWPatch for proper WASAPI loopback support.

This module provides true loopback capture from output devices on Windows,
allowing the visualizer to capture system audio without interrupting playback.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Callable, Optional

import numpy as np

try:
    import pyaudiowpatch as pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

logger = logging.getLogger(__name__)


class LoopbackDevice:
    """Represents an audio device with loopback capability."""
    
    def __init__(
        self,
        index: int,
        name: str,
        channels: int,
        sample_rate: int,
        is_loopback: bool,
        loopback_device_index: Optional[int] = None,
    ):
        self.index = index
        self.name = name
        self.channels = channels
        self.sample_rate = sample_rate
        self.is_loopback = is_loopback
        self.loopback_device_index = loopback_device_index
    
    def __str__(self) -> str:
        return f"[{self.index}] {self.name} ({'loopback' if self.is_loopback else 'input'})"


class WasapiLoopbackCapture:
    """
    Audio capture using PyAudioWPatch for WASAPI loopback.
    
    This allows capturing audio from output devices (speakers)
    without any impact on normal audio playback.
    """
    
    def __init__(
        self,
        buffer_size: int = 4096,
        device_index: Optional[int] = None,
    ) -> None:
        """
        Initialize WASAPI loopback capture.
        
        Args:
            buffer_size: Size of audio buffer for each callback
            device_index: Specific device to use (None for default speakers)
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError("pyaudiowpatch is required for loopback capture")
        
        self.buffer_size = buffer_size
        self._device_index = device_index
        
        # PyAudio instance
        self._pa: Optional[pyaudio.PyAudio] = None
        self._stream: Optional[pyaudio.Stream] = None
        
        # Audio state
        self._running = False
        self._sample_rate = 48000
        self._channels = 2
        
        # Ring buffer for audio data - need enough frames to hold buffer_size samples
        # With buffer_size=4096 and frames_per_buffer=4096, we need multiple chunks
        self._buffer_frames = 8  # Store multiple chunks for smooth FFT
        self._ring_buffer: deque[np.ndarray] = deque(maxlen=self._buffer_frames)
        self._lock = threading.Lock()
        
        # Current device
        self._device: Optional[LoopbackDevice] = None
        
        # Initialize PyAudio
        self._init_pyaudio()
    
    def _init_pyaudio(self) -> None:
        """Initialize PyAudio instance."""
        try:
            self._pa = pyaudio.PyAudio()
            logger.info("PyAudio initialized for WASAPI loopback")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {e}")
            raise
    
    def get_loopback_devices(self) -> list[LoopbackDevice]:
        """Get list of available loopback devices."""
        devices = []
        
        if self._pa is None:
            return devices
        
        try:
            # Get WASAPI host API info
            wasapi_info = None
            for i in range(self._pa.get_host_api_count()):
                api_info = self._pa.get_host_api_info_by_index(i)
                if api_info.get('name', '').lower() == 'windows wasapi':
                    wasapi_info = api_info
                    break
            
            if wasapi_info is None:
                logger.warning("WASAPI not found")
                return devices
            
            # Find loopback devices
            for i in range(self._pa.get_device_count()):
                try:
                    dev_info = self._pa.get_device_info_by_index(i)
                    
                    # Check if it's a WASAPI device with loopback
                    if dev_info.get('hostApi') == wasapi_info.get('index'):
                        is_loopback = dev_info.get('isLoopbackDevice', False)
                        
                        if is_loopback:
                            devices.append(LoopbackDevice(
                                index=i,
                                name=dev_info.get('name', 'Unknown'),
                                channels=int(dev_info.get('maxInputChannels', 2)),
                                sample_rate=int(dev_info.get('defaultSampleRate', 48000)),
                                is_loopback=True,
                                loopback_device_index=i,
                            ))
                except Exception as e:
                    logger.debug(f"Error checking device {i}: {e}")
                    continue
            
            logger.info(f"Found {len(devices)} loopback devices")
            
        except Exception as e:
            logger.error(f"Error enumerating loopback devices: {e}")
        
        return devices
    
    def get_default_loopback_device(self) -> Optional[LoopbackDevice]:
        """Get the default loopback device (default speakers)."""
        if self._pa is None:
            return None
        
        devices = self.get_loopback_devices()
        if not devices:
            return None
        
        # Prefer device with "Speakers" in name (not digital output)
        for dev in devices:
            if "speakers" in dev.name.lower() and "digital" not in dev.name.lower():
                logger.info(f"Selected speakers loopback: {dev.name}")
                return dev
        
        # Try PyAudioWPatch's default
        try:
            default_speakers = self._pa.get_default_wasapi_loopback()
            if default_speakers:
                logger.info(f"Using system default loopback: {default_speakers.get('name')}")
                return LoopbackDevice(
                    index=default_speakers['index'],
                    name=default_speakers.get('name', 'Default Speakers'),
                    channels=int(default_speakers.get('maxInputChannels', 2)),
                    sample_rate=int(default_speakers.get('defaultSampleRate', 48000)),
                    is_loopback=True,
                    loopback_device_index=default_speakers['index'],
                )
        except Exception as e:
            logger.warning(f"Could not get default loopback: {e}")
        
        # Fall back to first available loopback
        return devices[0] if devices else None
    
    def list_devices(self) -> str:
        """Get formatted string listing loopback devices."""
        devices = self.get_loopback_devices()
        lines = ["🔊 Available Loopback Devices (capture system audio):", "=" * 60]
        
        if devices:
            for d in devices:
                lines.append(f"  [{d.index}] {d.name}")
        else:
            lines.append("  No loopback devices found!")
            lines.append("  Make sure you have audio output devices connected.")
        
        return "\n".join(lines)
    
    @property
    def device(self) -> Optional[LoopbackDevice]:
        """Get current device."""
        return self._device
    
    @property
    def sample_rate(self) -> int:
        """Get sample rate."""
        return self._sample_rate
    
    @property
    def is_running(self) -> bool:
        """Check if capture is running."""
        return self._running
    
    def _audio_callback(
        self,
        in_data: bytes,
        frame_count: int,
        time_info: dict,
        status: int,
    ) -> tuple[None, int]:
        """PyAudio callback for audio data."""
        if status:
            logger.warning(f"PyAudio status: {status}")
        
        # Convert bytes to numpy array
        audio_data = np.frombuffer(in_data, dtype=np.float32)
        
        # Convert to mono if stereo
        if self._channels == 2:
            audio_data = audio_data.reshape(-1, 2).mean(axis=1)
        
        # Store in ring buffer
        with self._lock:
            self._ring_buffer.append(audio_data.copy())
        
        return (None, pyaudio.paContinue)
    
    def start(self, device_index: Optional[int] = None) -> None:
        """
        Start loopback capture.
        
        Args:
            device_index: Device index to capture from (None for default)
        """
        if self._running:
            logger.warning("Loopback capture already running")
            return
        
        if self._pa is None:
            self._init_pyaudio()
        
        # Get device
        if device_index is not None:
            # Find device by index
            devices = self.get_loopback_devices()
            self._device = next((d for d in devices if d.index == device_index), None)
        else:
            self._device = self.get_default_loopback_device()
        
        if self._device is None:
            raise RuntimeError("No loopback device available")
        
        try:
            # Clear buffer
            self._ring_buffer.clear()
            
            # Set up stream parameters
            self._sample_rate = self._device.sample_rate
            self._channels = min(2, self._device.channels)
            
            logger.info(f"Starting loopback capture: {self._device.name}")
            logger.info(f"  Sample rate: {self._sample_rate}, Channels: {self._channels}")
            
            # Create stream
            self._stream = self._pa.open(
                format=pyaudio.paFloat32,
                channels=self._channels,
                rate=self._sample_rate,
                input=True,
                input_device_index=self._device.index,
                frames_per_buffer=self.buffer_size,
                stream_callback=self._audio_callback,
            )
            
            self._stream.start_stream()
            self._running = True
            logger.info("Loopback capture started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start loopback capture: {e}")
            self._running = False
            raise
    
    def stop(self) -> None:
        """Stop loopback capture."""
        self._running = False
        
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self._stream = None
        
        logger.info("Loopback capture stopped")
    
    def get_audio_data(self) -> np.ndarray:
        """
        Get the most recent audio data concatenated from ring buffer.
        
        Returns:
            Numpy array of audio samples (buffer_size length)
        """
        with self._lock:
            if not self._ring_buffer:
                return np.zeros(self.buffer_size, dtype=np.float32)
            
            # Concatenate all chunks in the ring buffer
            all_data = np.concatenate(list(self._ring_buffer))
            
            # Return the most recent buffer_size samples
            if len(all_data) >= self.buffer_size:
                return all_data[-self.buffer_size:]
            else:
                # Pad with zeros if not enough data yet
                result = np.zeros(self.buffer_size, dtype=np.float32)
                result[-len(all_data):] = all_data
                return result
    
    def cycle_device(self) -> LoopbackDevice:
        """Cycle to next loopback device."""
        devices = self.get_loopback_devices()
        
        if not devices:
            raise RuntimeError("No loopback devices available")
        
        was_running = self._running
        if was_running:
            self.stop()
        
        # Find next device
        if self._device is None:
            self._device = devices[0]
        else:
            try:
                current_idx = next(
                    i for i, d in enumerate(devices)
                    if d.index == self._device.index
                )
                next_idx = (current_idx + 1) % len(devices)
            except StopIteration:
                next_idx = 0
            self._device = devices[next_idx]
        
        if was_running:
            self.start(self._device.index)
        
        return self._device
    
    def close(self) -> None:
        """Clean up resources."""
        self.stop()
        
        if self._pa is not None:
            try:
                self._pa.terminate()
            except Exception:
                pass
            self._pa = None
    
    def __enter__(self) -> "WasapiLoopbackCapture":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
    
    def __del__(self) -> None:
        self.close()
