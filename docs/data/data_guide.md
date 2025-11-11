# VIR Dataset Guide: Understanding the Available Data

## Overview

The Virginia International Raceway (VIR) dataset contains data from **2 races** with **~21 cars** per race, generating approximately **1.4GB of telemetry data per race** plus lap timing and race results.

**Total data points:** ~11.4 million telemetry readings per race
**Duration:** 20-lap races (~45 minutes each)
**Sampling rate:** ~10-20 Hz per telemetry parameter per car

---

## File Structure

```
VIR/
├── Race 1/
│   ├── R1_vir_telemetry_data.csv              (1.4 GB - High-frequency telemetry)
│   ├── vir_lap_time_R1.csv                    (51 KB - Lap times)
│   ├── vir_lap_start_R1.csv                   (60 KB - Lap start timestamps)
│   ├── vir_lap_end_R1.csv                     (60 KB - Lap end timestamps)
│   ├── 23_AnalysisEnduranceWithSections_*.CSV (99 KB - Detailed sector analysis)
│   ├── 03_Provisional Results_*.CSV           (2.6 KB - Final standings)
│   ├── 99_Best 10 Laps By Driver_*.CSV        (3.4 KB - Best lap times)
│   └── 26_Weather_*.CSV                       (3.0 KB - Weather conditions)
└── Race 2/
    └── (Same structure)
```

---

## 1. Track Metadata Files

### Track Configuration (`data/vir.json`)

**Purpose:** Physical track characteristics and timing points

```json
{
  "track_id": "vir",
  "name": "Virginia International Raceway",
  "geometry": {
    "circuit_length_m": 5262.6,
    "circuit_length_miles": 3.27
  },
  "timing_model": {
    "sectors": [
      {"id": "S1", "from": "SF", "to": "i1", "length_m": 1652.6},
      {"id": "S2", "from": "i1", "to": "i2", "length_m": 2158.0},
      {"id": "S3", "from": "i2", "to": "SF", "length_m": 1452.0}
    ],
    "intermediates": ["i1", "i2"],
    "speed_traps": [{"id": "ST", "length_m": 36.6}]
  },
  "pit_lane": {
    "pit_in_from_sf_m": 4898.7,
    "pit_out_from_sfp_m": -16.0,
    "pit_in_to_pit_out_m": 340.6
  }
}
```

**Use cases:**
- Convert distance markers to sector identification
- Calculate theoretical minimum lap times
- Map pit strategy timing
- Normalize sector times across different track configs

---

## 2. Telemetry Data (The Big One)

### `R1_vir_telemetry_data.csv` (1.4 GB)

**Format:** Long format (one row per measurement per parameter)

**Columns:**
```
expire_at          - (empty in this dataset)
lap                - Lap number (1-20+)
meta_event         - Event identifier (I_R04_2025-07-20)
meta_session       - Session type (R1 = Race 1)
meta_source        - Data source (kafka:gr-raw)
meta_time          - When data was received by system
original_vehicle_id- Original vehicle ID (GR86-XXX-YY)
outing             - Session outing number (usually 0)
telemetry_name     - Parameter being measured (see below)
telemetry_value    - The actual measurement value
timestamp          - ECU timestamp when measurement taken
vehicle_id         - Vehicle identifier (GR86-XXX-YY)
vehicle_number     - Car number (visible on car)
```

**Available telemetry parameters:**
```
accx_can         - Longitudinal acceleration (G) [forward/backward]
accy_can         - Lateral acceleration (G) [left/right turns]
ath              - Throttle blade position (0-100%)
gear             - Current gear (1-6)
nmot             - Engine RPM
pbrake_f         - Front brake pressure (bar)
pbrake_r         - Rear brake pressure (bar)
speed            - Vehicle speed (km/h)
Steering_Angle   - Steering wheel angle (degrees, -/+ for left/right)
```

**Data structure example:**
```csv
lap,vehicle_number,telemetry_name,telemetry_value,timestamp
1,2,accx_can,0.217,2025-07-19T18:06:40.077Z
1,2,accy_can,-0.19,2025-07-19T18:06:40.077Z
1,2,ath,100.02,2025-07-19T18:06:40.077Z
1,2,pbrake_f,0,2025-07-19T18:06:40.077Z
1,2,speed,145.3,2025-07-19T18:06:40.077Z
```

**Key characteristics:**
- **Long format:** Each telemetry parameter is a separate row
- **High frequency:** ~10-20 samples per second per parameter
- **11.4 million rows:** For all cars across entire race
- **Per car:** ~600,000 rows per car for 20-lap race

