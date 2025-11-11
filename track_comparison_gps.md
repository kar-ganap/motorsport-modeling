# GPS-Enabled Tracks: Detailed Comparison

## Executive Summary

✅ **2 tracks confirmed with GPS data:**
1. Indianapolis Motor Speedway
2. Barber Motorsports Park

❌ **Confirmed NO GPS:**
- COTA (Circuit of the Americas)
- Sebring
- VIR, Sonoma, Road America

---

## Track-by-Track Breakdown

### 🏁 Indianapolis Motor Speedway (RECOMMENDED)

**Location:** Speedway, Indiana
**Track Length:** ~4.05 km (2.5 miles) - Road Course
**Famous for:** Home of the Indy 500, iconic oval + road course

#### Data Overview
| Metric | Race 1 | Race 2 | Total |
|--------|--------|--------|-------|
| Telemetry rows | 21.4M | 23.1M | 44.5M |
| GPS records (lat+long) | 4.47M | ~4.8M | ~9.3M |
| Cars finished | 19 | TBD | ~19 |
| Laps completed | 26 | ~26 | ~52 |

#### Race 1 Winner
- **Driver:** Spike Kohlbecker (#55)
- **Margin:** 0.170s (incredibly close!)
- **Laps:** 26
- **Fastest lap:** 1:39.748 (141.7 km/h avg)
- **Total race time:** 46:41.553

#### Telemetry Parameters (12 total)
**Standard (9):**
- speed, ath, pbrake_f, pbrake_r, gear, nmot, Steering_Angle, accx_can, accy_can

**GPS-Enhanced (3):**
- `VBOX_Lat_Min` - GPS Latitude
- `VBOX_Long_Minutes` - GPS Longitude
- `Laptrigger_lapdist_dls` - Distance from start/finish line
- `aps` - Accelerator pedal position (alternative to ath)

#### Data Quality
- ✅ High GPS coverage: 4.47M GPS points across 21.4M telemetry samples = ~21% of samples have GPS
- ✅ Lap distance tracking available (precise position on track)
- ✅ Complete race results with detailed standings
- ✅ Both races available
- ✅ Large field (19+ cars)

#### Pros
1. **Iconic track** - Judges will instantly recognize it
2. **Largest dataset** - 44.5M total telemetry points
3. **Best GPS coverage** - 9.3M GPS samples
4. **Competitive racing** - Winner by 0.17s!
5. **Complete metadata** - Driver names, teams, times
6. **Road course configuration** - More interesting than oval (multiple corner types)

#### Cons
1. Slightly longer to process (larger file size)
2. Track layout is complex (might need external map reference)

---

### 🏁 Barber Motorsports Park

**Location:** Birmingham, Alabama
**Track Length:** ~3.7 km (2.3 miles)
**Famous for:** Beautiful, technical road course; "Augusta of motorsports"

#### Data Overview
| Metric | Race 1 | Race 2 | Total |
|--------|--------|--------|-------|
| Telemetry rows | 11.6M | 11.7M | 23.3M |
| GPS records (lat+long) | 2.41M | ~2.45M | ~4.9M |
| Cars finished | 20 | ~20 | ~40 |
| Laps completed | TBD | TBD | TBD |

#### Telemetry Parameters (12 total)
**Standard (9):** Same as Indianapolis

**GPS-Enhanced (3):**
- `VBOX_Lat_Min` - GPS Latitude
- `VBOX_Long_Minutes` - GPS Longitude
- `Laptrigger_lapdist_dls` - Distance from start/finish
- `aps` - Accelerator pedal position

#### Data Quality
- ✅ Good GPS coverage: 2.41M GPS points across 11.6M samples = ~21% with GPS
- ✅ Lap distance tracking available
- ✅ Both races available
- ✅ Good field size (20 cars)
- ⚠️ Less detailed race results found (may need to extract from lap times)

#### Pros
1. **Half the data size** - Faster to process/iterate
2. **Technical track** - Elevation changes, challenging corners
3. **Clean dataset** - Consistent format
4. **Good GPS coverage** - Still 4.9M GPS samples total

#### Cons
1. Less famous than Indianapolis (judges may not recognize)
2. Smaller dataset overall
3. Fewer auxiliary files found (weather, detailed results)
4. Track layout unknown (need external reference)

---

## Side-by-Side Comparison

| Feature | Indianapolis | Barber |
|---------|-------------|---------|
| **Total telemetry** | 44.5M rows | 23.3M rows |
| **Total GPS samples** | ~9.3M | ~4.9M |
| **Data size** | ~253 MB | ~141 MB |
| **Cars per race** | ~19 | ~20 |
| **Track fame** | ⭐⭐⭐⭐⭐ Iconic | ⭐⭐⭐ Known |
| **Processing speed** | Slower | Faster |
| **Aux files** | ✅ Complete | ⚠️ Basic |
| **GPS coverage** | 21% of samples | 21% of samples |
| **Lap distance** | ✅ Yes | ✅ Yes |

---

## Recommendation: **Indianapolis Motor Speedway**

### Why Indianapolis?

#### 1. **Brand Recognition** ⭐
- Every motorsport fan knows Indianapolis
- Judges will immediately connect with the venue
- "We analyzed the GR Cup at Indianapolis" > "We analyzed Barber"

#### 2. **Data Richness** 📊
- 44.5M telemetry points (nearly 2x Barber)
- More laps, more drivers, more samples
- Better statistical power for analysis
- More robust model training/validation

#### 3. **Competitive Racing** 🏁
- Winner decided by 0.17 seconds!
- Tight field throughout (19 finishers within ~24s)
- More opportunities to analyze:
  - Close battles
  - Position changes
  - Traffic management
  - Strategic differences

#### 4. **Complete Metadata** 📋
- Full driver names, teams, countries
- Detailed results files
- Easy to build compelling narratives
- "Spike Kohlbecker won by 0.17s - let's see why"

#### 5. **Multiple Analysis Angles** 🔍
With Indianapolis data, you can showcase:
- **Visual:** GPS racing line overlays on track map
- **Analytical:** 10 high-confidence metrics on 19 drivers
- **Strategic:** Lap-by-lap position changes and battles
- **Predictive:** Model Race 2 results from Race 1 patterns

---

## Recommended Project Scope

### Phase 1: Core Analysis (Week 1)
**Dataset:** Indianapolis Race 1 only
- Load and clean 21.4M rows
- Calculate 10 high-confidence metrics for all 19 drivers
- Rank drivers by technique quality
- Compare winner vs. field

**Deliverable:** "Driver Performance Scorecard"

### Phase 2: GPS Visualization (Week 2)
**Dataset:** Indianapolis Race 1 GPS data
- Extract 4.47M GPS coordinates
- Plot racing lines for top 5 drivers
- Create speed heat maps on track
- Show where winner gains time spatially

**Deliverable:** "Interactive Racing Line Comparison"

### Phase 3: Multi-Race Insights (Week 3)
**Dataset:** Indianapolis Race 1 + Race 2
- Compare same drivers across races
- Track evolution (Race 2 typically faster)
- Learning curve analysis
- Tire strategy comparison

**Deliverable:** "Race-to-Race Improvement Analysis"

### Optional: Generalization
**Dataset:** Add Barber for validation
- Show metrics work on different track
- Validate GPS extraction pipeline
- Prove approach generalizes

**Deliverable:** "Cross-Track Validation"

---

## Implementation Checklist

### Week 1: Foundation
- [ ] Extract Indianapolis data to project directory
- [ ] Load Race 1 telemetry into pandas/dask
- [ ] Implement high-confidence metrics (10 total)
- [ ] Generate driver scorecards
- [ ] Create basic visualizations

### Week 2: GPS Layer
- [ ] Parse GPS coordinates from telemetry
- [ ] Align GPS with lap timestamps
- [ ] Plot basic track outline from GPS
- [ ] Overlay multiple drivers' lines
- [ ] Create speed-colored trajectories

### Week 3: Polish
- [ ] Build interactive dashboard
- [ ] Add Race 2 comparison
- [ ] Generate insights document
- [ ] Create demo video
- [ ] Prepare presentation

---

## Data Loading Strategy (Indianapolis)

### Option A: Full Load (if you have RAM)
```python
import pandas as pd

# Load entire dataset (requires ~16GB RAM)
indy_r1 = pd.read_csv('R1_indianapolis_motor_speedway_telemetry.csv')

# Filter to specific cars
winner = indy_r1[indy_r1['vehicle_number'] == 55]  # Spike Kohlbecker
runner_up = indy_r1[indy_r1['vehicle_number'] == 2]  # Will Robusto
```

### Option B: Chunked Processing (recommended)
```python
import dask.dataframe as dd

# Load with Dask (lazy evaluation)
indy_r1 = dd.read_csv('R1_indianapolis_motor_speedway_telemetry.csv')

# Process in chunks
for car_num in [55, 2, 13]:  # Top 3 finishers
    car_data = indy_r1[indy_r1['vehicle_number'] == car_num].compute()
    metrics = calculate_metrics(car_data)
    print(f"Car #{car_num}: {metrics}")
```

### Option C: Database (for repeated analysis)
```python
import sqlite3
import pandas as pd

# One-time import to SQLite
conn = sqlite3.connect('indianapolis.db')
pd.read_csv('R1_indianapolis_motor_speedway_telemetry.csv',
            chunksize=100000).to_sql('telemetry', conn)

# Fast queries afterward
query = "SELECT * FROM telemetry WHERE vehicle_number = 55 AND lap = 7"
fastest_lap = pd.read_sql(query, conn)
```

---

## GPS Data Structure (Indianapolis)

### Sample GPS Records
```csv
lap,vehicle_number,telemetry_name,telemetry_value,timestamp
7,55,VBOX_Lat_Min,39.79534,2025-10-15T22:45:32.123Z
7,55,VBOX_Long_Minutes,-86.23512,2025-10-15T22:45:32.123Z
7,55,Laptrigger_lapdist_dls,1250,2025-10-15T22:45:32.123Z
```

### Converting to Track Visualization
```python
# Extract GPS for one car, one lap
gps_data = indy[
    (indy['vehicle_number'] == 55) &
    (indy['lap'] == 7) &
    (indy['telemetry_name'].isin(['VBOX_Lat_Min', 'VBOX_Long_Minutes']))
]

# Pivot to wide format
gps_pivot = gps_data.pivot_table(
    index='timestamp',
    columns='telemetry_name',
    values='telemetry_value'
)

# Plot racing line
import matplotlib.pyplot as plt
plt.plot(gps_pivot['VBOX_Long_Minutes'],
         gps_pivot['VBOX_Lat_Min'])
plt.title("Car #55 - Lap 7 Racing Line")
plt.xlabel("Longitude")
plt.ylabel("Latitude")
```

---

## Final Decision Matrix

| Criterion | Weight | Indianapolis | Barber | Winner |
|-----------|--------|--------------|---------|---------|
| Data volume | 20% | 10/10 | 5/10 | **Indy** |
| GPS quality | 25% | 10/10 | 10/10 | Tie |
| Track fame | 20% | 10/10 | 6/10 | **Indy** |
| Race competitiveness | 15% | 10/10 | ?/10 | **Indy** |
| Processing speed | 10% | 6/10 | 10/10 | Barber |
| Aux data | 10% | 10/10 | 6/10 | **Indy** |
| **Total Score** | | **9.15/10** | **7.15/10** | **INDY** |

---

## Conclusion

**Use Indianapolis Motor Speedway** as your primary dataset for the hackathon.

### Immediate Next Steps:
1. Extract Indianapolis data: `unzip indianapolis.zip -d data/indy/`
2. Load Race 1 results to understand race narrative
3. Pick 3-5 drivers to focus on (winner, podium, mid-pack, last)
4. Implement consistency metric first (easiest)
5. Build from there

### Success Criteria:
By end of Week 1, you should have:
- ✅ All 19 drivers ranked by 10 metrics
- ✅ Clear winner analysis ("Why Spike won by 0.17s")
- ✅ Improvement recommendations for each driver
- ✅ Basic visualizations (lap time plots, metric comparisons)

Then add GPS visualization in Week 2 for the "wow factor"!

Ready to start coding?
