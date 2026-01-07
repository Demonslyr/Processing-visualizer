"""
Application settings and configuration dataclasses.

Provides type-safe configuration with sensible defaults.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass
class AudioSettings:
    """Audio capture settings."""
    
    device: str = "default"
    sample_rate: int = 44100
    buffer_size: int = 4096
    channels: int = 1


@dataclass
class VisualizationSettings:
    """Visualization display settings."""
    
    mode: Literal["legacy", "modern"] = "modern"
    width: int = 800
    height: int = 300
    fps: int = 60
    bar_count: int = 50


@dataclass
class ColorSettings:
    """Color cycling settings."""
    
    cycle_speed: float = 0.02
    background: tuple[int, int, int] = (0, 0, 0)
    enabled: bool = True


@dataclass
class ParticleSettings:
    """Particle system settings."""
    
    enabled: bool = True
    count: int = 100


@dataclass
class BarAnimationSettings:
    """Bar animation dynamics settings."""
    
    # Growth rate: how fast bars rise (0.001 - 0.05, default 0.01)
    growth_rate: float = 0.01
    
    # Decay rate: how fast bars fall (0.005 - 0.05, default 0.015)  
    decay_rate: float = 0.015
    
    # Trigger threshold: signal must be this many times current to trigger rise (1.0 - 5.0, default 2.5)
    trigger_threshold: float = 2.5
    
    # Amplitude scaling factor for float audio (1 - 100, default 15)
    amplitude_scale: float = 15.0


@dataclass
class WindowSettings:
    """Window appearance settings."""
    
    borderless: bool = False
    always_on_top: bool = False
    title: str = "Spectrum Visualizer"


@dataclass
class Settings:
    """
    Complete application settings.
    
    Combines all setting categories into a single configuration object.
    """
    
    audio: AudioSettings = field(default_factory=AudioSettings)
    visualization: VisualizationSettings = field(default_factory=VisualizationSettings)
    colors: ColorSettings = field(default_factory=ColorSettings)
    particles: ParticleSettings = field(default_factory=ParticleSettings)
    bar_animation: BarAnimationSettings = field(default_factory=BarAnimationSettings)
    window: WindowSettings = field(default_factory=WindowSettings)
    
    @classmethod
    def create_default(cls) -> "Settings":
        """Create settings with all defaults."""
        return cls()
    
    @classmethod
    def create_legacy(cls) -> "Settings":
        """Create settings matching original Processing sketch."""
        return cls(
            audio=AudioSettings(
                sample_rate=44100,
                buffer_size=4096,
            ),
            visualization=VisualizationSettings(
                mode="legacy",
                width=800,
                height=300,
                fps=60,  # Processing target was 240, but 60 is smoother
                bar_count=50,
            ),
            colors=ColorSettings(
                cycle_speed=0.01,  # Slower, matching original
            ),
            particles=ParticleSettings(
                enabled=True,
                count=100,
            ),
        )
    
    def to_dict(self) -> dict:
        """Convert settings to dictionary for serialization."""
        return {
            "audio": {
                "device": self.audio.device,
                "sample_rate": self.audio.sample_rate,
                "buffer_size": self.audio.buffer_size,
                "channels": self.audio.channels,
            },
            "visualization": {
                "mode": self.visualization.mode,
                "width": self.visualization.width,
                "height": self.visualization.height,
                "fps": self.visualization.fps,
                "bar_count": self.visualization.bar_count,
            },
            "colors": {
                "cycle_speed": self.colors.cycle_speed,
                "background": list(self.colors.background),
                "enabled": self.colors.enabled,
            },
            "particles": {
                "enabled": self.particles.enabled,
                "count": self.particles.count,
            },
            "window": {
                "borderless": self.window.borderless,
                "always_on_top": self.window.always_on_top,
                "title": self.window.title,
            },
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Settings":
        """Create settings from dictionary."""
        settings = cls()
        
        if "audio" in data:
            audio = data["audio"]
            settings.audio = AudioSettings(
                device=audio.get("device", "default"),
                sample_rate=audio.get("sample_rate", 44100),
                buffer_size=audio.get("buffer_size", 4096),
                channels=audio.get("channels", 1),
            )
        
        if "visualization" in data:
            vis = data["visualization"]
            settings.visualization = VisualizationSettings(
                mode=vis.get("mode", "modern"),
                width=vis.get("width", 800),
                height=vis.get("height", 300),
                fps=vis.get("fps", 60),
                bar_count=vis.get("bar_count", 50),
            )
        
        if "colors" in data:
            colors = data["colors"]
            bg = colors.get("background", [0, 0, 0])
            settings.colors = ColorSettings(
                cycle_speed=colors.get("cycle_speed", 0.02),
                background=tuple(bg) if isinstance(bg, list) else bg,
                enabled=colors.get("enabled", True),
            )
        
        if "particles" in data:
            particles = data["particles"]
            settings.particles = ParticleSettings(
                enabled=particles.get("enabled", True),
                count=particles.get("count", 100),
            )
        
        if "window" in data:
            window = data["window"]
            settings.window = WindowSettings(
                borderless=window.get("borderless", False),
                always_on_top=window.get("always_on_top", False),
                title=window.get("title", "Spectrum Visualizer"),
            )
        
        return settings
