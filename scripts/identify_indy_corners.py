"""
Identify corners from Indianapolis Race 1 telemetry data.

Usage:
    uv run python scripts/identify_indy_corners.py

This script will:
1. Load R1_indianapolis_motor_speedway_telemetry.csv
2. Identify corners using GPS + speed data
3. Save results to data/processed/corners_race1.csv
"""

from pathlib import Path
from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    identify_corners_from_gps,
    validate_corner_identification,
    get_available_vehicles
)


def main():
    # Path to Race 1 telemetry
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print("=" * 70)
        print("ERROR: Telemetry file not found")
        print("=" * 70)
        print(f"\nExpected file: {data_file}")
        print("\nPlease extract the zip file to data/raw/")
        print("Expected file: R1_indianapolis_motor_speedway_telemetry.csv")
        return

    print("=" * 70)
    print("GPS CORNER IDENTIFICATION - Indianapolis Road Course")
    print("Race 1 Telemetry Data")
    print("=" * 70)

    # Step 1: Check available vehicles
    print("\n1. Checking available vehicles...")
    vehicles = get_available_vehicles(data_file)
    print(f"   Found {len(vehicles)} vehicles: {sorted(vehicles)}")

    # Use winner (vehicle #55) or first available vehicle
    if 55 in vehicles:
        vehicle = 55
        print(f"   Using vehicle #{vehicle} (winner)")
    else:
        vehicle = vehicles[0]
        print(f"   Using vehicle #{vehicle} (first available)")

    # Step 2: Load GPS data
    print(f"\n2. Loading GPS data for vehicle #{vehicle}...")
    # Use laps 5-10 for analysis (after warm-up, before tire degradation)
    gps = load_gps_data(data_file, vehicle=vehicle, lap=[5, 6, 7, 8, 9, 10], verbose=True)

    if len(gps) < 500:
        print(f"\n⚠️  WARNING: Only {len(gps)} GPS points found.")
        print("   Trying all laps instead...")
        gps = load_gps_data(data_file, vehicle=vehicle, verbose=True)

        if len(gps) < 500:
            print(f"\n❌ ERROR: Insufficient GPS data ({len(gps)} points)")
            print("   Need at least 500 GPS points for reliable corner identification.")
            return

    # Step 3: Load speed data
    print(f"\n3. Loading speed telemetry...")
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=[5, 6, 7, 8, 9, 10],
        parameters=['speed'],
        wide_format=True,
        verbose=True
    )

    if 'speed' not in telemetry.columns:
        print("\n❌ ERROR: No speed data found in telemetry.")
        print("   Available parameters:", telemetry.columns.tolist())
        return

    # Step 4: Merge GPS with speed
    print(f"\n4. Merging GPS with speed data...")
    gps_with_speed = gps.merge(
        telemetry[['timestamp', 'speed']],
        on='timestamp',
        how='inner'
    )

    print(f"   Merged: {len(gps_with_speed):,} GPS points with speed")
    print(f"   Non-null speed: {gps_with_speed['speed'].notna().sum():,}")

    if gps_with_speed['speed'].notna().sum() < 100:
        print("\n❌ ERROR: Insufficient speed data.")
        print(f"   Only {gps_with_speed['speed'].notna().sum()} speed measurements available.")
        return

    # Step 5: Identify corners
    print(f"\n5. Identifying corners...")
    corners = identify_corners_from_gps(
        gps_with_speed,
        min_corners=10,      # Indianapolis Road Course has 14 corners
        max_corners=18,      # Allow some tolerance for clustering
        verbose=True
    )

    # Step 6: Validate results
    print(f"\n6. Validating corner identification...")
    try:
        validate_corner_identification(
            corners,
            expected_range=(12, 18),
            track_name="Indianapolis Motor Speedway (Road Course)"
        )
        print("   ✅ Validation PASSED")
    except ValueError as e:
        print(f"   ⚠️  Validation warning: {e}")
        print("   Proceeding anyway - this may be normal depending on data quality.")

    # Step 7: Summary
    print("\n" + "=" * 70)
    print("CORNER IDENTIFICATION COMPLETE")
    print("=" * 70)
    print(f"\nFound {len(corners)} corners:")
    print(f"  Slow corners (<60 km/h): {len(corners[corners['corner_type'] == 'slow'])}")
    print(f"  Medium corners (60-90 km/h): {len(corners[corners['corner_type'] == 'medium'])}")
    print(f"  Fast corners (>90 km/h): {len(corners[corners['corner_type'] == 'fast'])}")

    print("\nCorner details:")
    print(corners[['corner_id', 'corner_type', 'min_speed', 'latitude', 'longitude', 'n_observations']].to_string(index=False))

    # Step 8: Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1.csv'

    corners.to_csv(output_file, index=False)
    print(f"\n💾 Corners saved to: {output_file}")

    print("\n" + "=" * 70)
    print("Next steps:")
    print("  - Use these corners for per-corner metrics (braking, apex speed, etc.)")
    print("  - Compare racing lines between drivers")
    print("  - Analyze corner-by-corner performance")
    print("=" * 70)

    return corners


if __name__ == "__main__":
    main()
