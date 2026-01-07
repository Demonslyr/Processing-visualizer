"""
Configuration file persistence using YAML.

Handles loading and saving configuration files.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml

from spectrum_visualizer.config.settings import Settings

logger = logging.getLogger(__name__)

# Default config file locations
DEFAULT_CONFIG_NAME = "config.yaml"


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
    
    # Look in current directory first
    local_config = Path.cwd() / DEFAULT_CONFIG_NAME
    if local_config.exists():
        return local_config
    
    # Then app directory
    app_config = Path(__file__).parent.parent.parent.parent / DEFAULT_CONFIG_NAME
    if app_config.exists():
        return app_config
    
    # Default to current directory for new config
    return local_config


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
