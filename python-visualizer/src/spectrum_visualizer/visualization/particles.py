"""
Particle system for ambient floating dots.

Replicates the original Processing dot particle effect.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame
import pygame.gfxdraw

# Track if gfxdraw is available
_HAS_GFXDRAW = True
try:
    pygame.gfxdraw.filled_circle  # Test if available
except AttributeError:
    _HAS_GFXDRAW = False


@dataclass
class Particle:
    """A single floating particle."""
    
    x: float
    y: float
    size: float
    dx: float
    dy: float
    alpha: int
    
    @classmethod
    def create_random(cls, width: int, height: int) -> "Particle":
        """Create a particle with random properties matching original."""
        divisor = 75
        
        # Random position
        x = random.uniform(0, width)
        y = random.uniform(0, height)
        
        # Size distribution (matching original)
        # Original: if diam<7: 1, elif diam<11: 2, else: 3
        raw_size = random.uniform(1, 12)
        if raw_size < 7:
            size = 1.0
        elif raw_size < 11:
            size = 2.0
        else:
            size = 3.0
        
        # Velocity (matching original)
        dx = (random.uniform(1, 3) / divisor) * 3
        dy = (random.uniform(0, 6) - 3) / divisor
        
        # Alpha/transparency
        alpha = random.randint(100, 255)
        
        return cls(x, y, size, dx, dy, alpha)


class ParticleSystem:
    """
    Floating particle system for ambient background effect.
    
    Replicates the dot particles from the original Processing sketch.
    """
    
    def __init__(
        self,
        count: int = 100,
        width: int = 800,
        height: int = 300,
        color: tuple[int, int, int] = (245, 245, 245),
        speed_multiplier: float = 1.0,
    ) -> None:
        """
        Initialize particle system.
        
        Args:
            count: Number of particles
            width: Canvas width
            height: Canvas height
            color: Particle color (RGB)
            speed_multiplier: Velocity multiplier (1.0 = default, higher = faster)
        """
        self.width = width
        self.height = height
        self.color = color
        self.enabled = True
        self.speed_multiplier = speed_multiplier
        
        # Create particles
        self._particles: list[Particle] = [
            Particle.create_random(width, height)
            for _ in range(count)
        ]
    
    @property
    def count(self) -> int:
        """Get particle count."""
        return len(self._particles)
    
    def update(self) -> None:
        """Update all particle positions."""
        if not self.enabled:
            return
        
        # Base speed boost (original was too slow for smooth movement)
        # Plus user-configurable multiplier
        effective_speed = 8.0 * self.speed_multiplier
        
        for p in self._particles:
            # Update position with speed multiplier
            p.x += p.dx * effective_speed
            p.y += p.dy * effective_speed
            
            # Wrap around edges (matching original)
            if p.x > self.width:
                p.x = 0
            elif p.x < 0:
                p.x = self.width
            
            if p.y > self.height:
                p.y = 0
            elif p.y < 0:
                p.y = self.height
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render all particles to surface with 2x supersampling for smooth movement.
        
        Args:
            surface: Pygame surface to draw on
        """
        if not self.enabled:
            return
        
        # Create 2x resolution surface for supersampling
        scale = 2
        ss_width = self.width * scale
        ss_height = self.height * scale
        
        # Create supersampled surface with alpha
        ss_surface = pygame.Surface((ss_width, ss_height), pygame.SRCALPHA)
        
        for p in self._particles:
            # Create color with alpha
            color = (*self.color, p.alpha)
            
            # Draw at 2x scale using round() for better positioning
            x = round(p.x * scale)
            y = round(p.y * scale)
            size = max(1, round(p.size * scale))
            
            # Draw particle
            if _HAS_GFXDRAW:
                pygame.gfxdraw.filled_circle(ss_surface, x, y, size, color)
            else:
                pygame.draw.circle(ss_surface, self.color, (x, y), size)
        
        # Scale down to target size (provides anti-aliasing)
        scaled = pygame.transform.smoothscale(ss_surface, (self.width, self.height))
        surface.blit(scaled, (0, 0))
    
    def resize(self, width: int, height: int) -> None:
        """
        Handle window resize.
        
        Args:
            width: New width
            height: New height
        """
        # Scale particle positions
        x_scale = width / self.width if self.width > 0 else 1
        y_scale = height / self.height if self.height > 0 else 1
        
        for p in self._particles:
            p.x *= x_scale
            p.y *= y_scale
        
        self.width = width
        self.height = height
    
    def set_count(self, count: int) -> None:
        """
        Change particle count.
        
        Args:
            count: New particle count
        """
        current = len(self._particles)
        
        if count > current:
            # Add particles
            for _ in range(count - current):
                self._particles.append(
                    Particle.create_random(self.width, self.height)
                )
        elif count < current:
            # Remove particles
            self._particles = self._particles[:count]
    
    def toggle(self) -> bool:
        """Toggle particle system on/off."""
        self.enabled = not self.enabled
        return self.enabled
    
    def reset(self) -> None:
        """Reset all particles to random positions."""
        for i, _ in enumerate(self._particles):
            self._particles[i] = Particle.create_random(self.width, self.height)
