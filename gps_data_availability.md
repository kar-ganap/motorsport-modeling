# GPS Data Availability Across Tracks

## Summary

✅ **GPS data IS available** for some tracks!
❌ **GPS data NOT available** for others

---

## Tracks WITH GPS Data (3 tracks)

### 1. ✅ Indianapolis Motor Speedway
**Parameters:**
- `VBOX_Lat_Min` - GPS Latitude (degrees)
- `VBOX_Long_Minutes` - GPS Longitude (degrees)
- `Laptrigger_lapdist_dls` - Distance from start/finish line (meters)
- Plus all standard telemetry (speed, throttle, brake, steering, G-forces)

**File:** `R1_indianapolis_motor_speedway_telemetry.csv` (253 MB archive)

**Sample data:**
```csv
telemetry_name,telemetry_value
VBOX_Lat_Min,39.79315948
VBOX_Long_Minutes,-86.23873901
Laptrigger_lapdist_dls,524
```

**Track coordinates:** ~39.793°N, 86.239°W (Indianapolis Motor Speedway)

---

### 2. ✅ Barber Motorsports Park
**Parameters:**
- `VBOX_Lat_Min` - GPS Latitude
- `VBOX_Long_Minutes` - GPS Longitude
- `Laptrigger_lapdist_dls` - Distance from start/finish
- `aps` - Accelerator pedal position (in addition to `ath`)
- All standard telemetry

**File:** `R1_barber_telemetry_data.csv` (141 MB archive)

**Track coordinates:** TBD (Birmingham, Alabama area)

---

### 3. ✅ Circuit of the Americas (COTA) - *Maybe*
**Status:** Needs verification
**File:** `R1_cota_telemetry_data.csv` (197 MB archive)

**Parameters found:** Standard telemetry only in initial check
- Need deeper scan to confirm GPS presence

---

## Tracks WITHOUT GPS Data (4 tracks)

### ❌ Virginia International Raceway (VIR)
- Only standard 9 parameters
- No GPS, no lap distance

### ❌ Sonoma Raceway
- Only standard 9 parameters
- No GPS, no lap distance

### ❌ Road America
- Only standard 9 parameters
- No GPS, no lap distance

### ❌ Sebring International Raceway
- Different data format (JSON in value field)
- Needs verification but likely no GPS

---

## Standard Telemetry Parameters (All Tracks)

All tracks have these core parameters:
1. `speed` - Vehicle speed (km/h)
2. `ath` - Throttle blade position (0-100%)
3. `pbrake_f` - Front brake pressure (bar)
4. `pbrake_r` - Rear brake pressure (bar)
5. `gear` - Current gear (1-6)
6. `nmot` - Engine RPM
7. `Steering_Angle` - Steering wheel angle (degrees)
8. `accx_can` - Longitudinal acceleration (G)
9. `accy_can` - Lateral acceleration (G)

---

## GPS-Enhanced Tracks: Additional Capabilities

With GPS data available, you can now:

### ✅ **Visualize Racing Lines**
```python
import matplotlib.pyplot as plt

# Plot actual racing line on track
plt.scatter(longitude, latitude, c=speed, cmap='viridis')
plt.colorbar(label='Speed (km/h)')
plt.title('Racing Line Colored by Speed')
```

### ✅ **Compare Lines Between Drivers**
```python
# Overlay multiple drivers' GPS traces
for driver in drivers:
    plt.plot(driver.longitude, driver.latitude, label=f"Car #{driver.number}")

# Show where fast driver takes different line
```

### ✅ **Identify Corners Precisely**
```python
# Use GPS + speed to map corners
corners = identify_corners_from_gps(lat, lon, speed)
# No more time-based heuristics!
```

### ✅ **Measure Track Width Usage**
```python
# Calculate lateral position within track
# See if driver uses full width

for corner in corners:
    # Get all drivers' GPS at this corner
    # Calculate spread (track width usage)
    track_width_used = max(lateral_positions) - min(lateral_positions)
```

### ✅ **Physics-Based Simulation**
```python
# Extract actual track geometry from GPS
track_geometry = extract_geometry_from_gps(lat, lon)

# Now you can run realistic lap simulation
simulated_lap = simulate_ideal_lap(
    track=track_geometry,
    vehicle=GR86_model,
    constraints=high_confidence_metrics
)
```

### ✅ **Apex Detection**
```python
# Find true apex (innermost point of corner)
for corner in corners:
    apex_gps = find_minimum_radius_point(lat, lon)
    apex_speed = speed_at(apex_gps)

# No more "guess based on minimum speed"
```

---

