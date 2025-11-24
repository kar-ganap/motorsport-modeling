"""
Identify corners using brake pressure instead of speed.

This script uses brake pressure peaks for corner detection, which is more
reliable when speed data is sparse.

Usage:
    uv run python scripts/identify_indy_corners_brake.py
"""

from pathlib import Path
from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    identify_corners_from_brake,
    validate_corner_identification
)


def main():
    # Path to Race 1 telemetry
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("GPS CORNER IDENTIFICATION - Indianapolis Road Course")
    print("BRAKE-BASED DETECTION")
    print("=" * 70)

    vehicle = 55
    laps = list(range(3, 16))  # Use laps 3-15 for better clustering

    print(f"\nVehicle: #{vehicle}")
    print(f"Laps: {laps[0]}-{laps[-1]} ({len(laps)} laps)")

    # Step 1: Load GPS data
    print("\n1. Loading GPS data...")
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)
    print(f"   GPS points: {len(gps):,}")

    # Step 2: Load brake pressure data
    print("\n2. Loading brake pressure telemetry...")
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['pbrake_f', 'pbrake_r'],  # Front and rear brake
        wide_format=True,
        verbose=False
    )

    print(f"   Telemetry rows: {len(telemetry):,}")

    # Check brake data availability
    if 'pbrake_f' not in telemetry.columns and 'pbrake_r' not in telemetry.columns:
        print("\n❌ ERROR: No brake data found!")
        return

    # Use front brake if available, otherwise rear
    brake_col = 'pbrake_f' if 'pbrake_f' in telemetry.columns else 'pbrake_r'
    print(f"   Using brake column: {brake_col}")

    # Step 3: Merge GPS with brake data
    print("\n3. Merging GPS with brake data...")
    gps_with_brake = gps.merge(
        telemetry[['timestamp', brake_col]],
        on='timestamp',
        how='inner'
    )

    print(f"   Merged: {len(gps_with_brake):,} GPS points with brake data")
    print(f"   Non-null brake: {gps_with_brake[brake_col].notna().sum():,}")

    # Step 4: Identify corners using brake pressure
    print("\n4. Identifying corners from brake pressure peaks...")
    corners = identify_corners_from_brake(
        gps_with_brake,
        brake_col=brake_col,
        min_corners=10,
        max_corners=18,
        brake_threshold_percentile=60,  # Consider top 40% brake pressures
        verbose=True
    )

    # Step 5: Validate results
    print("\n5. Validating corner identification...")
    try:
        validate_corner_identification(
            corners,
            expected_range=(12, 18),
            track_name="Indianapolis Motor Speedway (Road Course)"
        )
        print("   ✅ Validation PASSED")
    except ValueError as e:
        print(f"   ⚠️  Validation warning: {e}")

    # Step 6: Summary
    print("\n" + "=" * 70)
    print("CORNER IDENTIFICATION COMPLETE")
    print("=" * 70)

    print(f"\nFound {len(corners)} corners:")
    print(f"  Light braking (<30): {len(corners[corners['corner_type'] == 'light'])}")
    print(f"  Medium braking (30-60): {len(corners[corners['corner_type'] == 'medium'])}")
    print(f"  Heavy braking (>60): {len(corners[corners['corner_type'] == 'heavy'])}")

    print(f"\nBrake pressure range: {corners['max_brake'].min():.1f} - {corners['max_brake'].max():.1f}")

    print("\nCorner details:")
    print(corners[['corner_id', 'corner_type', 'max_brake', 'latitude', 'longitude', 'n_observations']].to_string(index=False))

    # Step 7: Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1_brake.csv'

    corners.to_csv(output_file, index=False)
    print(f"\n💾 Corners saved to: {output_file}")

    # Step 8: Compare with speed-based detection
    print("\n" + "=" * 70)
    print("COMPARISON")
    print("=" * 70)
    print(f"Speed-based detection: 8 corners (limited by sparse speed data)")
    print(f"Brake-based detection: {len(corners)} corners (full brake data coverage)")
    print(f"\nImprovement: {len(corners) - 8} additional corners detected")

    if len(corners) >= 12:
        print("\n✅ SUCCESS: Found expected number of corners for Indianapolis!")
    else:
        print(f"\n⚠️  Found {len(corners)} corners (expected 12-18)")

    print("=" * 70)

    return corners


if __name__ == "__main__":
    main()
