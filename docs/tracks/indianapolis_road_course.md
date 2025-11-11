# Indianapolis Motor Speedway - Track Configuration

**Source:** `data/tracks/indy.json`

## Track Layout

**Configuration:** Indianapolis Motor Speedway (Road Course)

**Key Specifications:**
- Circuit length: 3,925.2 meters (2.44 miles)
- Number of corners: **14**
- Layout: Combines part of the oval with infield section
- Used by: IndyCar Grand Prix, sports cars

## Track Geometry

```json
{
  "track_id": "indy",
  "name": "Indianapolis Motor Speedway (Road Course)",
  "geometry": {
    "circuit_length_m": 3925.2144,
    "circuit_length_miles": 2.4399570175953076
  }
}
```

## Timing Sectors

The track is divided into 3 timing sectors:

| Sector | From | To | Length (m) | Length (in) |
|--------|------|-----|------------|-------------|
| S1 | Start/Finish | i1 | 1,364.0 | 53,712 |
| S2 | i1 | i2 | 1,386.7 | 54,604 |
| S3 | i2 | i3 | 1,173.4 | 46,220 |

**Total:** 3,924.1 meters

## Expected Corner Identification

When running GPS corner identification on Indianapolis Road Course data:

**Expected Results:**
- Number of corners: **14** (±2 for clustering tolerance)
- Validation range: 12-18 corners
- Corner types: Mix of slow, medium, and fast corners

**Corner Characteristics:**
- **Slow corners** (<60 km/h): Hairpins and tight infield corners
- **Medium corners** (60-90 km/h): Technical infield sections
- **Fast corners** (>90 km/h): Banking transitions, fast sweepers

## Usage in Code

```python
from motorsport_modeling.data import identify_corners_from_gps

# For Indianapolis Road Course
corners = identify_corners_from_gps(
    gps_with_speed,
    min_corners=10,      # Lower bound (accounting for clustering)
    max_corners=18,      # Upper bound (some corners may split)
    verbose=True
)

# Validate
validate_corner_identification(
    corners,
    expected_range=(12, 18),
    track_name="Indianapolis Motor Speedway (Road Course)"
)
```

## References

- Track data: `data/tracks/indy.json`
- Sector map: `data/tracks/indy_table.csv`
- Source document: `Indy_Circuit_Map.pdf`

---

**Note:** The actual number of corners detected may vary slightly (12-16) depending on:
- DBSCAN clustering parameters
- GPS data density and quality
- Speed measurement frequency
- Whether complex/chicane corners cluster as one or split into multiple

This is normal and expected - the algorithm will find the major braking zones consistently.
