"""
Audio analysis including FFT and beat detection.

Provides real-time frequency spectrum analysis and beat detection
algorithms matching the original Processing implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

logger = logging.getLogger(__name__)


# Original Processing frequency bands (logarithmically distributed)
LEGACY_FREQ_BANDS = np.array([
    1, 3, 5, 10, 16, 22, 26, 31, 39, 42, 45, 55, 60, 65, 70, 80, 90, 100,
    120, 140, 160, 200, 240, 280, 320, 400, 480, 560, 590, 640, 720, 800,
    960, 1024, 1120, 1280, 1600, 1920, 2240, 2560, 3200, 3340, 3590, 3720,
    3840, 4480, 5120, 6400, 7680, 8960, 10240, 12800, 15360, 15360, 15360, 17800
], dtype=np.float32)


@dataclass
class AnalysisResult:
    """Results from audio analysis."""
    
    # Frequency bands (normalized 0-1)
    bands: np.ndarray
    
    # Raw FFT magnitudes
    fft_magnitudes: np.ndarray
    
    # Beat detection
    is_beat: bool
    beat_intensity: float
    
    # Audio levels
    peak_level: float
    rms_level: float
    
    # Frequencies
    frequencies: np.ndarray


@dataclass
class BeatDetector:
    """
    Beat detection using energy comparison.
    
    Detects beats by comparing current energy to recent average,
    matching the Minim library's BeatDetect behavior.
    """
    
    sensitivity_ms: float = 20.0
    threshold: float = 1.5
    
    # Internal state
    _energy_history: list[float] = field(default_factory=list)
    _history_size: int = 43  # ~1 second at 43fps
    _last_beat_time: float = 0.0
    _cooldown_samples: int = 0
    
    def detect(self, audio_data: np.ndarray, sample_rate: int = 44100) -> tuple[bool, float]:
        """
        Detect if current audio frame contains a beat.
        
        Args:
            audio_data: Audio samples
            sample_rate: Sample rate in Hz
            
        Returns:
            Tuple of (is_beat, intensity)
        """
        # Calculate current energy (RMS)
        current_energy = float(np.sqrt(np.mean(audio_data ** 2)))
        
        # Update history
        self._energy_history.append(current_energy)
        if len(self._energy_history) > self._history_size:
            self._energy_history.pop(0)
        
        # Calculate average energy
        avg_energy = np.mean(self._energy_history) if self._energy_history else 0.0
        
        # Calculate intensity (ratio of current to average)
        intensity = current_energy / avg_energy if avg_energy > 0.001 else 0.0
        
        # Apply cooldown
        if self._cooldown_samples > 0:
            self._cooldown_samples -= 1
            return False, intensity
        
        # Detect beat
        is_beat = intensity > self.threshold and current_energy > 0.01
        
        if is_beat:
            # Set cooldown based on sensitivity
            cooldown_frames = int((self.sensitivity_ms / 1000.0) * 60)  # Assuming ~60fps
            self._cooldown_samples = max(cooldown_frames, 1)
        
        return is_beat, min(intensity, 5.0)  # Cap intensity
    
    def reset(self) -> None:
        """Reset beat detection state."""
        self._energy_history.clear()
        self._cooldown_samples = 0


class AudioAnalyzer:
    """
    Real-time audio analysis with FFT and beat detection.
    
    Provides frequency band extraction matching the original
    Processing implementation, plus modern improvements.
    """
    
    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 4096,
        num_bands: int = 50,
        mode: str = "modern",
    ) -> None:
        """
        Initialize audio analyzer.
        
        Args:
            sample_rate: Audio sample rate in Hz
            buffer_size: FFT buffer size
            num_bands: Number of frequency bands to extract
            mode: "legacy" for original behavior, "modern" for improved
        """
        self.sample_rate = sample_rate
        self.buffer_size = buffer_size
        self.num_bands = num_bands
        self.mode = mode
        
        # FFT setup
        self._window = np.hanning(buffer_size)
        self._fft_freqs = np.fft.rfftfreq(buffer_size, 1.0 / sample_rate)
        
        # Frequency band mapping
        if mode == "legacy":
            self._band_freqs = LEGACY_FREQ_BANDS[:num_bands + 6]  # Extra for averaging
        else:
            self._band_freqs = self._generate_log_bands(num_bands)
        
        # Band indices for FFT bins
        self._band_indices = self._compute_band_indices()
        
        # Beat detection
        self.beat_detector = BeatDetector(sensitivity_ms=20.0)
        
        # Smoothing
        self._prev_bands: Optional[np.ndarray] = None
        self._smoothing = 0.3 if mode == "modern" else 0.0
        
        logger.info(f"AudioAnalyzer initialized: {mode} mode, {num_bands} bands")
    
    def _generate_log_bands(self, num_bands: int) -> np.ndarray:
        """Generate logarithmically spaced frequency bands."""
        min_freq = 20.0
        max_freq = min(self.sample_rate / 2, 20000.0)
        return np.logspace(
            np.log10(min_freq),
            np.log10(max_freq),
            num_bands + 1,
            dtype=np.float32
        )
    
    def _compute_band_indices(self) -> list[tuple[int, int]]:
        """Compute FFT bin indices for each frequency band."""
        indices = []
        freq_resolution = self.sample_rate / self.buffer_size
        
        for i in range(len(self._band_freqs) - 1):
            low_freq = self._band_freqs[i]
            high_freq = self._band_freqs[i + 1]
            
            low_bin = int(low_freq / freq_resolution)
            high_bin = int(high_freq / freq_resolution)
            
            # Ensure at least one bin
            high_bin = max(high_bin, low_bin + 1)
            
            # Clamp to valid range
            low_bin = min(low_bin, len(self._fft_freqs) - 1)
            high_bin = min(high_bin, len(self._fft_freqs))
            
            indices.append((low_bin, high_bin))
        
        return indices
    
    def analyze(self, audio_data: np.ndarray, amplitude_scale: float = 15.0) -> AnalysisResult:
        """
        Perform full audio analysis on a buffer.
        
        Args:
            audio_data: Audio samples (should be buffer_size length)
            amplitude_scale: Multiplier for band amplitudes (default 15.0)
            
        Returns:
            AnalysisResult with frequency bands, beat detection, etc.
        """
        # Ensure correct size
        if len(audio_data) < self.buffer_size:
            audio_data = np.pad(audio_data, (0, self.buffer_size - len(audio_data)))
        elif len(audio_data) > self.buffer_size:
            audio_data = audio_data[:self.buffer_size]
        
        # Apply window function
        windowed = audio_data * self._window
        
        # Compute FFT
        fft_result = np.fft.rfft(windowed)
        # Don't normalize - keep raw magnitudes like Processing's minim library
        magnitudes = np.abs(fft_result)
        
        # Extract frequency bands
        if self.mode == "legacy":
            bands = self._extract_bands_legacy(magnitudes, amplitude_scale)
        else:
            bands = self._extract_bands_modern(magnitudes)
        
        # Debug: log max band value periodically
        if hasattr(self, '_debug_counter'):
            self._debug_counter += 1
        else:
            self._debug_counter = 0
        if self._debug_counter % 60 == 0:  # Log every ~1 second at 60fps
            logger.debug(f"Audio: peak={np.max(np.abs(audio_data)):.4f}, max_band={np.max(bands):.2f}, max_mag={np.max(magnitudes):.2f}")
        
        # Apply smoothing
        if self._prev_bands is not None and self._smoothing > 0:
            bands = self._smoothing * self._prev_bands + (1 - self._smoothing) * bands
        self._prev_bands = bands.copy()
        
        # Beat detection
        is_beat, beat_intensity = self.beat_detector.detect(audio_data, self.sample_rate)
        
        # Audio levels
        peak_level = float(np.max(np.abs(audio_data)))
        rms_level = float(np.sqrt(np.mean(audio_data ** 2)))
        
        return AnalysisResult(
            bands=bands,
            fft_magnitudes=magnitudes,
            is_beat=is_beat,
            beat_intensity=beat_intensity,
            peak_level=peak_level,
            rms_level=rms_level,
            frequencies=self._fft_freqs,
        )
    
    def _extract_bands_legacy(self, magnitudes: np.ndarray, amplitude_scale: float = 15.0) -> np.ndarray:
        """
        Extract frequency bands using original Processing algorithm.
        
        Replicates: sqrt(((fft.getFreq(freq[g+1]) + 2*fft.getFreq(freq[g+2]) + fft.getFreq(freq[g+3]))/4) * 15 * ((k/25)+0.8)
        
        Args:
            magnitudes: FFT magnitude values
            amplitude_scale: Multiplier for amplitude (default 15.0)
        """
        bands = np.zeros(self.num_bands, dtype=np.float32)
        freq_resolution = self.sample_rate / self.buffer_size
        
        for i in range(self.num_bands):
            # Get 3 frequency bins with center weighting (matching original)
            freq1 = self._band_freqs[min(i + 1, len(self._band_freqs) - 1)]
            freq2 = self._band_freqs[min(i + 2, len(self._band_freqs) - 1)]
            freq3 = self._band_freqs[min(i + 3, len(self._band_freqs) - 1)]
            
            bin1 = int(freq1 / freq_resolution)
            bin2 = int(freq2 / freq_resolution)
            bin3 = int(freq3 / freq_resolution)
            
            # Clamp to valid range
            bin1 = max(0, min(bin1, len(magnitudes) - 1))
            bin2 = max(0, min(bin2, len(magnitudes) - 1))
            bin3 = max(0, min(bin3, len(magnitudes) - 1))
            
            # Weighted average (center bin weighted 2x)
            val = (magnitudes[bin1] + 2 * magnitudes[bin2] + magnitudes[bin3]) / 4
            
            # Apply sqrt and scaling (from original)
            # sqrt(val) * 15 * ((k/25) + 0.8)
            # Use amplitude_scale for dynamic adjustment
            scale = (i / 25.0) + 0.8
            bands[i] = np.sqrt(val * amplitude_scale) * amplitude_scale * scale
        
        return bands
    
    def _extract_bands_modern(self, magnitudes: np.ndarray) -> np.ndarray:
        """
        Extract frequency bands using improved algorithm.
        
        Uses proper logarithmic bands and A-weighting curve.
        """
        bands = np.zeros(self.num_bands, dtype=np.float32)
        
        for i, (low, high) in enumerate(self._band_indices[:self.num_bands]):
            if low < len(magnitudes) and high <= len(magnitudes):
                # Average magnitude in band
                band_mags = magnitudes[low:high]
                if len(band_mags) > 0:
                    # Use RMS for smoother response
                    bands[i] = np.sqrt(np.mean(band_mags ** 2))
        
        # Apply A-weighting approximation (boost mids, reduce bass/treble extremes)
        center_freqs = (self._band_freqs[:-1] + self._band_freqs[1:]) / 2
        center_freqs = center_freqs[:self.num_bands]
        a_weights = self._a_weighting(center_freqs)
        bands *= a_weights
        
        # Normalize and scale for visualization
        bands = bands * 50  # Scale factor
        
        return bands
    
    def _a_weighting(self, frequencies: np.ndarray) -> np.ndarray:
        """
        Calculate A-weighting coefficients for frequencies.
        
        Simplified A-weighting curve for perceptual loudness.
        """
        f = np.clip(frequencies, 20, 20000)
        
        # Simplified A-weighting formula
        ra = (12194**2 * f**4) / (
            (f**2 + 20.6**2) *
            np.sqrt((f**2 + 107.7**2) * (f**2 + 737.9**2)) *
            (f**2 + 12194**2)
        )
        
        # Normalize to 1 at 1kHz
        ra_1k = (12194**2 * 1000**4) / (
            (1000**2 + 20.6**2) *
            np.sqrt((1000**2 + 107.7**2) * (1000**2 + 737.9**2)) *
            (1000**2 + 12194**2)
        )
        
        return ra / ra_1k
    
    def get_frequency_for_band(self, band_index: int) -> float:
        """Get the center frequency for a band index."""
        if band_index < len(self._band_freqs) - 1:
            return (self._band_freqs[band_index] + self._band_freqs[band_index + 1]) / 2
        return self._band_freqs[-1]
    
    def reset(self) -> None:
        """Reset analyzer state."""
        self._prev_bands = None
        self.beat_detector.reset()
