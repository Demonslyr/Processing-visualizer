"""
Modern renderer - enhanced visualization with improved aesthetics.

Provides a polished, modern take on the spectrum visualizer with
rounded bars, glow effects, and smoother animations.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

import numpy as np
import pygame

from spectrum_visualizer.visualization.base import (
    BaseRenderer,
    Color,
    rainbow_color_smooth,
    lerp_color,
    brighten_saturate,
)
from spectrum_visualizer.visualization.particles import ParticleSystem

if TYPE_CHECKING:
    from spectrum_visualizer.audio.analysis import AnalysisResult
    from spectrum_visualizer.config.settings import Settings


class ModernRenderer(BaseRenderer):
    """
    Modern visualization with enhanced aesthetics.
    
    Features:
    - Rounded bar caps
    - Glow/bloom effects
    - Smooth color gradients
    - Reflection effect
    - Better frequency response visualization
    """
    
    def __init__(self, settings: "Settings") -> None:
        """Initialize modern renderer."""
        super().__init__(settings)
        
        # Layout
        self._margin = 50
        self._bar_spacing = 2
        self._available_width = self.width - (2 * self._margin)
        self._bar_width = max(4, (self._available_width - (self.num_bars - 1) * self._bar_spacing) // self.num_bars)
        self._bar_y = int(self.height * 0.8)  # Base line at 80% height
        self._max_bar_height = int(self.height * 0.7)
        
        # Animation state
        self._target_heights = np.zeros(self.num_bars, dtype=np.float32)
        self._current_heights = np.zeros(self.num_bars, dtype=np.float32)
        # Note: smoothing now comes from settings.bar_animation (growth_rate/decay_rate)
        
        # Peak hold (falling dots above bars)
        self._peaks = np.zeros(self.num_bars, dtype=np.float32)
        self._peak_velocities = np.zeros(self.num_bars, dtype=np.float32)
        self._peak_gravity = 0.5
        
        # Glow effect
        self._glow_enabled = True
        self._glow_intensity = 0.5
        
        # Reflection
        self._reflection_enabled = True
        self._reflection_alpha = 0.3
        
        # Back dust layer (80% of particles, behind everything)
        back_count = int(settings.particles.count * 0.8)
        self._particles_back = ParticleSystem(
            count=back_count,
            width=self.width,
            height=self.height,
            color=(200, 200, 200),
            speed_multiplier=settings.particles.speed,  # Default 0.2x
        )
        self._particles_back.enabled = settings.particles.enabled
        
        # Front dust layer (20% of particles, in front of bars)
        front_count = int(settings.particles.count * 0.2)
        self._particles_front = ParticleSystem(
            count=front_count,
            width=self.width,
            height=self.height,
            color=(255, 255, 255),  # Slightly brighter
            speed_multiplier=settings.particles.front_speed,  # Default 0.4x
        )
        self._particles_front.enabled = settings.particles.front_enabled
        
        self._settings = settings  # Keep reference for dynamic updates
        
        # Color state
        self._hue_offset = 0.0
        self._hue_speed = 0.002
        
        # Beat response
        self._beat_pulse = 0.0
        self._beat_decay = 0.80  # Faster decay for snappier beat response
    
    def render(
        self,
        surface: pygame.Surface,
        analysis: "AnalysisResult",
    ) -> None:
        """Render modern visualization."""
        # Update beat pulse
        if analysis.is_beat:
            self._beat_pulse = min(1.0, self._beat_pulse + 0.5)
        else:
            self._beat_pulse *= self._beat_decay
        
        # Background with subtle gradient
        self._draw_background(surface)
        
        # Update back particle speed from settings (allows runtime adjustment)
        self._particles_back.speed_multiplier = self._settings.particles.speed
        self._particles_back.enabled = self._settings.particles.enabled
        
        # Draw back dust (behind reflection and bars)
        self._particles_back.update()
        self._particles_back.render(surface)
        
        # Update bar heights with smoothing
        self._update_heights(analysis.bands)
        
        # Draw reflection first (behind bars)
        if self._reflection_enabled:
            self._draw_reflection(surface)
        
        # Draw glow
        if self._glow_enabled:
            self._draw_glow(surface)
        
        # Draw bars
        self._draw_bars(surface)
        
        # Draw peaks
        self._draw_peaks(surface)
        
        # Draw base line
        self._draw_base_line(surface)
        
        # Draw front dust (in front of everything, toggleable)
        self._particles_front.speed_multiplier = self._settings.particles.front_speed
        self._particles_front.enabled = self._settings.particles.front_enabled
        if self._particles_front.enabled:
            self._particles_front.update()
            self._particles_front.render(surface)
    
    def _draw_background(self, surface: pygame.Surface) -> None:
        """Draw gradient background."""
        # Solid dark background
        base_color = (10, 10, 15)
        surface.fill(base_color)
        
        # Optional: subtle gradient based on beat
        if self._beat_pulse > 0.1:
            pulse_alpha = int(20 * self._beat_pulse)
            overlay = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            overlay.fill((50, 30, 60, pulse_alpha))
            surface.blit(overlay, (0, 0))
    
    def _update_heights(self, bands: np.ndarray) -> None:
        """Update bar heights with smooth animation."""
        amplitude_scale = self._settings.bar_animation.amplitude_scale
        
        # Auto mode (amplitude_scale = 0): use original hardcoded behavior
        if amplitude_scale == 0:
            self._update_heights_auto(bands)
            return
        
        # Preset mode: use configurable settings
        growth_rate = self._settings.bar_animation.growth_rate
        decay_rate = self._settings.bar_animation.decay_rate
        trigger_threshold = self._settings.bar_animation.trigger_threshold
        
        # Set targets from analysis with amplitude scaling
        # amplitude_scale affects sensitivity (higher = more responsive to quiet sounds)
        raw_bands = bands[:self.num_bars]
        scaled_bands = raw_bands * (amplitude_scale / 15.0)  # Normalize around default of 15
        self._target_heights[:len(scaled_bands)] = scaled_bands
        
        # Apply threshold - values below threshold are suppressed
        self._target_heights = np.where(
            self._target_heights < trigger_threshold,
            self._target_heights * 0.3,  # Suppress quiet signals
            self._target_heights
        )
        
        # Scale to max height (but amplitude_scale still affects relative heights)
        max_val = np.max(self._target_heights)
        if max_val > 0:
            # Scale factor depends on amplitude - higher amp = less auto-scaling
            auto_scale = self._max_bar_height / max(max_val, 1.0)
            # Blend between full auto-scale (amp=1) and minimal auto-scale (amp=30+)
            blend = min(1.0, amplitude_scale / 30.0)
            effective_scale = auto_scale * (1.0 - blend * 0.7)  # At high amp, reduce auto-scale by 70%
            self._target_heights *= min(effective_scale, self._max_bar_height / 30)
        
        # Asymmetric smoothing: growth_rate when rising, decay_rate when falling
        for i in range(self.num_bars):
            diff = self._target_heights[i] - self._current_heights[i]
            if diff > 0:
                # Rising - use growth_rate (higher = faster rise)
                self._current_heights[i] += diff * min(1.0, growth_rate * 5)
            else:
                # Falling - use decay_rate (higher = faster fall)
                self._current_heights[i] += diff * min(1.0, decay_rate * 3)
        
        # Ensure minimum
        self._current_heights = np.maximum(self._current_heights, 3.0)
        
        # Update peaks (must run for all modes)
        self._update_peaks()
    
    def _update_heights_auto(self, bands: np.ndarray) -> None:
        """Original hardcoded auto-scaling behavior (Auto preset)."""
        # Set targets from analysis (no amplitude scaling)
        self._target_heights[:len(bands)] = bands[:self.num_bars]
        
        # Scale to max height (full auto-scaling)
        max_val = np.max(self._target_heights)
        if max_val > 0:
            scale = self._max_bar_height / max(max_val, 1.0)
            self._target_heights *= min(scale, self._max_bar_height / 50)  # Original limit
        
        # Smooth towards target (symmetric, fixed rate)
        diff = self._target_heights - self._current_heights
        self._current_heights += diff * 0.15  # Original smoothing factor
        
        # Ensure minimum
        self._current_heights = np.maximum(self._current_heights, 3.0)
        
        # Update peaks
        self._update_peaks()
    
    def _update_peaks(self) -> None:
        """Update peak hold indicators."""
        for i in range(self.num_bars):
            if self._current_heights[i] > self._peaks[i]:
                self._peaks[i] = self._current_heights[i]
                self._peak_velocities[i] = 0
            else:
                # Apply gravity
                self._peak_velocities[i] += self._peak_gravity
                self._peaks[i] -= self._peak_velocities[i]
                self._peaks[i] = max(self._peaks[i], self._current_heights[i])
    
    def _get_bar_x(self, index: int) -> int:
        """Get X position for bar index."""
        return self._margin + index * (self._bar_width + self._bar_spacing)
    
    def _get_bar_color(self, index: int) -> Color:
        """Get color for bar with modern gradient."""
        # Hue varies across spectrum
        base_hue = self._hue_offset + (index / self.num_bars) * 0.7
        color = rainbow_color_smooth(base_hue, saturation=0.8)
        
        # Brighten and saturate on beat (configurable intensity)
        beat_intensity = self._settings.visualization.beat_intensity
        if self._beat_pulse > 0.1 and beat_intensity > 0:
            color = brighten_saturate(color, self._beat_pulse * beat_intensity)
        
        return color
    
    def _draw_bars(self, surface: pygame.Surface) -> None:
        """Draw the main spectrum bars."""
        for i in range(self.num_bars):
            x = self._get_bar_x(i)
            height = int(self._current_heights[i])
            
            if height < 2:
                continue
            
            color = self._get_bar_color(i)
            
            # Main bar body
            bar_rect = pygame.Rect(
                x,
                self._bar_y - height,
                self._bar_width,
                height
            )
            pygame.draw.rect(surface, color.to_tuple(), bar_rect, border_radius=2)
            
            # Rounded cap
            cap_rect = pygame.Rect(
                x,
                self._bar_y - height - 2,
                self._bar_width,
                6
            )
            pygame.draw.ellipse(surface, color.to_tuple(), cap_rect)
    
    def _draw_glow(self, surface: pygame.Surface) -> None:
        """Draw glow effect behind bars."""
        glow_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        for i in range(self.num_bars):
            x = self._get_bar_x(i)
            height = int(self._current_heights[i])
            
            if height < 5:
                continue
            
            color = self._get_bar_color(i)
            glow_alpha = int(50 * self._glow_intensity)
            glow_color = (*color.to_tuple(), glow_alpha)
            
            # Draw larger blur rectangle
            glow_rect = pygame.Rect(
                x - 3,
                self._bar_y - height - 5,
                self._bar_width + 6,
                height + 10
            )
            pygame.draw.rect(glow_surface, glow_color, glow_rect, border_radius=5)
        
        surface.blit(glow_surface, (0, 0))
    
    def _draw_reflection(self, surface: pygame.Surface) -> None:
        """Draw reflection below bars."""
        reflection_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        for i in range(self.num_bars):
            x = self._get_bar_x(i)
            height = int(self._current_heights[i] * 0.4)  # Shorter reflection
            
            if height < 2:
                continue
            
            color = self._get_bar_color(i)
            
            # Gradient fade for reflection
            for y_offset in range(height):
                alpha = int(self._reflection_alpha * 255 * (1 - y_offset / height))
                if alpha < 5:
                    break
                
                pygame.draw.line(
                    reflection_surface,
                    (*color.to_tuple(), alpha),
                    (x, self._bar_y + 5 + y_offset),
                    (x + self._bar_width, self._bar_y + 5 + y_offset)
                )
        
        surface.blit(reflection_surface, (0, 0))
    
    def _draw_peaks(self, surface: pygame.Surface) -> None:
        """Draw falling peak indicators."""
        for i in range(self.num_bars):
            x = self._get_bar_x(i)
            peak_y = self._bar_y - int(self._peaks[i])
            
            if self._peaks[i] < 5:
                continue
            
            color = self._get_bar_color(i)
            
            # Small rectangle for peak
            pygame.draw.rect(
                surface,
                color.to_tuple(),
                (x, peak_y - 3, self._bar_width, 3),
                border_radius=1
            )
    
    def _draw_base_line(self, surface: pygame.Surface) -> None:
        """Draw stylized base line."""
        # Gradient line
        for i in range(self.num_bars):
            x = self._get_bar_x(i)
            color = self._get_bar_color(i)
            pygame.draw.line(
                surface,
                color.to_tuple(),
                (x, self._bar_y),
                (x + self._bar_width, self._bar_y),
                2
            )
    
    def update(self, dt: float) -> None:
        """Update animation state."""
        super().update(dt)
        
        # Update hue
        if self._color_enabled:
            self._hue_offset += self._hue_speed
            if self._hue_offset > 1.0:
                self._hue_offset -= 1.0
    
    def toggle_particles(self) -> bool:
        """Toggle both particle layers together."""
        result = self._particles_back.toggle()
        # Sync front layer to match back layer state
        self._particles_front.enabled = self._particles_back.enabled
        return result
    
    def toggle_glow(self) -> bool:
        """Toggle glow effect."""
        self._glow_enabled = not self._glow_enabled
        return self._glow_enabled
    
    def toggle_reflection(self) -> bool:
        """Toggle reflection effect."""
        self._reflection_enabled = not self._reflection_enabled
        return self._reflection_enabled
    
    def reset(self) -> None:
        """Reset renderer state."""
        super().reset()
        self._current_heights.fill(0)
        self._target_heights.fill(0)
        self._peaks.fill(0)
        self._peak_velocities.fill(0)
        self._beat_pulse = 0.0
        self._particles_back.reset()
        self._particles_front.reset()