**Sampling rate calculation:**
```
Race duration: ~45 minutes = 2,700 seconds
Parameters: 9 different measurements
Cars: 21 vehicles
Frequency: ~10 Hz average

Expected rows: 2,700s × 9 params × 21 cars × 10 Hz = 5.1M rows
Actual: 11.4M rows (some params sampled faster, includes practice/warm-up)
```

**GPS/Location data:**
⚠️ **NOT INCLUDED** in this telemetry file. The documentation mentions `VBOX_Long_Minutes` and `VBOX_Lat_Min` but they don't appear in the VIR data. You'll need to infer position from:
- Lap distance (`Laptrigger_lapdist_dls` mentioned in docs but not in data)
- Time-based interpolation between timing sectors
- Speed integration

---

## 3. Lap Timing Files

### `vir_lap_time_R1.csv` (484 rows)

**Purpose:** Lap completion times

**Columns:**
```
lap           - Lap number
vehicle_id    - Vehicle identifier
vehicle_number- Car number
timestamp     - When lap was completed
value         - Lap time in milliseconds
```

**Example:**
```csv
lap,vehicle_id,value
20,GR86-002-2,129469  (= 2:09.469)
19,GR86-002-2,130043  (= 2:10.043)
```

**Use cases:**
- Calculate lap time degradation over stint
- Identify fastest laps
- Compare race pace vs. qualifying
- Detect pit stops (missing laps or huge time jump)

### `vir_lap_start_R1.csv` & `vir_lap_end_R1.csv`

**Purpose:** Precise timing of lap start/end crossing start/finish line

**Columns:** Same as lap_time, but:
- `lap_start`: timestamp when car crosses SF line to start lap
- `lap_end`: timestamp when car crosses SF line to end lap

**Use case:**
- Calculate exact lap duration
- Synchronize telemetry to lap boundaries
- Detect timing anomalies

---

## 4. Sector Analysis Files

### `23_AnalysisEnduranceWithSections_Race_1_Anonymized.CSV`

**Purpose:** Detailed lap-by-lap sector performance

**Columns (40+ fields):**
```
NUMBER          - Car number
DRIVER_NUMBER   - Driver identifier
LAP_NUMBER      - Lap number (1-20)
LAP_TIME        - Total lap time (MM:SS.mmm)
S1, S2, S3      - Sector times (seconds.milliseconds)
S1_IMPROVEMENT  - Improvement over previous lap S1
S2_IMPROVEMENT  - Improvement over previous lap S2
S3_IMPROVEMENT  - Improvement over previous lap S3
KPH             - Average lap speed
TOP_SPEED       - Maximum speed on lap
IM1_time        - Intermediate 1 split time
IM2_time        - Intermediate 2 split time
FL_time         - Finish line time
ELAPSED         - Total elapsed race time
FLAG_AT_FL      - Flag status (GF=Green, FCY=Full Course Yellow)
PIT_TIME        - Time spent in pit (if applicable)
```

**Example row:**
```
NUMBER: 3
LAP_NUMBER: 10
LAP_TIME: 2:10.282
S1: 45.996
S2: 48.988
S3: 35.298
KPH: 145.4
TOP_SPEED: (not always populated)
FLAG_AT_FL: GF (Green Flag)
```

**Use cases:**
- **Sector comparison:** Which sector is a driver's weakness?
- **Tire degradation:** Track S1/S2/S3 times over stint
- **Traffic impact:** Lap time spikes indicate traffic/incidents
- **Consistency analysis:** Standard deviation of sector times
- **Flag analysis:** Performance under yellow vs. green

---

## 5. Race Results Files

### `03_Provisional Results_Race_1_Anonymized.CSV`

**Purpose:** Final race standings

**Columns:**
```
POSITION        - Finishing position
NUMBER          - Car number
STATUS          - Classified / DNF / DNS
LAPS            - Laps completed
TOTAL_TIME      - Total race time
GAP_FIRST       - Gap to race winner
GAP_PREVIOUS    - Gap to car ahead
FL_LAPNUM       - Lap number of fastest lap
FL_TIME         - Fastest lap time
FL_KPH          - Fastest lap average speed
CLASS           - Race class (Am = Amateur)
VEHICLE         - Car model (Toyota GR86)
```

**Example:**
```
POSITION: 1
NUMBER: 72
LAPS: 20
TOTAL_TIME: 45:41.760
FL_TIME: 2:08.511
FL_LAPNUM: 10
```

**Use cases:**
- Identify race winner and podium
- Calculate average race pace
- Find who set fastest lap and when
- Analyze finishing gaps

### `99_Best 10 Laps By Driver_Race_1_Anonymized.CSV`

**Purpose:** Top 10 lap times per driver

**Columns:**
```
NUMBER           - Car number
VEHICLE          - Car model
BESTLAP_1        - Fastest lap time
BESTLAP_1_LAPNUM - When fastest lap occurred
BESTLAP_2        - 2nd fastest lap
...
BESTLAP_10       - 10th fastest lap
AVERAGE          - Average of top 10 laps
```

