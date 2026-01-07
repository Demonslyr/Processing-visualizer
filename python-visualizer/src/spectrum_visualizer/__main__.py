"""
Entry point for spectrum visualizer.

Allows running as: python -m spectrum_visualizer
"""

from __future__ import annotations

import logging
import sys

from spectrum_visualizer.audio.devices import DeviceManager
from spectrum_visualizer.config.cli import parse_args, apply_args_to_settings
from spectrum_visualizer.config.persistence import load_config, save_config
from spectrum_visualizer.config.settings import Settings
from spectrum_visualizer.app import SpectrumVisualizer


def setup_logging(verbose: bool = False, debug: bool = False) -> None:
    """Configure logging."""
    level = logging.DEBUG if debug else (logging.INFO if verbose else logging.WARNING)
    
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def list_devices() -> None:
    """List available audio devices and exit."""
    manager = DeviceManager()
    print(manager.list_devices())


def main(argv: list[str] | None = None) -> int:
    """
    Main entry point.
    
    Args:
        argv: Command-line arguments (None for sys.argv)
        
    Returns:
        Exit code
    """
    # Parse arguments
    args = parse_args(argv)
    
    # Setup logging
    setup_logging(verbose=args.verbose, debug=args.debug)
    logger = logging.getLogger(__name__)
    
    # Handle --list-devices
    if args.list_devices:
        list_devices()
        return 0
    
    # Load configuration
    settings = load_config(args.config)
    
    # Apply command-line overrides
    settings = apply_args_to_settings(args, settings)
    
    # Handle --save-config
    if args.save_config:
        if save_config(settings, args.config):
            print(f"Configuration saved")
            return 0
        else:
            print("Failed to save configuration", file=sys.stderr)
            return 1
    
    # Run visualizer
    try:
        logger.info(f"Starting in {settings.visualization.mode} mode")
        
        visualizer = SpectrumVisualizer(settings)
        visualizer.run()
        
        return 0
        
    except KeyboardInterrupt:
        logger.info("Interrupted")
        return 0
    except Exception as e:
        logger.exception(f"Error: {e}")
        print(f"Error: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
