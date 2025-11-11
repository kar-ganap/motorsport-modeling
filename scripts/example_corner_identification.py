"""
Example: GPS Corner Identification

This script demonstrates how to identify corners from GPS and speed data.
Run this with the full race dataset (not the sample).

Usage:
    uv run python scripts/example_corner_identification.py /path/to/race1.csv

Expected output:
    - Identifies 8-15 corners at Indianapolis
    - Shows corner locations, speeds, and classifications
    - Validates corner detection quality
"""

import sys
from pathlib import Path

from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    identify_corners_from_gps,
    validate_corner_identification
)


def identify_indy_corners(data_file: Path, vehicle: int = 55, laps: list = None):
    """
    Identify corners at Indianapolis Motor Speedway from race data.

    Parameters
    ----------
    data_file : Path
        Path to race telemetry CSV file
    vehicle : int, default=55
        Vehicle number to analyze (default: winner #55)
    laps : list, optional
        Specific laps to analyze (default: use fastest 5 laps)

    Returns
    -------
    pd.DataFrame
        Corner information with locations and characteristics
    """
    print("=" * 70)
    print("GPS CORNER IDENTIFICATION - Indianapolis Motor Speedway")
    print("=" * 70)

    # Step 1: Load GPS data
    print(f"\n1. Loading GPS data for vehicle #{vehicle}...")
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=True)

    if len(gps) < 500:
        print("\n⚠️  WARNING: Very few GPS points found.")
        print("   Make sure you're using the full race dataset, not the sample.")
        print("   Sample data is too sparse for corner identification.")
        return None

    # Step 2: Load speed data
    print(f"\n2. Loading speed telemetry...")
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['speed'],
        wide_format=True,
        verbose=True
    )

    # Step 3: Merge GPS with speed
    print(f"\n3. Merging GPS with speed data...")
    gps_with_speed = gps.merge(
        telemetry[['timestamp', 'speed']],
        on='timestamp',
        how='inner'
    )

    print(f"   Merged: {len(gps_with_speed):,} GPS points with speed")
    print(f"   Non-null speed: {gps_with_speed['speed'].notna().sum():,}")

    if gps_with_speed['speed'].notna().sum() < 100:
        print("\n⚠️  ERROR: Insufficient speed data.")
        print("   Cannot identify corners without speed measurements.")
        return None

    # Step 4: Identify corners
    print(f"\n4. Identifying corners...")
    corners = identify_corners_from_gps(
        gps_with_speed,
        min_corners=8,       # Indianapolis has ~10-12 corners
        max_corners=15,
        verbose=True
    )

    # Step 5: Validate results
    print(f"\n5. Validating corner identification...")
    try:
        validate_corner_identification(
            corners,
            expected_range=(8, 15),
            track_name="Indianapolis Motor Speedway"
        )
        print("   ✅ Validation PASSED")
    except ValueError as e:
        print(f"   ❌ Validation FAILED: {e}")

    # Step 6: Summary
    print("\n" + "=" * 70)
    print("CORNER IDENTIFICATION COMPLETE")
    print("=" * 70)
    print(f"\nFound {len(corners)} corners:")
    print(f"  Slow corners (<60 km/h): {len(corners[corners['corner_type'] == 'slow'])}")
    print(f"  Medium corners (60-90 km/h): {len(corners[corners['corner_type'] == 'medium'])}")
    print(f"  Fast corners (>90 km/h): {len(corners[corners['corner_type'] == 'fast'])}")

    print("\nCorner details:")
    print(corners[['corner_id', 'corner_type', 'min_speed', 'latitude', 'longitude', 'n_observations']].to_string(index=False))

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  - Use these corners for per-corner metrics (braking, apex speed, etc.)")
    print("  - Compare racing lines between drivers")
    print("  - Analyze corner-by-corner performance")
    print("=" * 70)

    return corners


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: uv run python scripts/example_corner_identification.py <data_file>")
        print("\nExample:")
        print("  uv run python scripts/example_corner_identification.py data/race1.csv")
        sys.exit(1)

    data_file = Path(sys.argv[1])

    if not data_file.exists():
        print(f"Error: File not found: {data_file}")
        sys.exit(1)

    # Identify corners for winner (vehicle #55)
    # Use laps 5-10 for analysis (after warm-up, before tire degradation)
    corners = identify_indy_corners(
        data_file,
        vehicle=55,
        laps=[5, 6, 7, 8, 9, 10]
    )

    if corners is not None:
        # Save corners to CSV for later use
        output_file = data_file.parent / 'corners_identified.csv'
        corners.to_csv(output_file, index=False)
        print(f"\n💾 Corners saved to: {output_file}")