**Example:**
```
NUMBER: 72
BESTLAP_1: 2:08.511 (Lap 10)
BESTLAP_2: 2:08.610 (Lap 9)
BESTLAP_3: 2:08.777 (Lap 8)
AVERAGE: 2:09.044
```

**Use cases:**
- **Consistency metric:** Spread between best and 10th best
- **Peak performance:** Absolute fastest lap
- **Race strategy:** When did they set fast laps (early/mid/late)?

---

## 6. Weather Data

### `26_Weather_Race_1_Anonymized.CSV`

**Purpose:** Environmental conditions during race

**Columns:**
```
TIME_UTC_SECONDS  - Unix timestamp
TIME_UTC_STR      - Human-readable time
AIR_TEMP          - Air temperature (°C)
TRACK_TEMP        - Track surface temperature (°C)
HUMIDITY          - Relative humidity (%)
PRESSURE          - Atmospheric pressure (mbar)
WIND_SPEED        - Wind speed (km/h)
WIND_DIRECTION    - Wind direction (degrees)
RAIN              - Rain status (0=dry, 1=wet)
```

**Sampling:** ~1 reading per minute

**Example:**
```
TIME: 2025-07-19 6:07:02 PM
AIR_TEMP: 34.15°C
TRACK_TEMP: 49.9°C
HUMIDITY: 53.33%
WIND_SPEED: 5.76 km/h
RAIN: 0 (dry)
```

**Use cases:**
- **Temperature impact:** How does track temp affect lap times?
- **Track evolution:** Track typically gets faster as temp increases
- **Tire strategy:** Hot track = more degradation
- **Comparison:** Race 1 vs Race 2 conditions

---

## Data Relationships & Linkage

### How files connect:

```
Car #72 (Race Winner)
│
├─ Telemetry (R1_vir_telemetry_data.csv)
│  └─ Filter: vehicle_number = 72
│     └─ 11M rows → ~600K rows for this car
│
├─ Lap Times (vir_lap_time_R1.csv)
│  └─ Filter: vehicle_number = 72
│     └─ 20 rows (one per lap)
│
├─ Sector Analysis (23_AnalysisEnduranceWithSections_*.CSV)
│  └─ Filter: NUMBER = 72
│     └─ 20 rows with S1/S2/S3 breakdown
│
└─ Race Result (03_Provisional Results_*.CSV)
   └─ Filter: NUMBER = 72
      └─ 1 row (overall result)
```

### Join keys:

**Primary key:** `vehicle_number` or `NUMBER` (car number on vehicle)

**Temporal key:** `lap` number

**Example join:**
```python
# Get Car 72's Lap 10 data
lap_time = lap_times[(car == 72) & (lap == 10)]  # 2:08.511
sectors = sector_data[(NUMBER == 72) & (LAP_NUMBER == 10)]  # S1/S2/S3 splits
telemetry = telem[(vehicle_number == 72) & (lap == 10)]  # All sensor data

# Now you have:
# - Lap time: 2:08.511
# - Sector splits: S1=45.996, S2=48.988, S3=35.298
# - Full telemetry: speed, throttle, braking at every moment
```

---

## Data Quality Notes

### Known Issues (from documentation):

**1. Lap count errors:**
- Sometimes reported as lap 32768 (data corruption)
- Time values still accurate
- Use timestamps to calculate actual lap number

**2. Vehicle identification:**
```
Format: GR86-XXX-YY
        └─┬─┘ └┬┘ └┬┘
          │    │   └─ Car number (visible sticker)
          │    └───── Chassis number (always unique)
          └────────── Model

Note: Car number may be 000 if not assigned yet
      Chassis number is always reliable for tracking
```

**3. Timestamp accuracy:**
- `timestamp`: ECU time (may drift)
- `meta_time`: Server receive time (more accurate)
- Prefer `meta_time` for synchronization

**4. Missing GPS:**
- Documentation mentions GPS fields
- Not present in VIR data
- Must infer location from lap distance or time-based interpolation

---

## Quick Stats: VIR Race 1

```
Cars started:         24
Cars finished:        24
Laps completed:       20 (all finishers)
Race duration:        45:41.760 (winner)
Average lap (winner): 2:17.088
Fastest lap:          2:08.432 (Car #13, Lap 10)
Slowest lap:          2:15+ (various)

Winner margin:        0.215s (incredibly close!)
Last place gap:       1:56.588 behind winner

Telemetry points:     11,401,182 measurements
Parameters tracked:   9 per car
Sampling rate:        ~10-20 Hz per parameter
```

---

## Recommended Data Loading Strategy

### For Python Analysis:

