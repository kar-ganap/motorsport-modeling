"""
Diagnose why corner detection is finding only 8 corners instead of 14.

This script analyzes:
1. Speed data sampling frequency
2. Speed distribution across the lap
3. Alternative signals (brake, steering) for corner detection
4. DBSCAN clustering parameter sensitivity

Usage:
    uv run python scripts/diagnose_corner_detection.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    get_available_parameters
)


def main():
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("CORNER DETECTION DIAGNOSTIC")
    print("=" * 70)

    vehicle = 55
    laps = list(range(5, 11))  # Laps 5-10

    # 1. Check available parameters
    print("\n1. AVAILABLE TELEMETRY PARAMETERS")
    print("-" * 70)
    params = get_available_parameters(data_file)
    print(f"Total parameters: {len(params)}")
    print(f"Parameters: {sorted(params)}")

    # Look for corner-related parameters
    corner_params = []
    for p in params:
        p_lower = p.lower()
        if any(keyword in p_lower for keyword in ['brake', 'steer', 'speed', 'throttle', 'aps', 'lat', 'long']):
            corner_params.append(p)

    print(f"\nCorner-relevant parameters ({len(corner_params)}):")
    for p in sorted(corner_params):
        print(f"  - {p}")

    # 2. Load all corner-relevant telemetry
    print("\n2. TELEMETRY DATA DENSITY")
    print("-" * 70)

    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=corner_params,
        wide_format=True,
        verbose=False
    )

    print(f"Rows: {len(telemetry):,}")
    print(f"Laps: {len(laps)}")
    print(f"Rows per lap: {len(telemetry) / len(laps):,.0f}")

    # Check data availability for each parameter
    print("\nData availability:")
    for param in sorted(corner_params):
        if param in telemetry.columns:
            non_null = telemetry[param].notna().sum()
            pct = 100 * non_null / len(telemetry)
            print(f"  {param:30s}: {non_null:6,} ({pct:5.1f}%)")

    # 3. Analyze speed distribution
    print("\n3. SPEED DISTRIBUTION ANALYSIS")
    print("-" * 70)

    if 'speed' in telemetry.columns:
        speeds = telemetry['speed'].dropna()
        print(f"Speed measurements: {len(speeds):,}")
        print(f"Speed range: {speeds.min():.1f} - {speeds.max():.1f} km/h")
        print(f"Mean speed: {speeds.mean():.1f} km/h")
        print(f"Median speed: {speeds.median():.1f} km/h")

        print("\nSpeed percentiles:")
        for p in [10, 20, 30, 40, 50]:
            threshold = np.percentile(speeds, p)
            count = (speeds < threshold).sum()
            print(f"  {p}th percentile: {threshold:6.1f} km/h ({count:4,} points below)")

        # Check if we have any very slow speeds
        slow_speeds = speeds[speeds < 60]
        print(f"\nVery slow speeds (<60 km/h): {len(slow_speeds):,} measurements")
        if len(slow_speeds) > 0:
            print(f"  Minimum: {slow_speeds.min():.1f} km/h")
            print(f"  Mean: {slow_speeds.mean():.1f} km/h")

    # 4. Check brake data
    print("\n4. BRAKE DATA ANALYSIS")
    print("-" * 70)

    brake_cols = [c for c in telemetry.columns if 'brake' in c.lower()]
    if brake_cols:
        for brake_col in brake_cols:
            brake_data = telemetry[brake_col].dropna()
            if len(brake_data) > 0:
                print(f"\n{brake_col}:")
                print(f"  Measurements: {len(brake_data):,}")
                print(f"  Range: {brake_data.min():.2f} - {brake_data.max():.2f}")
                print(f"  Mean: {brake_data.mean():.2f}")

                # Count braking events (brake > 10)
                braking = brake_data[brake_data > 10]
                print(f"  Braking events (>{10}): {len(braking):,}")
    else:
        print("No brake data available")

    # 5. GPS data quality
    print("\n5. GPS DATA QUALITY")
    print("-" * 70)

    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)
    print(f"GPS points: {len(gps):,}")
    print(f"GPS points per lap: {len(gps) / len(laps):,.0f}")

    # Calculate lap distance covered
    if len(gps) > 0:
        from scipy.spatial.distance import cdist

        # Group by lap and check coverage
        for lap in laps[:2]:  # Just check first 2 laps
            lap_gps = gps[gps['lap'] == lap].sort_values('timestamp')
            if len(lap_gps) > 1:
                coords = lap_gps[['latitude', 'longitude']].values
                # Estimate total distance (rough approximation)
                dists = np.sqrt(np.sum(np.diff(coords, axis=0)**2, axis=1))
                # Convert degrees to meters (rough: 1 degree ≈ 111km)
                dists_m = dists * 111000
                total_dist = dists_m.sum()
                print(f"  Lap {lap}: {len(lap_gps)} GPS points, ~{total_dist:.0f}m covered, ~{total_dist/len(lap_gps):.1f}m between points")

    # 6. Recommendation
    print("\n" + "=" * 70)
    print("DIAGNOSIS & RECOMMENDATIONS")
    print("=" * 70)

    print("\nIssues identified:")

    # Check speed data density
    if 'speed' in telemetry.columns:
        speed_per_lap = telemetry['speed'].notna().sum() / len(laps)
        if speed_per_lap < 1000:
            print(f"  ⚠️  Low speed data density: {speed_per_lap:.0f} measurements/lap")
            print(f"     (Need ~1000+ for reliable corner detection)")

    # Check for slow corners
    if 'speed' in telemetry.columns:
        slow_count = (telemetry['speed'] < 60).sum()
        if slow_count < 50:
            print(f"  ⚠️  Very few slow speed measurements (<60 km/h): {slow_count}")
            print(f"     (Missing tight corners or driver very fast)")

    # Check alternative signals
    if not brake_cols:
        print("  ⚠️  No brake data available for corner detection")

    print("\nPossible solutions:")
    print("  1. Use ALL laps (not just 5-10) to increase data density")
    print("  2. Adjust DBSCAN eps parameter (corner clustering distance)")
    print("  3. Use brake pressure peaks instead of speed minima")
    print("  4. Combine multiple signals (speed + brake + steering)")
    print("  5. Accept 8 corners as valid (may represent major braking zones)")

    print("\nNext steps:")
    print("  - Try script with ALL available laps")
    print("  - Consider brake-based corner detection")
    print("  - Or proceed with 8 corners for initial analysis")

    print("=" * 70)


if __name__ == "__main__":
    main()
