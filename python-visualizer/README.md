# Spectrum Visualizer

A real-time audio spectrum visualizer written in Python, featuring WASAPI loopback support for capturing system audio without interrupting playback.

## Features

- 🎵 **Real-time FFT Analysis** - 50-band spectrum visualization
- 🎨 **Two Visualization Modes** - Legacy (original) and Modern (enhanced)
- 🔊 **System Audio Capture** - WASAPI loopback monitoring (Windows)
- 🎯 **Beat Detection** - Visual pulse on bass hits
- ✨ **Ambient Particles** - Floating dot particle system
- 🌈 **Color Cycling** - Rainbow gradient animation
- ⚙️ **Configurable** - CLI options and config file support

## Installation

```bash
# Clone the repository
git clone https://github.com/DrMur/spectrum-visualizer.git
cd spectrum-visualizer/python-visualizer

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows

# Install dependencies
pip install -e .
```

## Usage

### Basic Usage

```bash
# Run with default settings (modern mode)
spectrum-visualizer

# Or run as module
python -m spectrum_visualizer
```

### Command Line Options

```bash
# List available audio devices
spectrum-visualizer --list-devices

# Select specific audio device
spectrum-visualizer --device "Speakers (Realtek)"

# Use legacy visualization mode (original Processing style)
spectrum-visualizer --mode legacy

# Custom window size
spectrum-visualizer --width 1280 --height 400

# Borderless window
spectrum-visualizer --borderless

# All options
spectrum-visualizer --help
```

### Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `M` / `ESC` | Toggle settings menu |
| `D` | Cycle audio devices |
| `V` | Toggle visualization mode |
| `C` | Toggle color cycling |
| `P` | Toggle particles |
| `B` | Toggle borderless |
| `S` | Save settings |
| `Q` | Quit |

## Configuration

Settings are stored in `config.yaml`:

```yaml
audio:
  device: "default"
  sample_rate: 44100
  buffer_size: 4096

visualization:
  mode: "modern"
  width: 800
  height: 300
  fps: 60
  bar_count: 50

colors:
  cycle_speed: 0.02
  background: [0, 0, 0]

particles:
  enabled: true
  count: 100
```

## Visualization Modes

### Legacy Mode
Faithful recreation of the original Processing sketch:
- Same bar positioning and sizing
- Original rise/decay animation algorithm
- Classic color cycling

### Modern Mode
Enhanced visualization with:
- Rounded bar caps with glow effects
- Improved frequency weighting
- Smoother animations
- Gradient background option
- Reflection effects

## OBS Integration

For streaming, add as a **Window Capture** source:
1. Run the visualizer
2. In OBS, add Window Capture source
3. Select "spectrum-visualizer" window
4. Use borderless mode for cleaner capture

## Requirements

- Windows 10/11
- Python 3.10+
- Audio output device (for WASAPI loopback)

## License

MIT License