**1. Small files first (understanding the race):**
```python
import pandas as pd

# Race results - who won?
results = pd.read_csv('03_Provisional Results_Race 1_Anonymized.CSV', sep=';')

# Sector analysis - lap-by-lap performance
sectors = pd.read_csv('23_AnalysisEnduranceWithSections_Race 1_Anonymized.CSV', sep=';')

# Best laps - consistency check
best_laps = pd.read_csv('99_Best 10 Laps By Driver_Race 1_Anonymized.CSV', sep=';')

# Weather - conditions
weather = pd.read_csv('26_Weather_Race 1_Anonymized.CSV', sep=';')
```

**2. Medium files (timing data):**
```python
# Lap times
lap_times = pd.read_csv('vir_lap_time_R1.csv')

# Calculate lap time in seconds
lap_times['lap_time_sec'] = lap_times['value'] / 1000
```

**3. Large file (telemetry - be careful!):**
```python
# Option A: Load one car at a time
import dask.dataframe as dd

# Use Dask for large files
telemetry = dd.read_csv('R1_vir_telemetry_data.csv')

# Filter to one car
car_72 = telemetry[telemetry['vehicle_number'] == 72].compute()

# Option B: Load specific laps only
# (Read in chunks, filter, then concatenate)

# Option C: Use database (recommended for repeated analysis)
import sqlite3
# Load CSV into SQLite once, then query efficiently
```

**4. Pivot telemetry to wide format:**
```python
# Current format (long):
# timestamp, telemetry_name, telemetry_value
# 10:00:01, speed, 145.3
# 10:00:01, throttle, 100
# 10:00:01, brake_f, 0

# Convert to wide format (better for analysis):
car_72_wide = car_72.pivot_table(
    index=['timestamp', 'lap'],
    columns='telemetry_name',
    values='telemetry_value'
).reset_index()

# Result:
# timestamp, lap, speed, ath, pbrake_f, pbrake_r, accx_can, accy_can, ...
# 10:00:01, 5, 145.3, 100, 0, 0, 0.5, -1.2, ...
```

---

## Analysis Ideas by Data Type

### Using Sector Data:
- **Tire degradation:** Plot S1/S2/S3 times over 20 laps
- **Consistency:** Calculate σ of sector times per driver
- **Traffic impact:** Detect lap time spikes (>2σ from mean)
- **Race pace:** Compare early laps (1-5) vs. late laps (16-20)

### Using Telemetry:
- **Braking analysis:** Peak `pbrake_f` values per lap
- **Throttle discipline:** % of lap at full throttle
- **Cornering G-forces:** Max `accy_can` (lateral) per sector
- **Smoothness:** Calculate derivative of `Steering_Angle`
- **Coasting time:** Count time with `ath < 5` AND `pbrake_f < 5`

### Using Lap Times:
- **Degradation curve:** Plot lap time vs. lap number
- **Fastest lap prediction:** Analyze lap 8-12 (typically fastest)
- **Stint analysis:** Detect tire change (lap time suddenly improves)

### Using Race Results + Telemetry:
- **Winner analysis:** What made Car #72 fastest?
- **Position battles:** Compare telemetry of cars finishing close
- **Overtaking detection:** Lap where positions swap + telemetry

---

## Summary: What Can You Build?

With this data, you can:

### Category 1: Driver Training & Insights
✓ Compare driver inputs (throttle, brake, steering) at same point on track
✓ Identify braking point differences
✓ Analyze corner-by-corner performance
✓ Calculate consistency metrics
✓ Find where slower drivers lose time

### Category 2: Pre-Event Prediction
✓ Model lap time degradation patterns
✓ Predict qualifying results from practice (if practice data exists)
✓ Forecast race pace from early laps
✓ Analyze track evolution (Race 1 vs Race 2)

### Category 4: Real-Time Analytics
✓ Pit strategy calculator (when tire delta exceeds pit loss)
✓ Gap management (track intervals lap-by-lap)
✓ Position prediction (if X pits now, where do they emerge?)
✓ Live dashboard simulation (replay race with "real-time" data)

### Limitations:
✗ No GPS coordinates (can't visualize racing line on map)
✗ Limited to race data (no practice/qualifying sessions in some tracks)
✗ No pit stop data (must infer from lap time jumps)
✗ No tire compound information
✗ No fuel load data

---

## Next Steps

1. **Load and explore results.csv** to understand race outcome
2. **Load sector analysis** to see lap-by-lap patterns
3. **Pick 2-3 cars** (winner, mid-pack, last place)
4. **Load telemetry for those cars** and compare
5. **Identify interesting patterns** (degradation, traffic, mistakes)
6. **Build initial prototype** of your chosen project category

The data is rich enough for sophisticated analysis despite missing GPS!
