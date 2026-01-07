"""
Overlay menu for runtime settings.

Provides a temporary on-screen menu for adjusting settings
without interrupting the visualization.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Optional

import pygame

if TYPE_CHECKING:
    from spectrum_visualizer.config.settings import Settings

# Menu colors
MENU_BG_COLOR = (20, 20, 30, 200)
MENU_BORDER_COLOR = (100, 100, 120)
MENU_TEXT_COLOR = (220, 220, 220)
MENU_HIGHLIGHT_COLOR = (80, 180, 255)
MENU_KEY_COLOR = (255, 200, 100)


@dataclass
class MenuItem:
    """A menu item with key binding."""
    
    key: str
    label: str
    value_getter: Callable[[], str]
    action: Callable[[], None]
    multiline: bool = False  # If True, value shows on second line


@dataclass
class SliderItem:
    """A slider menu item with increase/decrease keys."""
    
    key_decrease: str  # Key to decrease value
    key_increase: str  # Key to increase value
    label: str
    value_getter: Callable[[], str]
    action_decrease: Callable[[], None]
    action_increase: Callable[[], None]


class OverlayMenu:
    """
    Temporary overlay menu for settings.
    
    Features:
    - Semi-transparent background
    - Auto-hide after timeout
    - Keyboard navigation
    """
    
    AUTO_HIDE_SECONDS = 5.0
    
    def __init__(
        self,
        settings: "Settings",
        width: int = 420,
        height: int = 560,
    ) -> None:
        """
        Initialize overlay menu.
        
        Args:
            settings: Application settings
            width: Menu width (default 420)
            height: Menu height (default 560)
        """
        self.settings = settings
        self.width = width
        self.height = height
        
        self._visible = False
        self._last_interaction = 0.0
        self._items: list[MenuItem] = []
        self._sliders: list[SliderItem] = []
        
        # Font setup (initialized lazily)
        self._font: Optional[pygame.font.Font] = None
        self._title_font: Optional[pygame.font.Font] = None
        
        # Status message
        self._status_message = ""
        self._status_time = 0.0
        self._status_duration = 2.0
    
    def _ensure_fonts(self) -> None:
        """Initialize fonts if needed."""
        if self._font is None:
            pygame.font.init()
            self._font = pygame.font.SysFont("consolas", 16)
            self._title_font = pygame.font.SysFont("consolas", 20, bold=True)
    
    def add_item(
        self,
        key: str,
        label: str,
        value_getter: Callable[[], str],
        action: Callable[[], None],
        multiline: bool = False,
    ) -> None:
        """
        Add a menu item.
        
        Args:
            key: Keyboard key to trigger action
            label: Display label
            value_getter: Function returning current value string
            action: Function to call when activated
            multiline: If True, value displays on second line
        """
        self._items.append(MenuItem(key, label, value_getter, action, multiline))
    
    def add_slider(
        self,
        key_decrease: str,
        key_increase: str,
        label: str,
        value_getter: Callable[[], str],
        action_decrease: Callable[[], None],
        action_increase: Callable[[], None],
    ) -> None:
        """
        Add a slider menu item.
        
        Args:
            key_decrease: Key to decrease value
            key_increase: Key to increase value
            label: Display label
            value_getter: Function returning current value string
            action_decrease: Function to decrease value
            action_increase: Function to increase value
        """
        self._sliders.append(SliderItem(
            key_decrease, key_increase, label,
            value_getter, action_decrease, action_increase
        ))
    
    def clear_items(self) -> None:
        """Remove all menu items."""
        self._items.clear()
        self._sliders.clear()
    
    @property
    def is_visible(self) -> bool:
        """Check if menu is currently visible."""
        return self._visible
    
    def show(self) -> None:
        """Show the menu."""
        self._visible = True
        self._last_interaction = time.time()
    
    def hide(self) -> None:
        """Hide the menu."""
        self._visible = False
    
    def toggle(self) -> bool:
        """
        Toggle menu visibility.
        
        Returns:
            New visibility state
        """
        if self._visible:
            self.hide()
        else:
            self.show()
        return self._visible
    
    def show_status(self, message: str, duration: float = 2.0) -> None:
        """
        Show a temporary status message.
        
        Args:
            message: Message to display
            duration: How long to show (seconds)
        """
        self._status_message = message
        self._status_time = time.time()
        self._status_duration = duration
    
    def handle_key(self, key: int) -> bool:
        """
        Handle a key press.
        
        Args:
            key: Pygame key code
            
        Returns:
            True if key was handled
        """
        self._last_interaction = time.time()
        
        # Toggle menu on M or Escape
        if key == pygame.K_m or key == pygame.K_ESCAPE:
            self.toggle()
            return True
        
        # Only process item keys if visible
        if not self._visible:
            return False
        
        # Check menu items
        key_char = pygame.key.name(key).upper()
        for item in self._items:
            if item.key.upper() == key_char:
                item.action()
                self._last_interaction = time.time()
                return True
        
        # Check slider items
        for slider in self._sliders:
            if slider.key_decrease.upper() == key_char:
                slider.action_decrease()
                self._last_interaction = time.time()
                return True
            if slider.key_increase.upper() == key_char:
                slider.action_increase()
                self._last_interaction = time.time()
                return True
        
        return False
    
    def update(self) -> None:
        """Update menu state (auto-hide check)."""
        if self._visible:
            elapsed = time.time() - self._last_interaction
            if elapsed > self.AUTO_HIDE_SECONDS:
                self.hide()
    
    def render(self, surface: pygame.Surface) -> None:
        """
        Render menu to surface.
        
        Args:
            surface: Surface to render on
        """
        self._ensure_fonts()
        
        # Always render status message if active
        self._render_status(surface)
        
        if not self._visible:
            return
        
        # Calculate menu position (centered)
        screen_width = surface.get_width()
        screen_height = surface.get_height()
        
        x = (screen_width - self.width) // 2
        y = (screen_height - self.height) // 2
        
        # Create menu surface with alpha
        menu_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
        
        # Background
        pygame.draw.rect(
            menu_surface,
            MENU_BG_COLOR,
            (0, 0, self.width, self.height),
            border_radius=10
        )
        
        # Border
        pygame.draw.rect(
            menu_surface,
            MENU_BORDER_COLOR,
            (0, 0, self.width, self.height),
            width=2,
            border_radius=10
        )
        
        # Title
        title = self._title_font.render("Spectrum Visualizer", True, MENU_HIGHLIGHT_COLOR)
        title_x = (self.width - title.get_width()) // 2
        menu_surface.blit(title, (title_x, 15))
        
        # Separator line
        pygame.draw.line(
            menu_surface,
            MENU_BORDER_COLOR,
            (20, 45),
            (self.width - 20, 45),
            1
        )
        
        # Menu items
        y_offset = 60
        line_height = 28
        
        for item in self._items:
            # Key indicator
            key_text = self._font.render(f"[{item.key}]", True, MENU_KEY_COLOR)
            menu_surface.blit(key_text, (20, y_offset))
            
            # Label
            label_text = self._font.render(item.label + ":", True, MENU_TEXT_COLOR)
            menu_surface.blit(label_text, (60, y_offset))
            
            # Value
            try:
                value = item.value_getter()
            except Exception:
                value = "?"
            
            if item.multiline:
                # Value on second line, indented
                y_offset += line_height - 6  # Tighter spacing for multiline
                value_text = self._font.render(value, True, MENU_HIGHLIGHT_COLOR)
                menu_surface.blit(value_text, (40, y_offset))
            else:
                # Value on same line, right-aligned
                value_text = self._font.render(value, True, MENU_HIGHLIGHT_COLOR)
                menu_surface.blit(value_text, (self.width - value_text.get_width() - 20, y_offset))
            
            y_offset += line_height
        
        # Slider items
        for slider in self._sliders:
            # Key indicators for decrease/increase
            key_text = self._font.render(f"[{slider.key_decrease}/{slider.key_increase}]", True, MENU_KEY_COLOR)
            menu_surface.blit(key_text, (20, y_offset))
            
            # Label
            label_text = self._font.render(slider.label + ":", True, MENU_TEXT_COLOR)
            menu_surface.blit(label_text, (90, y_offset))
            
            # Value
            try:
                value = slider.value_getter()
            except Exception:
                value = "?"
            value_text = self._font.render(value, True, MENU_HIGHLIGHT_COLOR)
            menu_surface.blit(value_text, (self.width - value_text.get_width() - 20, y_offset))
            
            y_offset += line_height
        
        # Hint at bottom
        hint = self._font.render("Press M or ESC to close", True, (128, 128, 128))
        hint_x = (self.width - hint.get_width()) // 2
        menu_surface.blit(hint, (hint_x, self.height - 30))
        
        # Blit to main surface
        surface.blit(menu_surface, (x, y))
    
    def _render_status(self, surface: pygame.Surface) -> None:
        """Render status message if active."""
        if not self._status_message:
            return
        
        elapsed = time.time() - self._status_time
        if elapsed > self._status_duration:
            self._status_message = ""
            return
        
        self._ensure_fonts()
        
        # Fade out
        alpha = 255
        if elapsed > self._status_duration - 0.5:
            alpha = int(255 * (self._status_duration - elapsed) / 0.5)
        
        # Render text
        text = self._font.render(self._status_message, True, MENU_HIGHLIGHT_COLOR)
        
        # Position at bottom center
        x = (surface.get_width() - text.get_width()) // 2
        y = surface.get_height() - 40
        
        # Background pill
        padding = 10
        bg_rect = pygame.Rect(
            x - padding,
            y - 5,
            text.get_width() + padding * 2,
            text.get_height() + 10
        )
        
        bg_surface = pygame.Surface(bg_rect.size, pygame.SRCALPHA)
        pygame.draw.rect(
            bg_surface,
            (*MENU_BG_COLOR[:3], min(alpha, MENU_BG_COLOR[3])),
            (0, 0, *bg_rect.size),
            border_radius=5
        )
        surface.blit(bg_surface, bg_rect.topleft)
        
        # Text with alpha
        text.set_alpha(alpha)
        surface.blit(text, (x, y))
