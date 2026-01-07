"""
Configuration file persistence using YAML.

Handles loading and saving configuration files and presets.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

import yaml

from spectrum_visualizer.config.settings import Settings, BarAnimationSettings

logger = logging.getLogger(__name__)

# Default config file locations
DEFAULT_CONFIG_NAME = "config.yaml"
PRESETS_DIR_NAME = "presets"


def get_app_dir() -> Path:
    """Get the application directory, handling frozen executables."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return Path(sys.executable).parent
    else:
        # Running as script - go up from persistence.py to python-visualizer root
        return Path(__file__).parent.parent.parent.parent


def get_presets_dir() -> Path:
    """Get the presets directory, creating it if needed."""
    presets_dir = get_app_dir() / PRESETS_DIR_NAME
    presets_dir.mkdir(parents=True, exist_ok=True)
    return presets_dir


def get_config_path(custom_path: Optional[str] = None) -> Path:
    """
    Get the configuration file path.
    
    Args:
        custom_path: Optional custom path to config file
        
    Returns:
        Path to configuration file
    """
    if custom_path:
        return Path(custom_path)
    
    # For frozen app, look next to the executable
    app_dir = get_app_dir()
    app_config = app_dir / DEFAULT_CONFIG_NAME
    if app_config.exists():
        return app_config
    
    # Look in current directory
    local_config = Path.cwd() / DEFAULT_CONFIG_NAME
    if local_config.exists():
        return local_config
    
    # Default to app directory for new config (so it saves next to exe)
    return app_config


def load_config(path: Optional[str | Path] = None) -> Settings:
    """
    Load settings from configuration file.
    
    Args:
        path: Path to config file (optional)
        
    Returns:
        Settings object (defaults if file not found)
    """
    config_path = get_config_path(str(path) if path else None)
    
    if not config_path.exists():
        logger.info(f"Config file not found at {config_path}, using defaults")
        return Settings.create_default()
    
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if data is None:
            logger.warning(f"Empty config file at {config_path}, using defaults")
            return Settings.create_default()
        
        settings = Settings.from_dict(data)
        logger.info(f"Loaded configuration from {config_path}")
        return settings
        
    except yaml.YAMLError as e:
        logger.error(f"Error parsing config file {config_path}: {e}")
        return Settings.create_default()
    except Exception as e:
        logger.error(f"Error loading config file {config_path}: {e}")
        return Settings.create_default()


def save_config(settings: Settings, path: Optional[str | Path] = None) -> bool:
    """
    Save settings to configuration file.
    
    Args:
        settings: Settings to save
        path: Path to save to (optional)
        
    Returns:
        True if successful, False otherwise
    """
    config_path = get_config_path(str(path) if path else None)
    
    try:
        # Ensure parent directory exists
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert to dict and save
        data = settings.to_dict()
        
        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Saved configuration to {config_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving config file {config_path}: {e}")
        return False


# =============================================================================
# Preset Management
# =============================================================================

def list_presets() -> list[str]:
    """
    List all available preset names.
    
    Returns:
        List of preset names (without .yaml extension)
    """
    presets_dir = get_presets_dir()
    presets = []
    
    for f in presets_dir.glob("*.yaml"):
        presets.append(f.stem)
    
    return sorted(presets)


def save_preset(name: str, bar_animation: BarAnimationSettings) -> bool:
    """
    Save current bar animation settings as a named preset.
    
    Args:
        name: Preset name (will be sanitized for filesystem)
        bar_animation: Bar animation settings to save
        
    Returns:
        True if successful
    """
    # Sanitize name for filesystem
    safe_name = "".join(c for c in name if c.isalnum() or c in "._- ").strip()
    if not safe_name:
        safe_name = "preset"
    
    preset_path = get_presets_dir() / f"{safe_name}.yaml"
    
    try:
        data = {
            "name": name,
            "bar_animation": {
                "amplitude_scale": bar_animation.amplitude_scale,
                "growth_rate": bar_animation.growth_rate,
                "decay_rate": bar_animation.decay_rate,
                "trigger_threshold": bar_animation.trigger_threshold,
            }
        }
        
        with open(preset_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, default_flow_style=False)
        
        logger.info(f"Saved preset '{name}' to {preset_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error saving preset '{name}': {e}")
        return False


def load_preset(name: str) -> Optional[BarAnimationSettings]:
    """
    Load a preset by name.
    
    Args:
        name: Preset name
        
    Returns:
        BarAnimationSettings if found, None otherwise
    """
    preset_path = get_presets_dir() / f"{name}.yaml"
    
    if not preset_path.exists():
        logger.warning(f"Preset '{name}' not found")
        return None
    
    try:
        with open(preset_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        
        if not data or "bar_animation" not in data:
            logger.warning(f"Invalid preset file: {preset_path}")
            return None
        
        ba = data["bar_animation"]
        settings = BarAnimationSettings(
            amplitude_scale=ba.get("amplitude_scale", 15.0),
            growth_rate=ba.get("growth_rate", 0.01),
            decay_rate=ba.get("decay_rate", 0.015),
            trigger_threshold=ba.get("trigger_threshold", 2.5),
        )
        
        logger.info(f"Loaded preset '{name}'")
        return settings
        
    except Exception as e:
        logger.error(f"Error loading preset '{name}': {e}")
        return None


def delete_preset(name: str) -> bool:
    """
    Delete a preset by name.
    
    Args:
        name: Preset name
        
    Returns:
        True if deleted successfully
    """
    preset_path = get_presets_dir() / f"{name}.yaml"
    
    if not preset_path.exists():
        return False
    
    try:
        preset_path.unlink()
        logger.info(f"Deleted preset '{name}'")
        return True
    except Exception as e:
        logger.error(f"Error deleting preset '{name}': {e}")
        return False


# Create default presets on first run
def create_default_presets() -> None:
    """Create built-in preset files if they don't exist."""
    presets_dir = get_presets_dir()
    
    default_presets = {
        "Auto": BarAnimationSettings(
            amplitude_scale=0,  # Sentinel: use original hardcoded behavior
            growth_rate=0.01,   # Ignored in Auto mode
            decay_rate=0.015,   # Ignored in Auto mode
            trigger_threshold=0,  # Ignored in Auto mode
        ),
        "Punchy EDM": BarAnimationSettings(
            amplitude_scale=17,
            growth_rate=0.028,
            decay_rate=0.05,
            trigger_threshold=4.0,
        ),
        "Smooth Ambient": BarAnimationSettings(
            amplitude_scale=12,
            growth_rate=0.008,
            decay_rate=0.01,
            trigger_threshold=1.5,
        ),
        "Aggressive Metal": BarAnimationSettings(
            amplitude_scale=25,
            growth_rate=0.04,
            decay_rate=0.06,
            trigger_threshold=3.0,
        ),
        "Chill Lofi": BarAnimationSettings(
            amplitude_scale=10,
            growth_rate=0.005,
            decay_rate=0.008,
            trigger_threshold=2.0,
        ),
        "Balanced": BarAnimationSettings(
            amplitude_scale=15,
            growth_rate=0.01,
            decay_rate=0.015,
            trigger_threshold=2.5,
        ),
    }
    
    for name, settings in default_presets.items():
        preset_path = presets_dir / f"{name}.yaml"
        if not preset_path.exists():
            save_preset(name, settings)
