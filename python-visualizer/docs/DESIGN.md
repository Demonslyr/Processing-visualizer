# Audio Spectrum Visualizer - Design Document

## 1. Original Application Analysis

### 1.1 Core Features Identified
From the Processing sketch analysis:

| Feature | Implementation Details |
|---------|----------------------|
| **Audio Input** | Minim `getLineIn()` - mono, 4096 buffer |
| **FFT Analysis** | 56 frequency bands (logarithmically spaced from 1Hz to 17.8kHz) |
| **Beat Detection** | 20ms sensitivity, onset detection |
| **Bar Visualizer** | 50 bars with smooth rise/decay animation |
| **Ambient Dots** | 100 floating particles for atmosphere |
| **Color Cycling** | Rainbow gradient using sine waves (RGB phase offset) |
| **Frame Rate** | Target 240fps |
| **Window Size** | 800x300 pixels |

### 1.2 Bar Animation Algorithm
```
On each frame:
  - If new_height > current_height * 2.5:
      current_height += 0.01 * new_height + beat_boost
  - Else:
      current_height *= 0.985 (decay factor)
  - Minimum height: 6px
```

### 1.3 Frequency Band Mapping
Logarithmic distribution weighted toward bass frequencies:
- Bands 0-10: 1-45 Hz (sub-bass to bass)
- Bands 11-20: 55-160 Hz (bass to low-mid)
- Bands 21-35: 200-1280 Hz (mid)
- Bands 36-50: 1600-17800 Hz (high-mid to presence)

---

## 2. Feature Requirements

### 2.1 Must Have (Parity)
- [x] Real-time audio capture from system audio endpoint
- [x] FFT analysis with configurable buffer size
- [x] 50-bar spectrum visualization
- [x] Smooth bar animation (rise/decay)
- [x] Beat detection with visual feedback
- [x] Floating ambient particles
- [x] Rainbow color cycling
- [x] Configurable window size
- [x] Audio passthrough (captured audio continues to output device)

### 2.2 Should Have (Improvements)
- [x] Audio device selection (list and choose endpoints)
- [x] Two visualization modes: "legacy" and "modern"
- [x] Command-line configuration
- [x] Temporary on-screen menu (auto-hide)
- [x] Configuration persistence
- [x] Borderless/transparent window option

### 2.3 Nice to Have
- [ ] Multiple visualizer styles
- [ ] Custom color themes
- [ ] Audio reactivity tuning sliders
- [ ] Recording/screenshot capability

---

## 3. Architecture Design

### 3.1 High-Level Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    Main Application                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Audio      │  │   Analysis   │  │  Renderer    │       │
│  │   Capture    │──▶│   Engine     │──▶│  (Pygame)   │       │
│  │   (WASAPI)   │  │   (FFT+Beat) │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                                    │               │
│         ▼                                    ▼               │
│  ┌──────────────┐                    ┌──────────────┐       │
│  │   Device     │                    │   UI/Menu    │       │
│  │   Manager    │                    │   Overlay    │       │
│  └──────────────┘                    └──────────────┘       │
├─────────────────────────────────────────────────────────────┤
│                    Configuration Layer                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │    CLI       │  │   Config     │  │   Logging    │       │
│  │   Parser     │  │   Manager    │  │              │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Module Responsibilities

#### `audio/capture.py`
- WASAPI loopback audio capture
- Device enumeration and selection
- Audio stream management
- Passthrough handling (no interference with output)

#### `audio/analysis.py`
- FFT computation with NumPy
- Frequency band extraction
- Beat detection algorithm
- Smoothing and normalization

#### `visualization/base.py`
- Abstract renderer interface
- Common utilities (color math, interpolation)

#### `visualization/legacy.py`
- Exact replication of original Processing behavior
- Same bar animation algorithm
- Same color cycling

#### `visualization/modern.py`
- Improved aesthetics
- Better frequency weighting
- Glow effects, rounded bars
- Smoother animations

#### `ui/menu.py`
- Temporary overlay menu
- Device selection
- Mode switching
- Auto-hide after timeout

#### `config/`
- CLI argument parsing
- YAML/JSON configuration file
- Settings persistence

---

## 4. Visualization Modes

### 4.1 Legacy Mode (`--mode legacy`)
Faithful recreation of original:
- Exact bar positioning: `x = i*13 + 100`
- Same rise/decay algorithm
- Same color cycling formula
- Same dot particle system
- Black background with white line

### 4.2 Modern Mode (`--mode modern`)
Enhanced version:
- Rounded bar caps
- Glow/bloom effect on bars
- Improved frequency weighting (A-weighting curve)
- Smoother color transitions
- Gradient backgrounds
- Reflection effect below bars

---

## 5. Audio Device Handling

### 5.1 WASAPI Loopback (Windows)
```python
# Using sounddevice with WASAPI
import sounddevice as sd

# List loopback devices
devices = sd.query_devices()
loopback_devices = [d for d in devices if 'loopback' in d['name'].lower()]

# Capture without interrupting output
stream = sd.InputStream(
    device=device_id,
    channels=1,
    samplerate=44100,
    blocksize=4096,
    dtype='float32'
)
```

### 5.2 Passthrough Guarantee
- WASAPI loopback is read-only monitoring
- Does NOT intercept or modify audio stream
- Original audio continues to output device unchanged

---

## 6. Configuration Schema

```yaml
# config.yaml
audio:
  device: "default"  # or device name/id
  sample_rate: 44100
  buffer_size: 4096
  channels: 1

visualization:
  mode: "modern"  # "legacy" or "modern"
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

---

## 7. CLI Interface

```bash
# Basic usage
python -m spectrum_visualizer

# Legacy mode
python -m spectrum_visualizer --mode legacy

# Select specific audio device
python -m spectrum_visualizer --device "Speakers (Realtek)"

# List available devices
python -m spectrum_visualizer --list-devices

# Custom window size
python -m spectrum_visualizer --width 1280 --height 400

# Borderless window
python -m spectrum_visualizer --borderless
```

---

## 8. Menu System

### 8.1 Activation
- Press `M` or `ESC` to toggle menu
- Auto-hides after 5 seconds of inactivity
- Semi-transparent overlay

### 8.2 Menu Options
```
┌─────────────────────────────┐
│  Spectrum Visualizer        │
├─────────────────────────────┤
│  [D] Audio Device: Speakers │
│  [V] Mode: Modern           │
│  [C] Color Cycle: On        │
│  [P] Particles: On          │
│  [B] Borderless: Off        │
│  [S] Save Settings          │
│  [Q] Quit                   │
└─────────────────────────────┘
```
