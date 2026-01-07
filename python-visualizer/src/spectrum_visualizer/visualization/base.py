"""
Base renderer and color utilities for visualization.

Provides abstract base class for visualizers and common
color manipulation functions.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pygame

if TYPE_CHECKING:
    from spectrum_visualizer.audio.analysis import AnalysisResult
    from spectrum_visualizer.config.settings import Settings


@dataclass
class Color:
    """RGB color with optional alpha."""
    
    r: int
    g: int
    b: int
    a: int = 255
    
    def to_tuple(self) -> tuple[int, int, int]:
        """Convert to RGB tuple."""
        return (self.r, self.g, self.b)
    
    def to_tuple_alpha(self) -> tuple[int, int, int, int]:
        """Convert to RGBA tuple."""
        return (self.r, self.g, self.b, self.a)
    
    @classmethod
    def from_hsv(cls, h: float, s: float, v: float, a: int = 255) -> "Color":
        """
        Create color from HSV values.
        
        Args:
            h: Hue (0-360)
            s: Saturation (0-1)
            v: Value (0-1)
            a: Alpha (0-255)
        """
        h = h % 360
        c = v * s
        x = c * (1 - abs((h / 60) % 2 - 1))
        m = v - c
        
        if h < 60:
            r, g, b = c, x, 0
        elif h < 120:
            r, g, b = x, c, 0
        elif h < 180:
            r, g, b = 0, c, x
        elif h < 240:
            r, g, b = 0, x, c
        elif h < 300:
            r, g, b = x, 0, c
        else:
            r, g, b = c, 0, x
        
        return cls(
            int((r + m) * 255),
            int((g + m) * 255),
            int((b + m) * 255),
            a
        )


def rainbow_color(phase: float, offset: float = 0.0) -> Color:
    """
    Generate rainbow color using sine waves (original Processing algorithm).
    
    Args:
        phase: Current phase in color cycle (0-2π)
        offset: Phase offset for different colors
        
    Returns:
        RGB Color
    """
    r = abs(int(127 * math.sin(phase + offset) + 128))
    g = abs(int(127 * math.sin(phase + offset + 2.0) + 128))
    b = abs(int(127 * math.sin(phase + offset + 4.0) + 128))
    return Color(r, g, b)


def rainbow_color_smooth(phase: float, saturation: float = 1.0) -> Color:
    """
    Generate smooth rainbow color using HSV.
    
    Args:
        phase: Phase (0-1 for full cycle)
        saturation: Color saturation (0-1)
        
    Returns:
        RGB Color
    """
    hue = (phase * 360) % 360
    return Color.from_hsv(hue, saturation, 1.0)


def lerp_color(c1: Color, c2: Color, t: float) -> Color:
    """
    Linear interpolation between two colors.
    
    Args:
        c1: Start color
        c2: End color
        t: Interpolation factor (0-1)
        
    Returns:
        Interpolated color
    """
    t = max(0.0, min(1.0, t))
    return Color(
        int(c1.r + (c2.r - c1.r) * t),
        int(c1.g + (c2.g - c1.g) * t),
        int(c1.b + (c2.b - c1.b) * t),
        int(c1.a + (c2.a - c1.a) * t),
    )


class BaseRenderer(ABC):
    """
    Abstract base class for spectrum visualizers.
    
    Subclasses implement specific visualization styles
    (legacy, modern, etc.)
    """
    
    def __init__(self, settings: "Settings") -> None:
        """
        Initialize renderer.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.width = settings.visualization.width
        self.height = settings.visualization.height
        self.num_bars = settings.visualization.bar_count
        
        # Color cycling state
        self._color_phase = 0.0
        self._color_speed = settings.colors.cycle_speed
        self._color_enabled = True
        
        # Bar state (for animation)
        self._bar_heights = np.zeros(self.num_bars, dtype=np.float32)
        
        # Time tracking
        self._frame_count = 0
    
    @abstractmethod
    def render(
        self,
        surface: pygame.Surface,
        analysis: "AnalysisResult",
    ) -> None:
        """
        Render visualization to surface.
        
        Args:
            surface: Pygame surface to draw on
            analysis: Audio analysis results
        """
        pass
    
    def update(self, dt: float) -> None:
        """
        Update animation state.
        
        Args:
            dt: Delta time since last update (seconds)
        """
        # Update color phase
        if self._color_enabled:
            self._color_phase += self._color_speed
            if self._color_phase > 2 * math.pi:
                self._color_phase -= 2 * math.pi
        
        self._frame_count += 1
    
    def get_bar_color(self, bar_index: int) -> Color:
        """
        Get color for a bar based on current phase and index.
        
        Args:
            bar_index: Index of the bar (0 to num_bars-1)
            
        Returns:
            Color for this bar
        """
        if not self._color_enabled:
            return Color(128, 255, 128)  # Default green
        
        offset = bar_index * 0.02
        return rainbow_color(self._color_phase, offset)
    
    def toggle_color_cycling(self) -> bool:
        """Toggle color cycling on/off."""
        self._color_enabled = not self._color_enabled
        return self._color_enabled
    
    def set_color_speed(self, speed: float) -> None:
        """Set color cycling speed."""
        self._color_speed = speed
    
    def reset(self) -> None:
        """Reset renderer state."""
        self._bar_heights.fill(0)
        self._color_phase = 0.0
        self._frame_count = 0
