"""
Command-line argument parsing.

Provides the CLI interface for the spectrum visualizer.
"""

from __future__ import annotations

import argparse
from typing import Optional

from spectrum_visualizer.config.settings import Settings


def parse_args(args: Optional[list[str]] = None) -> argparse.Namespace:
    """
    Parse command-line arguments.
    
    Args:
        args: Arguments to parse (None for sys.argv)
        
    Returns:
        Parsed arguments namespace
    """
    parser = argparse.ArgumentParser(
        prog="spectrum-visualizer",
        description="Real-time audio spectrum visualizer with WASAPI loopback support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          Run with default settings (modern mode)
  %(prog)s --mode legacy            Use original Processing-style visualization
  %(prog)s --list-devices           Show available audio devices
  %(prog)s --device "Speakers"      Capture from specific audio device
  %(prog)s --width 1280 --height 400  Custom window size
  %(prog)s --borderless             Borderless window for streaming

Keyboard Shortcuts (while running):
  M / ESC    Toggle settings menu
  D          Cycle audio devices
  V          Toggle visualization mode
  C          Toggle color cycling
  P          Toggle particles
  S          Save settings
  Q          Quit
        """,
    )
    
    # Device options
    device_group = parser.add_argument_group("Audio Device")
    device_group.add_argument(
        "--list-devices",
        action="store_true",
        help="List available audio devices and exit",
    )
    device_group.add_argument(
        "-d", "--device",
        type=str,
        default=None,
        metavar="NAME",
        help="Audio device name or index (default: auto-detect loopback)",
    )
    
    # Visualization options
    vis_group = parser.add_argument_group("Visualization")
    vis_group.add_argument(
        "-m", "--mode",
        choices=["legacy", "modern"],
        default=None,
        help="Visualization mode (default: modern)",
    )
    vis_group.add_argument(
        "--bars",
        type=int,
        default=None,
        metavar="N",
        help="Number of frequency bars (default: 50)",
    )
    vis_group.add_argument(
        "--fps",
        type=int,
        default=None,
        help="Target frame rate (default: 60)",
    )
    vis_group.add_argument(
        "--no-particles",
        action="store_true",
        help="Disable ambient particle effects",
    )
    vis_group.add_argument(
        "--no-colors",
        action="store_true",
        help="Disable color cycling",
    )
    
    # Window options
    window_group = parser.add_argument_group("Window")
    window_group.add_argument(
        "-W", "--width",
        type=int,
        default=None,
        help="Window width in pixels (default: 800)",
    )
    window_group.add_argument(
        "-H", "--height",
        type=int,
        default=None,
        help="Window height in pixels (default: 300)",
    )
    window_group.add_argument(
        "--borderless",
        action="store_true",
        help="Use borderless window",
    )
    window_group.add_argument(
        "--always-on-top",
        action="store_true",
        help="Keep window on top of other windows",
    )
    
    # Config options
    config_group = parser.add_argument_group("Configuration")
    config_group.add_argument(
        "-c", "--config",
        type=str,
        default=None,
        metavar="FILE",
        help="Path to configuration file",
    )
    config_group.add_argument(
        "--save-config",
        action="store_true",
        help="Save current settings to config file and exit",
    )
    
    # Debug options
    debug_group = parser.add_argument_group("Debug")
    debug_group.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )
    debug_group.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode",
    )
    
    return parser.parse_args(args)


def apply_args_to_settings(args: argparse.Namespace, settings: Settings) -> Settings:
    """
    Apply command-line arguments to settings.
    
    Args:
        args: Parsed arguments
        settings: Base settings to modify
        
    Returns:
        Modified settings
    """
    # Audio
    if args.device is not None:
        settings.audio.device = args.device
    
    # Visualization
    if args.mode is not None:
        settings.visualization.mode = args.mode
    if args.bars is not None:
        settings.visualization.bar_count = args.bars
    if args.fps is not None:
        settings.visualization.fps = args.fps
    if args.no_particles:
        settings.particles.enabled = False
    if args.no_colors:
        settings.colors.enabled = False
    
    # Window
    if args.width is not None:
        settings.visualization.width = args.width
    if args.height is not None:
        settings.visualization.height = args.height
    if args.borderless:
        settings.window.borderless = True
    if args.always_on_top:
        settings.window.always_on_top = True
    
    return settings