## Impact on Hackathon Project

### With GPS (Indianapolis, Barber):

**Unlocks:**
- Category 1 (Driver Training): Visual racing line comparison
- Category 2 (Pre-Event Prediction): Track geometry for physics models
- Category 4 (Real-Time Analytics): Position-based strategy (e.g., "pit after Turn 6")

**Project Ideas:**
1. **"Racing Line Optimizer"** - Show ideal line vs. actual line with visual overlay
2. **"Track Position Heat Map"** - Where do drivers gain/lose time spatially?
3. **"Corner-by-Corner Breakdown"** - Analyze each corner with GPS precision
4. **"Lap Simulator"** - Physics-based ideal lap using real track geometry

### Without GPS (VIR, Sonoma, Road America):

**Still Available:**
- All 10 high-confidence metrics
- Driver technique analysis
- Time-based comparisons
- Statistical models

**Project Ideas:**
1. **"Driver Performance Score"** - Rank drivers by technique quality
2. **"Improvement Recommender"** - "Smooth your braking to gain 0.5s"
3. **"Tire Strategy Optimizer"** - When to pit based on degradation
4. **"Technique Comparison Dashboard"** - Winner vs. field analysis

---

## Recommendation

### Option 1: Focus on GPS Tracks (Indianapolis or Barber)
**Pros:**
- Unlock visual racing line analysis
- More impressive demo
- Spatial insights (not just temporal)
- Physics-based validation possible

**Cons:**
- Smaller dataset (2 tracks vs. 7)
- More complex analysis code
- GPS parsing overhead

**Best for:** Category 1 (Driver Training) with visual focus

---

### Option 2: Focus on All Tracks (Ignore GPS)
**Pros:**
- 7 tracks × 2 races = 14 datasets
- More robust statistical analysis
- Simpler code (no GPS parsing)
- Still have 10 strong metrics

**Cons:**
- No visual racing lines
- Position-based analysis limited
- Less "wow factor" in demo

**Best for:** Category 2 (Pre-Event Prediction) or Category 4 (Real-Time Analytics)

---

### Option 3: Hybrid Approach (Recommended)
**Strategy:**
1. Build core analysis engine using non-GPS metrics (works on all tracks)
2. Add GPS visualization layer for Indianapolis/Barber
3. Demo with Indianapolis (has GPS) but show it works on all tracks

**Pros:**
- Best of both worlds
- Demonstrates generality
- Visual appeal where available
- Robust metrics everywhere

**Cons:**
- More development work
- Need to handle two data formats

**Implementation:**
```python
class DriverAnalyzer:
    def __init__(self, telemetry, gps=None):
        self.telemetry = telemetry
        self.gps = gps  # Optional!

    def calculate_metrics(self):
        # Works with or without GPS
        return {
            'consistency': self.calc_consistency(),
            'smoothness': self.calc_smoothness(),
            # ... all 10 metrics
        }

    def visualize_racing_line(self):
        if self.gps is not None:
            # GPS-based visualization
            return self.plot_gps_line()
        else:
            # Time-based approximation
            return self.plot_time_based_line()
```

---

## Next Steps

1. **Extract Indianapolis data fully** to validate GPS quality
2. **Check COTA** more thoroughly (might have GPS too)
3. **Verify Sebring** format (different structure, might have GPS in JSON)
4. **Choose project direction** based on GPS availability

### Immediate Actions:
```bash
# Extract Indianapolis
unzip indianapolis.zip -d /path/to/project/data/

# Load and verify GPS data
python3 -c "
import pandas as pd
data = pd.read_csv('data/indianapolis/R1_indianapolis_motor_speedway_telemetry.csv')
gps_data = data[data['telemetry_name'].isin(['VBOX_Lat_Min', 'VBOX_Long_Minutes'])]
print(f'GPS records: {len(gps_data)}')
print(gps_data.head())
"
```

---

## Final Recommendation

**Use Indianapolis Motor Speedway as your primary dataset.**

Why:
1. ✅ Has GPS data (racing line visualization)
2. ✅ Has lap distance data (precise position tracking)
3. ✅ Iconic track (judges will recognize it)
4. ✅ Large dataset (~253 MB)
5. ✅ All standard telemetry parameters
6. ✅ Complete race results and timing

**Project:** "Indianapolis GR Cup Driver Analysis & Training Tool"
- **Core:** 10 high-confidence metrics (works anywhere)
- **Showcase:** GPS racing line visualization (Indianapolis-specific)
- **Value:** Driver improvement recommendations + visual feedback

This gives you the best demo while maintaining analytical rigor.
