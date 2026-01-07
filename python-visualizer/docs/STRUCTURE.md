# Spectrum Visualizer - Project Structure

```
python-visualizer/
├── pyproject.toml              # Modern Python packaging
├── README.md                   # User documentation
├── requirements.txt            # Dependencies
├── config.yaml                 # Default configuration
│
├── docs/
│   ├── DESIGN.md              # This design document
│   └── API.md                 # Internal API documentation
│
├── src/
│   └── spectrum_visualizer/
│       ├── __init__.py        # Package init, version
│       ├── __main__.py        # Entry point for `python -m`
│       ├── app.py             # Main application class
│       │
│       ├── audio/
│       │   ├── __init__.py
│       │   ├── capture.py     # WASAPI audio capture
│       │   ├── devices.py     # Device enumeration
│       │   └── analysis.py    # FFT, beat detection
│       │
│       ├── visualization/
│       │   ├── __init__.py
│       │   ├── base.py        # Abstract renderer
│       │   ├── legacy.py      # Original Processing style
│       │   ├── modern.py      # Enhanced visualizer
│       │   └── particles.py   # Floating dots system
│       │
│       ├── ui/
│       │   ├── __init__.py
│       │   ├── window.py      # Pygame window management
│       │   └── menu.py        # Overlay menu system
│       │
│       └── config/
│           ├── __init__.py
│           ├── cli.py         # Argument parsing
│           ├── settings.py    # Configuration dataclass
│           └── persistence.py # Save/load config
│
└── tests/
    ├── __init__.py
    ├── test_audio.py
    ├── test_analysis.py
    └── test_visualization.py
```

## File Responsibilities

### Core Files

| File | Purpose |
|------|---------|
| `__main__.py` | CLI entry, bootstraps app |
| `app.py` | Main loop, coordinates modules |

### Audio Module

| File | Purpose |
|------|---------|
| `capture.py` | `AudioCapture` class - stream management |
| `devices.py` | `DeviceManager` - enumerate, select devices |
| `analysis.py` | `AudioAnalyzer` - FFT, bands, beat detection |

### Visualization Module

| File | Purpose |
|------|---------|
| `base.py` | `BaseRenderer` ABC, color utilities |
| `legacy.py` | `LegacyRenderer` - exact Processing clone |
| `modern.py` | `ModernRenderer` - enhanced version |
| `particles.py` | `ParticleSystem` - ambient dots |

### UI Module

| File | Purpose |
|------|---------|
| `window.py` | `Window` - Pygame surface, events |
| `menu.py` | `OverlayMenu` - temporary settings UI |

### Config Module

| File | Purpose |
|------|---------|
| `cli.py` | `parse_args()` - argparse setup |
| `settings.py` | `Settings` dataclass with defaults |
| `persistence.py` | YAML load/save functions |
