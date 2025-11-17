"""
Identify corners from Indianapolis Race 1 telemetry data with tuning options.

This script provides multiple parameter settings to optimize corner detection.

Usage:
    uv run python scripts/identify_indy_corners_tuned.py
"""

from pathlib import Path
from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
    identify_corners_from_gps,
    validate_corner_identification,
    get_available_vehicles
)


def identify_corners_with_params(data_file, vehicle, laps, speed_threshold_percentile=40):
    """
    Identify corners with specific parameters.

    Parameters
    ----------
    data_file : Path
        Path to telemetry CSV
    vehicle : int
        Vehicle number
    laps : list
        List of laps to analyze
    speed_threshold_percentile : float
        Percentile for speed threshold (higher = more corners found)
    """
    print(f"\n{'='*70}")
    print(f"Attempting with speed_threshold_percentile={speed_threshold_percentile}")
    print(f"{'='*70}")

    # Load GPS data
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)

    # Load speed data
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['speed'],
        wide_format=True,
        verbose=False
    )

    # Merge
    gps_with_speed = gps.merge(
        telemetry[['timestamp', 'speed']],
        on='timestamp',
        how='inner'
    )

    print(f"Data: {len(gps_with_speed):,} GPS+speed points")

    # Identify corners
    corners = identify_corners_from_gps(
        gps_with_speed,
        min_corners=10,
        max_corners=20,
        speed_threshold_percentile=speed_threshold_percentile,
        verbose=True
    )

    return corners


def main():
    # Path to Race 1 telemetry
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("GPS CORNER IDENTIFICATION - Indianapolis Road Course")
    print("TUNING MODE: Trying multiple parameter sets")
    print("=" * 70)

    # Use vehicle #55 (winner)
    vehicle = 55

    # Strategy 1: More laps for better clustering
    print("\n" + "=" * 70)
    print("STRATEGY 1: Use more laps (3-15 instead of 5-10)")
    print("=" * 70)

    more_laps = list(range(3, 16))  # Laps 3-15
    print(f"Using laps: {more_laps[0]}-{more_laps[-1]} ({len(more_laps)} laps)")

    corners_strategy1 = identify_corners_with_params(
        data_file,
        vehicle,
        more_laps,
        speed_threshold_percentile=40  # Default
    )

    # Strategy 2: Higher speed threshold (find faster corners too)
    print("\n" + "=" * 70)
    print("STRATEGY 2: Higher speed threshold percentile (50 vs 40)")
    print("=" * 70)
    print("This will include faster corners in detection")

    corners_strategy2 = identify_corners_with_params(
        data_file,
        vehicle,
        more_laps,
        speed_threshold_percentile=50
    )

    # Strategy 3: Even higher threshold
    print("\n" + "=" * 70)
    print("STRATEGY 3: Very high speed threshold percentile (60)")
    print("=" * 70)
    print("This will detect even high-speed 'kinks' as corners")

    corners_strategy3 = identify_corners_with_params(
        data_file,
        vehicle,
        more_laps,
        speed_threshold_percentile=60
    )

    # Compare results
    print("\n" + "=" * 70)
    print("RESULTS COMPARISON")
    print("=" * 70)

    strategies = [
        ("Original (laps 5-10, threshold=40)", 7),  # From previous run
        ("Strategy 1 (laps 3-15, threshold=40)", len(corners_strategy1)),
        ("Strategy 2 (laps 3-15, threshold=50)", len(corners_strategy2)),
        ("Strategy 3 (laps 3-15, threshold=60)", len(corners_strategy3))
    ]

    print("\nCorners found by strategy:")
    for name, count in strategies:
        status = "✅" if 12 <= count <= 18 else "⚠️ "
        print(f"  {status} {name}: {count} corners")

    # Recommendation
    print("\n" + "=" * 70)
    print("RECOMMENDATION")
    print("=" * 70)

    best_strategy = None
    best_corners = None

    if 12 <= len(corners_strategy1) <= 18:
        best_strategy = "Strategy 1"
        best_corners = corners_strategy1
    elif 12 <= len(corners_strategy2) <= 18:
        best_strategy = "Strategy 2"
        best_corners = corners_strategy2
    elif 12 <= len(corners_strategy3) <= 18:
        best_strategy = "Strategy 3"
        best_corners = corners_strategy3
    else:
        # Pick closest to 14
        distances = [
            abs(len(corners_strategy1) - 14),
            abs(len(corners_strategy2) - 14),
            abs(len(corners_strategy3) - 14)
        ]
        best_idx = distances.index(min(distances))
        if best_idx == 0:
            best_strategy = "Strategy 1"
            best_corners = corners_strategy1
        elif best_idx == 1:
            best_strategy = "Strategy 2"
            best_corners = corners_strategy2
        else:
            best_strategy = "Strategy 3"
            best_corners = corners_strategy3

    print(f"\nBest result: {best_strategy}")
    print(f"Found {len(best_corners)} corners (expected 12-18 for Indianapolis Road Course)")

    # Show corner details
    print("\nCorner details:")
    print(best_corners[['corner_id', 'corner_type', 'min_speed', 'latitude', 'longitude', 'n_observations']].to_string(index=False))

    # Save best result
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1_tuned.csv'

    best_corners.to_csv(output_file, index=False)
    print(f"\n💾 Best corners saved to: {output_file}")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Strategy used: {best_strategy}")
    print(f"Corners found: {len(best_corners)}")
    print(f"  Slow (<60 km/h): {len(best_corners[best_corners['corner_type'] == 'slow'])}")
    print(f"  Medium (60-90 km/h): {len(best_corners[best_corners['corner_type'] == 'medium'])}")
    print(f"  Fast (>90 km/h): {len(best_corners[best_corners['corner_type'] == 'fast'])}")
    print(f"\nSpeed range: {best_corners['min_speed'].min():.1f} - {best_corners['min_speed'].max():.1f} km/h")
    print("=" * 70)

    return best_corners


if __name__ == "__main__":
    main()
