# Legacy vs Modern Mode Comparison

A detailed breakdown of the algorithmic and visual differences between the two visualization modes.

---

## 📊 Frequency Band Analysis

### Legacy Mode (Your Original Algorithm)
Your Processing sketch uses a **hand-crafted frequency array** with 56 values:

```
{1, 3, 5, 10, 16, 22, 26, 31, 39, 42, 45, 55, 60, 65, 70, 80, 90, 100, 
 120, 140, 160, 200, 240, 280, 320, 400, 480, 560, 590, 640, 720, 800, 
 960, 1024, 1120, 1280, 1600, 1920, 2240, 2560, 3200, 3340, 3590, 3720, 
 3840, 4480, 5120, 6400, 7680, 8960, 10240, 12800, 15360, 15360, 15360, 17800}
```

**Characteristics:**
- Dense sampling in bass frequencies (1-100 Hz) - **18 frequency points**
- Gradual spread through mids (100-1000 Hz) - **15 frequency points**
- Wider spacing in highs (1000+ Hz) - **23 frequency points**
- Plateau at 15360 Hz (repeated 3x) - interesting quirk!

**FFT Sampling Method:**
```java
// Original Processing code
sqrt(((fft.getFreq(freq[g+1]) + 2*fft.getFreq(freq[g+2]) + fft.getFreq(freq[g+3]))/4) * 15 * ((k/25)+0.8))
```

This takes 3 frequency bins with **center-weighted averaging** (1:2:1 ratio), applies sqrt compression, then scales by `15 * ((bar_index/25) + 0.8)`.

### Modern Mode (New Algorithm)
Uses **mathematically-derived logarithmic bands**:

```python
# Compute log-spaced frequency boundaries
min_freq, max_freq = 20, 20000  # Human hearing range
log_min, log_max = np.log10(min_freq), np.log10(max_freq)
band_edges = np.logspace(log_min, log_max, num_bands + 1)
```

**Characteristics:**
- True logarithmic distribution matching human perception
- Equal perceptual spacing (each octave gets similar visual weight)
- Proper bin aggregation (sums energy across entire band, not just 3 points)

**A-Weighting Curve:**
Modern mode applies the A-weighting curve to match human hearing sensitivity:
- Attenuates very low frequencies (<200 Hz) that we're less sensitive to
- Boosts mid frequencies (1-4 kHz) where hearing is most sensitive
- Rolls off extreme highs

---

## 🎬 Bar Animation

### Legacy Mode (Your Settings)
```yaml
amplitude_scale: 17      # FFT magnitude multiplier
growth_rate: 0.028       # How fast bars rise per frame
decay_rate: 0.05         # How fast bars fall per frame  
trigger_threshold: 4.0   # Min amplitude delta to trigger growth
```

**Animation Logic:**
```python
if new_height > current_height + trigger_threshold:
    # Start growing toward new_height
    target = new_height
    current += growth_rate * (target - current)
else:
    # Decay toward zero
    current -= decay_rate * current
```

**Your Tuning Philosophy:**
- **High decay (0.05)** = Snappy, punchy response - bars drop quickly
- **High growth (0.028)** = Fast attack on transients
- **High threshold (4.0)** = Only significant amplitude changes trigger growth (reduces noise)
- **Amp 17** = Moderate boost, prevents clipping on loud passages

### Modern Mode Defaults
```yaml
amplitude_scale: 15
growth_rate: 0.01        # Slower, smoother rise
decay_rate: 0.015        # Gentler fall
trigger_threshold: 2.5   # More sensitive to changes
```

**Result:** Smoother, more flowing animation vs your punchy/reactive style.

---

## 🎨 Visual Rendering

### Legacy Mode
| Feature | Implementation |
|---------|---------------|
| **Bar Shape** | Sharp rectangles |
| **Color** | Rainbow HSB cycle based on bar index |
| **Spacing** | Fixed 3px gap |
| **Effects** | None (pure bars) |

**Color Formula:**
```java
colorMode(HSB, 50, 100, 100);
fill(k, 100, 100);  // k = bar index (0-49), maps directly to hue
```

### Modern Mode
| Feature | Implementation |
|---------|---------------|
| **Bar Shape** | Rounded rectangles with circular caps |
| **Color** | Gradient with glow effect |
| **Spacing** | Calculated proportionally |
| **Effects** | Reflection, glow, particles |

**Reflection Effect:**
```python
# Draw mirrored, faded copy below bars
reflection_alpha = 0.3
reflection_height = bar_height * 0.4
# Gradient fade from bar bottom downward
```

**Particle System:**
- Spawns particles on beat detection
- Particles have velocity, gravity, and fade
- Color matches the bar that spawned them

---

## 📈 Comparison Table

| Aspect | Legacy | Modern |
|--------|--------|--------|
| **Frequency Distribution** | Hand-tuned array (bass-heavy) | Log-scale (perceptually even) |
| **FFT Sampling** | 3-point weighted average | Full band energy summation |
| **Perceptual Weighting** | None | A-weighting curve |
| **Bar Animation** | Punchy (your tuning) | Smooth (default) |
| **Visual Style** | Clean, retro | Polished, modern |
| **Effects** | None | Reflection, glow, particles |
| **CPU Usage** | Lower | Slightly higher |

---

## 🔧 Why Your Settings Feel "Right"

Your tuned parameters create a **high-contrast, rhythmically accurate** visualization:

1. **High decay (0.05)** prevents "muddy" sustained bars - they snap back fast
2. **High threshold (4.0)** filters out small fluctuations - only real beats trigger movement
3. **Fast growth (0.028)** means transients (kicks, snares) immediately shoot up
4. **The combination** creates clear visual separation between beats

This is particularly effective for:
- EDM / electronic music with clear transients
- Hip-hop with punchy drums
- Any genre with distinct rhythmic elements

The modern mode defaults are tuned for **smoother, ambient visualization** - better for:
- Orchestral / classical
- Ambient / atmospheric
- Continuous synth pads

---

## 🎛️ Recommended Preset Configs

### "Punchy EDM" (Your Config)
```yaml
bar_animation:
  amplitude_scale: 17
  growth_rate: 0.028
  decay_rate: 0.05
  trigger_threshold: 4.0
```

### "Smooth Ambient"
```yaml
bar_animation:
  amplitude_scale: 12
  growth_rate: 0.008
  decay_rate: 0.01
  trigger_threshold: 1.5
```

### "Aggressive Metal"
```yaml
bar_animation:
  amplitude_scale: 25
  growth_rate: 0.04
  decay_rate: 0.06
  trigger_threshold: 3.0
```

### "Chill Lofi"
```yaml
bar_animation:
  amplitude_scale: 10
  growth_rate: 0.005
  decay_rate: 0.008
  trigger_threshold: 2.0
```

---

## 💡 Future Ideas

- [ ] Preset save/load system with hotkeys
- [ ] Per-frequency-band color customization
- [ ] Beat-reactive background effects
- [ ] Waveform overlay option
- [ ] Stereo separation visualization (L/R channels)
