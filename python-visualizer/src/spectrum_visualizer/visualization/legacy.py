"""
Legacy renderer - faithful recreation of original Processing visualizer.

Replicates the exact behavior of the original Processing sketch,
including bar animation algorithm, color cycling, and positioning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pygame

from spectrum_visualizer.visualization.base import BaseRenderer, rainbow_color
from spectrum_visualizer.visualization.particles import ParticleSystem

if TYPE_CHECKING:
    from spectrum_visualizer.audio.analysis import AnalysisResult
    from spectrum_visualizer.config.settings import Settings


@dataclass
class Bar:
    """
    A single visualizer bar with state.
    
    Replicates the bar class from Processing sketch.
    """
    
    x: int
    y: int = 250
    max_height: int = 200
    min_height: int = 6
    current_height: float = 0.0
    
    def update(
        self,
        new_height: float,
        beat_boost: int = 0,
        growth_rate: float = 0.01,
        decay_rate: float = 0.015,
        trigger_threshold: float = 2.5,
    ) -> float:
        """
        Update bar height with animation algorithm.
        
        Args:
            new_height: Target height from FFT
            beat_boost: Additional height on beat (typically 10)
            growth_rate: How fast bars rise (default 0.01)
            decay_rate: How fast bars fall (default 0.015)
            trigger_threshold: Signal ratio to trigger rise (default 2.5)
            
        Returns:
            Current display height
        """
        if new_height > (self.current_height * trigger_threshold) and self.current_height < self.max_height:
            # Rising - quick response to loud sounds
            self.current_height = self.current_height + (growth_rate * new_height) + beat_boost
        else:
            # Falling - gradual decay
            if self.current_height < self.min_height:
                self.current_height = self.min_height
            else:
                self.current_height = self.current_height - (decay_rate * self.current_height)
        
        return self.current_height


class LegacyRenderer(BaseRenderer):
    """
    Legacy visualization mode - exact Processing replica.
    
    Faithfully recreates the original Processing sketch's appearance
    and behavior, including:
    - 50 bars at x = i*13 + 100
    - Original bar animation algorithm
    - Sine-wave rainbow color cycling
    - Floating dot particles
    - Base line decoration
    """
    
    def __init__(self, settings: "Settings") -> None:
        """Initialize legacy renderer."""
        super().__init__(settings)
        
        # Create bars with original positioning
        # Original: (i*11)+(i*2)+100 = i*13 + 100
        self._bars: list[Bar] = [
            Bar(x=i * 13 + 100)
            for i in range(self.num_bars)
        ]
        
        # Bar dimensions (from original)
        self._bar_width = 11
        self._bar_y = 250  # Base Y position
        
        # Particle system
        self._particles = ParticleSystem(
            count=settings.particles.count,
            width=self.width,
            height=self.height,
            color=(245, 245, 245),
        )
        self._particles.enabled = settings.particles.enabled
        
        # Color cycling phase (updatec in original)
        self._color_phase = 1.0
    
    def render(
        self,
        surface: pygame.Surface,
        analysis: "AnalysisResult",
    ) -> None:
        """Render legacy visualization."""
        # Clear background (black)
        surface.fill((0, 0, 0))
        
        # Draw particles first (background layer)
        self._particles.update()
        self._particles.render(surface)
        
        # Beat boost
        beat_boost = 10 if analysis.is_beat else 0
        
        # Get animation settings
        growth_rate = self.settings.bar_animation.growth_rate
        decay_rate = self.settings.bar_animation.decay_rate
        trigger_threshold = self.settings.bar_animation.trigger_threshold
        
        # Draw bars
        for i, bar in enumerate(self._bars):
            # Get frequency band value
            band_value = analysis.bands[i] if i < len(analysis.bands) else 0.0
            
            # Update bar height with animation settings
            height = bar.update(
                band_value, beat_boost,
                growth_rate, decay_rate, trigger_threshold
            )
            
            # Get color with original sine-wave algorithm
            # Original: fill(abs(int(127*sin((updatec+(g*0.02)%6.28))+128)), ...)
            color = rainbow_color(self._color_phase, i * 0.02)
            
            # Draw bar rectangle
            # Original draws from (xloc, yloc) with negative height
            rect = pygame.Rect(
                bar.x,
                int(self._bar_y - height),
                self._bar_width,
                int(height)
            )
            pygame.draw.rect(surface, color.to_tuple(), rect)
            
            # Draw ellipse cap on top (original had stroke)
            ellipse_rect = pygame.Rect(
                bar.x + 1,
                int(self._bar_y - height) - 2,
                self._bar_width - 2,
                5
            )
            if ellipse_rect.height > 0 and ellipse_rect.width > 0:
                pygame.draw.ellipse(surface, color.to_tuple(), ellipse_rect)
        
        # Draw base line (from original)
        # Black thick line
        pygame.draw.line(
            surface,
            (0, 0, 0),
            (65, 247),
            (765, 247),
            10
        )
        # White thin line on top
        pygame.draw.line(
            surface,
            (245, 245, 245),
            (65, 246),
            (765, 246),
            3
        )
    
    def update(self, dt: float) -> None:
        """Update animation state."""
        super().update(dt)
        
        # Update color phase (matching original behavior)
        if self._color_enabled:
            # Original had updatec -= 0.01; updatec = updatec%6.28
            # But in the provided code it was not being updated in draw()
            # Using the positive direction for consistency
            self._color_phase -= 0.01
            if self._color_phase < 0:
                self._color_phase += 2 * math.pi
    
    def toggle_particles(self) -> bool:
        """Toggle particle system."""
        return self._particles.toggle()
    
    def reset(self) -> None:
        """Reset renderer state."""
        super().reset()
        for bar in self._bars:
            bar.current_height = 0.0
        self._particles.reset()
