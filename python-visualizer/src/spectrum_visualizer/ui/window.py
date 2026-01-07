"""
Pygame window management.

Handles window creation, events, and display settings.
"""

from __future__ import annotations

import logging
import os
from typing import TYPE_CHECKING, Optional

import pygame

if TYPE_CHECKING:
    from spectrum_visualizer.config.settings import Settings

logger = logging.getLogger(__name__)


class Window:
    """
    Pygame window manager.
    
    Handles window creation, configuration, and basic event loop.
    """
    
    def __init__(self, settings: "Settings") -> None:
        """
        Initialize window.
        
        Args:
            settings: Application settings
        """
        self.settings = settings
        self.width = settings.visualization.width
        self.height = settings.visualization.height
        self.fps = settings.visualization.fps
        
        self._surface: Optional[pygame.Surface] = None
        self._clock: Optional[pygame.time.Clock] = None
        self._running = False
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize Pygame and create window."""
        if self._initialized:
            return
        
        # Initialize Pygame
        pygame.init()
        pygame.display.set_caption(self.settings.window.title)
        
        # Determine display flags
        flags = pygame.DOUBLEBUF
        
        if self.settings.window.borderless:
            flags |= pygame.NOFRAME
        
        # Create display surface
        self._surface = pygame.display.set_mode(
            (self.width, self.height),
            flags
        )
        
        # Set up clock for frame rate control
        self._clock = pygame.time.Clock()
        
        # Handle always on top (Windows-specific)
        if self.settings.window.always_on_top:
            self._set_always_on_top()
        
        self._initialized = True
        self._running = True
        logger.info(f"Window initialized: {self.width}x{self.height}")
    
    def _set_always_on_top(self) -> None:
        """Set window to always on top (Windows)."""
        try:
            import ctypes
            from ctypes import wintypes
            
            hwnd = pygame.display.get_wm_info()["window"]
            HWND_TOPMOST = -1
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            
            ctypes.windll.user32.SetWindowPos(
                hwnd,
                HWND_TOPMOST,
                0, 0, 0, 0,
                SWP_NOMOVE | SWP_NOSIZE
            )
            logger.info("Window set to always on top")
        except Exception as e:
            logger.warning(f"Could not set always on top: {e}")
    
    @property
    def surface(self) -> pygame.Surface:
        """Get the display surface."""
        if self._surface is None:
            raise RuntimeError("Window not initialized")
        return self._surface
    
    @property
    def is_running(self) -> bool:
        """Check if window is running."""
        return self._running
    
    def process_events(self) -> list[pygame.event.Event]:
        """
        Process window events.
        
        Returns:
            List of events for application handling
        """
        events = []
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self._running = False
            else:
                events.append(event)
        
        return events
    
    def update(self) -> float:
        """
        Update display and control frame rate.
        
        Returns:
            Delta time since last frame (seconds)
        """
        pygame.display.flip()
        
        if self._clock:
            dt = self._clock.tick(self.fps) / 1000.0
        else:
            dt = 1.0 / self.fps
        
        return dt
    
    def get_fps(self) -> float:
        """Get current FPS."""
        if self._clock:
            return self._clock.get_fps()
        return 0.0
    
    def resize(self, width: int, height: int) -> None:
        """
        Resize window.
        
        Args:
            width: New width
            height: New height
        """
        self.width = width
        self.height = height
        
        flags = pygame.DOUBLEBUF
        if self.settings.window.borderless:
            flags |= pygame.NOFRAME
        
        self._surface = pygame.display.set_mode((width, height), flags)
        logger.info(f"Window resized to {width}x{height}")
    
    def toggle_borderless(self) -> bool:
        """
        Toggle borderless mode.
        
        Returns:
            New borderless state
        """
        self.settings.window.borderless = not self.settings.window.borderless
        
        # Recreate window with new flags
        flags = pygame.DOUBLEBUF
        if self.settings.window.borderless:
            flags |= pygame.NOFRAME
        
        self._surface = pygame.display.set_mode((self.width, self.height), flags)
        
        if self.settings.window.always_on_top:
            self._set_always_on_top()
        
        return self.settings.window.borderless
    
    def set_title(self, title: str) -> None:
        """Set window title."""
        pygame.display.set_caption(title)
    
    def close(self) -> None:
        """Close window and quit Pygame."""
        self._running = False
        if self._initialized:
            pygame.quit()
            self._initialized = False
        logger.info("Window closed")
    
    def __enter__(self) -> "Window":
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit."""
        self.close()
