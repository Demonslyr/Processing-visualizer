"""
Particle system for ambient floating dots.

Replicates the original Processing dot particle effect.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import pygame


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
    ) -> None:
        """
        Initialize particle system.
        
        Args:
            count: Number of particles
            width: Canvas width
            height: Canvas height
            color: Particle color (RGB)
        """
        self.width = width
        self.height = height
        self.color = color
        self.enabled = True
        
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
        
        for p in self._particles:
            # Update position
            p.x += p.dx
            p.y += p.dy
            
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
        Render all particles to surface.
        
        Args:
            surface: Pygame surface to draw on
        """
        if not self.enabled:
            return
        
        for p in self._particles:
            # Create color with alpha
            color = (*self.color, p.alpha)
            
            # Draw particle
            # Using gfxdraw for anti-aliased circles if available
            try:
                import pygame.gfxdraw
                pygame.gfxdraw.filled_circle(
                    surface,
                    int(p.x),
                    int(p.y),
                    int(p.size),
                    color
                )
            except (ImportError, AttributeError):
                # Fallback to regular circle
                pygame.draw.circle(
                    surface,
                    self.color,
                    (int(p.x), int(p.y)),
                    int(p.size)
                )
    
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
