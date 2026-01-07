"""
Main application class for Spectrum Visualizer.

Coordinates all components: audio capture, analysis, visualization, and UI.
"""

from __future__ import annotations

import logging
import sys
from typing import Optional, Union

import pygame

from spectrum_visualizer.audio.capture import AudioCapture
from spectrum_visualizer.audio.analysis import AudioAnalyzer
from spectrum_visualizer.config.settings import Settings
from spectrum_visualizer.config.persistence import save_config
from spectrum_visualizer.visualization.legacy import LegacyRenderer
from spectrum_visualizer.visualization.modern import ModernRenderer
from spectrum_visualizer.visualization.base import BaseRenderer
from spectrum_visualizer.ui.window import Window
from spectrum_visualizer.ui.menu import OverlayMenu

# Try to import loopback capture
try:
    from spectrum_visualizer.audio.loopback import WasapiLoopbackCapture, PYAUDIO_AVAILABLE
    LOOPBACK_AVAILABLE = PYAUDIO_AVAILABLE
except ImportError:
    LOOPBACK_AVAILABLE = False
    WasapiLoopbackCapture = None

logger = logging.getLogger(__name__)


class SpectrumVisualizer:
    """
    Main application class.
    
    Orchestrates audio capture, analysis, visualization, and user interaction.
    """
    
    def __init__(self, settings: Settings) -> None:
        """
        Initialize the spectrum visualizer.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        
        # Components (initialized in start())
        self._window: Optional[Window] = None
        self._audio: Optional[AudioCapture] = None
        self._loopback = None  # WASAPI loopback capture (type: WasapiLoopbackCapture)
        self._analyzer: Optional[AudioAnalyzer] = None
        self._renderer: Optional[BaseRenderer] = None
        self._menu: Optional[OverlayMenu] = None
        
        self._running = False
        self._use_loopback = LOOPBACK_AVAILABLE  # Prefer loopback on Windows
    
    def start(self) -> None:
        """Start the visualizer."""
        logger.info("Starting Spectrum Visualizer")
        
        try:
            # Initialize window
            self._window = Window(self.settings)
            self._window.initialize()
            
            # Initialize audio capture
            sample_rate = self.settings.audio.sample_rate
            
            if self._use_loopback and LOOPBACK_AVAILABLE:
                # Use WASAPI loopback for capturing system audio output
                logger.info("Using WASAPI loopback for audio capture")
                self._loopback = WasapiLoopbackCapture(
                    buffer_size=self.settings.audio.buffer_size,
                )
                
                # Start loopback capture
                self._loopback.start()
                
                # Use the device's actual sample rate for analyzer
                sample_rate = self._loopback.sample_rate
                logger.info(f"Loopback sample rate: {sample_rate}")
            else:
                # Fall back to regular input capture
                logger.info("Using standard audio input")
                self._audio = AudioCapture(
                    sample_rate=self.settings.audio.sample_rate,
                    buffer_size=self.settings.audio.buffer_size,
                    channels=self.settings.audio.channels,
                    device=self.settings.audio.device if self.settings.audio.device != "default" else None,
                )
                self._audio.start()
            
            # Initialize analyzer with correct sample rate
            self._analyzer = AudioAnalyzer(
                sample_rate=sample_rate,
                buffer_size=self.settings.audio.buffer_size,
                num_bands=self.settings.visualization.bar_count,
                mode=self.settings.visualization.mode,
            )
            
            # Initialize renderer
            self._create_renderer()
            
            # Initialize menu
            self._setup_menu()
            
            self._running = True
            logger.info("Visualizer started successfully")
            
        except Exception as e:
            logger.error(f"Failed to start visualizer: {e}")
            self.stop()
            raise
    
    def _create_renderer(self) -> None:
        """Create the appropriate renderer based on settings."""
        if self.settings.visualization.mode == "legacy":
            self._renderer = LegacyRenderer(self.settings)
        else:
            self._renderer = ModernRenderer(self.settings)
    
    def _setup_menu(self) -> None:
        """Set up the overlay menu."""
        self._menu = OverlayMenu(
            self.settings,
            width=360,
            height=400,
        )
        
        # Add menu items
        self._menu.add_item(
            "D", "Device",
            self._get_device_name,
            self._cycle_device,
        )
        self._menu.add_item(
            "V", "Mode",
            lambda: self.settings.visualization.mode.capitalize(),
            self._toggle_mode,
        )
        self._menu.add_item(
            "C", "Colors",
            lambda: "On" if self._renderer and self._renderer._color_enabled else "Off",
            self._toggle_colors,
        )
        self._menu.add_item(
            "P", "Particles",
            lambda: "On" if self.settings.particles.enabled else "Off",
            self._toggle_particles,
        )
        self._menu.add_item(
            "B", "Borderless",
            lambda: "On" if self.settings.window.borderless else "Off",
            self._toggle_borderless,
        )
        self._menu.add_item(
            "S", "Save Settings",
            lambda: "",
            self._save_settings,
        )
        self._menu.add_item(
            "Q", "Quit",
            lambda: "",
            self.stop,
        )
        
        # Add slider controls for bar animation
        self._menu.add_slider(
            "1", "2", "Amplitude",
            lambda: f"{self.settings.bar_animation.amplitude_scale:.0f}",
            lambda: self._adjust_amplitude(-2),
            lambda: self._adjust_amplitude(2),
        )
        self._menu.add_slider(
            "3", "4", "Growth",
            lambda: f"{self.settings.bar_animation.growth_rate:.3f}",
            lambda: self._adjust_growth(-0.002),
            lambda: self._adjust_growth(0.002),
        )
        self._menu.add_slider(
            "5", "6", "Decay",
            lambda: f"{self.settings.bar_animation.decay_rate:.3f}",
            lambda: self._adjust_decay(-0.003),
            lambda: self._adjust_decay(0.003),
        )
        self._menu.add_slider(
            "7", "8", "Threshold",
            lambda: f"{self.settings.bar_animation.trigger_threshold:.1f}",
            lambda: self._adjust_threshold(-0.3),
            lambda: self._adjust_threshold(0.3),
        )
    
    def _get_device_name(self) -> str:
        """Get current audio device name (truncated)."""
        if self._loopback and self._loopback.device:
            name = self._loopback.device.name
            return name[:20] + "..." if len(name) > 23 else name
        elif self._audio and self._audio.device:
            name = self._audio.device.name
            return name[:20] + "..." if len(name) > 23 else name
        return "Default Speakers"
    
    def _cycle_device(self) -> None:
        """Cycle to next audio device."""
        try:
            if self._loopback:
                # Cycle loopback device
                device = self._loopback.cycle_device()
                self.settings.audio.device = device.name
                
                # Update analyzer sample rate if it changed
                if self._analyzer and self._loopback.sample_rate != self._analyzer.sample_rate:
                    self._analyzer = AudioAnalyzer(
                        sample_rate=self._loopback.sample_rate,
                        buffer_size=self.settings.audio.buffer_size,
                        num_bands=self.settings.visualization.bar_count,
                        mode=self.settings.visualization.mode,
                    )
                
                if self._menu:
                    self._menu.show_status(f"Device: {device.name[:30]}")
            elif self._audio:
                # Cycle regular input device
                device = self._audio.cycle_device()
                self.settings.audio.device = device.name
                if self._menu:
                    self._menu.show_status(f"Device: {device.name[:30]}")
        except Exception as e:
            logger.error(f"Error cycling device: {e}")
            if self._menu:
                self._menu.show_status(f"Error: {e}")
    
    def _toggle_mode(self) -> None:
        """Toggle between legacy and modern modes."""
        if self.settings.visualization.mode == "legacy":
            self.settings.visualization.mode = "modern"
        else:
            self.settings.visualization.mode = "legacy"
        
        # Recreate analyzer and renderer
        if self._analyzer:
            self._analyzer = AudioAnalyzer(
                sample_rate=self.settings.audio.sample_rate,
                buffer_size=self.settings.audio.buffer_size,
                num_bands=self.settings.visualization.bar_count,
                mode=self.settings.visualization.mode,
            )
        
        self._create_renderer()
        
        if self._menu:
            self._menu.show_status(f"Mode: {self.settings.visualization.mode.capitalize()}")
    
    def _toggle_colors(self) -> None:
        """Toggle color cycling."""
        if self._renderer:
            enabled = self._renderer.toggle_color_cycling()
            self.settings.colors.enabled = enabled
            if self._menu:
                self._menu.show_status(f"Colors: {'On' if enabled else 'Off'}")
    
    def _toggle_particles(self) -> None:
        """Toggle particle system."""
        self.settings.particles.enabled = not self.settings.particles.enabled
        
        if self._renderer and hasattr(self._renderer, 'toggle_particles'):
            self._renderer.toggle_particles()
        
        if self._menu:
            self._menu.show_status(f"Particles: {'On' if self.settings.particles.enabled else 'Off'}")
    
    def _toggle_borderless(self) -> None:
        """Toggle borderless window."""
        if self._window:
            borderless = self._window.toggle_borderless()
            if self._menu:
                self._menu.show_status(f"Borderless: {'On' if borderless else 'Off'}")
    
    def _adjust_amplitude(self, delta: float) -> None:
        """Adjust amplitude scaling factor."""
        new_val = max(1, min(100, self.settings.bar_animation.amplitude_scale + delta))
        self.settings.bar_animation.amplitude_scale = new_val
        if self._menu:
            self._menu.show_status(f"Amplitude: {new_val:.0f}")
    
    def _adjust_growth(self, delta: float) -> None:
        """Adjust bar growth rate."""
        new_val = max(0.001, min(0.05, self.settings.bar_animation.growth_rate + delta))
        self.settings.bar_animation.growth_rate = new_val
        if self._menu:
            self._menu.show_status(f"Growth: {new_val:.3f}")
    
    def _adjust_decay(self, delta: float) -> None:
        """Adjust bar decay rate."""
        new_val = max(0.005, min(0.05, self.settings.bar_animation.decay_rate + delta))
        self.settings.bar_animation.decay_rate = new_val
        if self._menu:
            self._menu.show_status(f"Decay: {new_val:.3f}")
    
    def _adjust_threshold(self, delta: float) -> None:
        """Adjust trigger threshold."""
        new_val = max(1.0, min(5.0, self.settings.bar_animation.trigger_threshold + delta))
        self.settings.bar_animation.trigger_threshold = new_val
        if self._menu:
            self._menu.show_status(f"Threshold: {new_val:.1f}")
    
    def _save_settings(self) -> None:
        """Save current settings to file."""
        if save_config(self.settings):
            if self._menu:
                self._menu.show_status("Settings saved!")
        else:
            if self._menu:
                self._menu.show_status("Failed to save settings")
    
    def run(self) -> None:
        """Run the main loop."""
        if not self._running:
            self.start()
        
        try:
            while self._running and self._window and self._window.is_running:
                # Process events
                events = self._window.process_events()
                self._handle_events(events)
                
                # Get audio data and analyze
                audio_data = None
                if self._loopback:
                    audio_data = self._loopback.get_audio_data()
                elif self._audio:
                    audio_data = self._audio.get_audio_data()
                
                if audio_data is not None and self._analyzer:
                    analysis = self._analyzer.analyze(
                        audio_data,
                        amplitude_scale=self.settings.bar_animation.amplitude_scale
                    )
                else:
                    # Create dummy analysis if no audio
                    from spectrum_visualizer.audio.analysis import AnalysisResult
                    import numpy as np
                    analysis = AnalysisResult(
                        bands=np.zeros(self.settings.visualization.bar_count),
                        fft_magnitudes=np.zeros(100),
                        is_beat=False,
                        beat_intensity=0.0,
                        peak_level=0.0,
                        rms_level=0.0,
                        frequencies=np.zeros(100),
                    )
                
                # Render
                if self._renderer and self._window:
                    self._renderer.render(self._window.surface, analysis)
                
                # Render menu overlay
                if self._menu and self._window:
                    self._menu.update()
                    self._menu.render(self._window.surface)
                
                # Update display
                dt = self._window.update()
                
                # Update renderer animation
                if self._renderer:
                    self._renderer.update(dt)
                    
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        finally:
            self.stop()
    
    def _handle_events(self, events: list[pygame.event.Event]) -> None:
        """Handle pygame events."""
        for event in events:
            if event.type == pygame.KEYDOWN:
                # Let menu handle key first
                if self._menu and self._menu.handle_key(event.key):
                    continue
                
                # Handle other keys
                if event.key == pygame.K_q:
                    self.stop()
    
    def stop(self) -> None:
        """Stop the visualizer."""
        self._running = False
        
        if self._loopback:
            self._loopback.close()
            self._loopback = None
        
        if self._audio:
            self._audio.stop()
            self._audio = None
        
        if self._window:
            self._window.close()
            self._window = None
        
        logger.info("Visualizer stopped")
    
    def __enter__(self) -> "SpectrumVisualizer":
        """Context manager entry."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.stop()
