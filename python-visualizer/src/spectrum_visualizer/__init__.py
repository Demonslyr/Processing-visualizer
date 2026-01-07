"""
Spectrum Visualizer - Real-time audio spectrum visualization.

A Python application for visualizing audio spectrum in real-time,
supporting WASAPI loopback for system audio capture on Windows.
"""

__version__ = "1.0.0"
__author__ = "DrMur"

from spectrum_visualizer.app import SpectrumVisualizer

__all__ = ["SpectrumVisualizer", "__version__"]
