"""
Audio capture using sounddevice with WASAPI loopback support.

Provides non-blocking audio streaming that monitors system audio
without interrupting playback to other applications.
"""

from __future__ import annotations

import logging
import threading
from collections import deque
from typing import Callable, Optional

import numpy as np
import sounddevice as sd

from spectrum_visualizer.audio.devices import AudioDevice, DeviceManager

logger = logging.getLogger(__name__)

# Check if WASAPI loopback is available (Windows only)
try:
    WASAPI_LOOPBACK_AVAILABLE = hasattr(sd, 'WasapiSettings')
except Exception:
    WASAPI_LOOPBACK_AVAILABLE = False


class AudioCapture:
    """
    Real-time audio capture with WASAPI loopback support.
    
    Captures audio from system output (loopback) or input devices,
    providing audio data for spectrum analysis. Uses a ring buffer
    to ensure smooth, non-blocking data access.
    
    Example:
        >>> capture = AudioCapture(sample_rate=44100, buffer_size=4096)
        >>> capture.start()
        >>> audio_data = capture.get_audio_data()
        >>> capture.stop()
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 4096,
        channels: int = 1,
        device: Optional[AudioDevice | int | str] = None,
    ) -> None:
        """
        Initialize audio capture.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: FFT buffer size (samples per analysis frame)
            channels: Number of audio channels (1 for mono)
            device: Audio device to capture from
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.channels = channels
        
        # Device management
        self.device_manager = DeviceManager()
        self._device: Optional[AudioDevice] = None
        
        # Audio buffer - stores multiple frames for smooth access
        self._buffer_frames = 4  # Keep 4 buffer_size chunks
        self._ring_buffer: deque[np.ndarray] = deque(maxlen=self._buffer_frames)
        self._lock = threading.Lock()
        
        # Stream state
        self._stream: Optional[sd.InputStream] = None
        self._running = False
        
        # Callbacks
        self._on_audio_callback: Optional[Callable[[np.ndarray], None]] = None
        
        # Initialize device
        if device is not None:
            self.set_device(device)
        else:
            self._try_default_device()
    
    def _try_default_device(self) -> None:
        """Try to set up a default device."""
        try:
            # First try loopback
            loopback = self.device_manager.get_default_loopback()
            if loopback:
                self._device = self.device_manager.select_device(loopback)
                logger.info(f"Using loopback device: {self._device.name}")
            else:
                # Fall back to default input
                self._device = self.device_manager.select_device("default")
                logger.info(f"Using input device: {self._device.name}")
        except Exception as e:
            logger.warning(f"Could not set default device: {e}")
            self._device = None
    
    @property
    def device(self) -> Optional[AudioDevice]:
        """Get the current audio device."""
        return self._device
    
    @property
    def is_running(self) -> bool:
        """Check if audio capture is active."""
        return self._running
    
    def set_device(self, device: AudioDevice | int | str) -> None:
        """
        Set the audio capture device.
        
        Args:
            device: Device to capture from
        """
        was_running = self._running
        if was_running:
            self.stop()
        
        self._device = self.device_manager.select_device(device)
        
        if was_running:
            self.start()
    
    def cycle_device(self) -> AudioDevice:
        """Cycle to the next available device."""
        was_running = self._running
        if was_running:
            self.stop()
        
        self._device = self.device_manager.cycle_device()
        
        if was_running:
            self.start()
        
        return self._device
    
    def set_audio_callback(self, callback: Callable[[np.ndarray], None]) -> None:
        """
        Set a callback to be called with each audio frame.
        
        Args:
            callback: Function that receives audio data array
        """
        self._on_audio_callback = callback
    
    def _audio_callback(
        self,
        indata: np.ndarray,
        frames: int,
        time_info: dict,
        status: sd.CallbackFlags,
    ) -> None:
        """Internal callback for sounddevice stream."""
        if status:
            logger.warning(f"Audio callback status: {status}")
        
        # Convert to mono if needed
        if indata.ndim > 1:
            audio_data = np.mean(indata, axis=1)
        else:
            audio_data = indata.flatten()
        
        # Store in ring buffer
        with self._lock:
            self._ring_buffer.append(audio_data.copy())
        
        # Call user callback if set
        if self._on_audio_callback:
            try:
                self._on_audio_callback(audio_data)
            except Exception as e:
                logger.error(f"Audio callback error: {e}")
    
    def start(self) -> None:
        """Start audio capture."""
        if self._running:
            logger.warning("Audio capture already running")
            return
        
        if self._device is None:
            self._try_default_device()
            if self._device is None:
                raise RuntimeError("No audio device available")
        
        try:
            # Clear buffer
            self._ring_buffer.clear()
            
            # Determine channels to capture
            device_channels = min(self.channels, max(self._device.channels, 1))
            if device_channels < 1:
                device_channels = 1
            
            # Check if this is an output device (needs loopback mode)
            is_output_device = self._device.is_output and not self._device.is_input
            use_loopback = is_output_device and self._device.hostapi == "Windows WASAPI"
            
            # Get device sample rate
            device_info = sd.query_devices(self._device.index)
            device_samplerate = int(device_info['default_samplerate'])
            
            if use_loopback:
                # Use WASAPI loopback to capture from output device
                logger.info(f"Using WASAPI loopback for output device: {self._device.name}")
                
                # For loopback, we need to use the output device's channels
                loopback_channels = min(2, int(device_info['max_output_channels']))
                
                self._stream = sd.InputStream(
                    device=self._device.index,
                    channels=loopback_channels,
                    samplerate=device_samplerate,
                    blocksize=self.buffer_size,
                    dtype=np.float32,
                    callback=self._audio_callback,
                    extra_settings=sd.WasapiSettings(exclusive=False),
                )
            else:
                # Standard input capture
                self._stream = sd.InputStream(
                    device=self._device.index,
                    channels=device_channels,
                    samplerate=device_samplerate,
                    blocksize=self.buffer_size,
                    dtype=np.float32,
                    callback=self._audio_callback,
                )
            
            # Update our sample rate to match device
            self.sample_rate = device_samplerate
            
            self._stream.start()
            self._running = True
            logger.info(f"Audio capture started on {self._device.name} at {device_samplerate}Hz")
            
        except Exception as e:
            logger.error(f"Failed to start audio capture: {e}")
            self._running = False
            raise
    
    def stop(self) -> None:
        """Stop audio capture."""
        if not self._running:
            return
        
        self._running = False
        
        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error stopping audio stream: {e}")
            finally:
                self._stream = None
        
        logger.info("Audio capture stopped")
    
    def get_audio_data(self) -> np.ndarray:
        """
        Get the most recent audio data for analysis.
        
        Returns:
            Numpy array of audio samples (buffer_size length)
        """
        with self._lock:
            if not self._ring_buffer:
                # Return silence if no data yet
                return np.zeros(self.buffer_size, dtype=np.float32)
            
            # Get most recent frame
            return self._ring_buffer[-1].copy()
    
    def get_extended_buffer(self) -> np.ndarray:
        """
        Get an extended buffer with multiple frames concatenated.
        
        Useful for analysis that needs more context.
        
        Returns:
            Concatenated audio data from ring buffer
        """
        with self._lock:
            if not self._ring_buffer:
                return np.zeros(self.buffer_size, dtype=np.float32)
            
            return np.concatenate(list(self._ring_buffer))
    
    def get_peak_level(self) -> float:
        """Get the current peak audio level (0.0 to 1.0)."""
        data = self.get_audio_data()
        return float(np.max(np.abs(data)))
    
    def get_rms_level(self) -> float:
        """Get the current RMS audio level."""
        data = self.get_audio_data()
        return float(np.sqrt(np.mean(data ** 2)))
    
    def __enter__(self) -> "AudioCapture":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
    
    def __del__(self) -> None:
        """Cleanup on deletion."""
        self.stop()
