"""
Identify corners with tuned parameters for Indianapolis Road Course.

Based on analysis:
- Track has 14 corners
- Previous detection found only 10
- Issues: tight chicanes merged, start/finish area split

Parameters tuned:
- Smaller eps (0.00012) to separate tight chicanes
- Lower brake threshold (50th percentile) to catch light braking
- More laps for better clustering

Usage:
    uv run python scripts/identify_corners_tuned_v2.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from scipy.signal import find_peaks
from sklearn.cluster import DBSCAN

from motorsport_modeling.data import (
    load_telemetry,
    load_gps_data,
)


def identify_corners_tuned(
    gps_with_brake: pd.DataFrame,
    brake_col: str = 'pbrake_f',
    eps: float = 0.00012,  # Smaller for tight chicanes (~13m)
    min_samples: int = 3,
    brake_threshold_percentile: float = 50,  # Lower to catch light braking
    verbose: bool = True
) -> pd.DataFrame:
    """Identify corners with tuned parameters."""

    df = gps_with_brake.copy()

    if verbose:
        print("=" * 60)
        print("CORNER IDENTIFICATION (TUNED PARAMETERS)")
        print("=" * 60)
        print(f"Input: {len(df):,} GPS points")
        print(f"Parameters: eps={eps}, min_samples={min_samples}, threshold={brake_threshold_percentile}%")

    # Find brake peaks for each lap
    all_peaks = []
    laps = sorted(df['lap'].unique())

    if verbose:
        print(f"Analyzing {len(laps)} laps")

    for lap in laps:
        lap_data = df[df['lap'] == lap].sort_values('timestamp').reset_index(drop=True)

        if len(lap_data) < 100:
            continue

        brake = lap_data[brake_col].values

        # Smooth brake data
        brake_smooth = pd.Series(brake).rolling(5, center=True).mean().fillna(pd.Series(brake)).values

        # Get threshold
        non_zero_brake = brake_smooth[brake_smooth > 0]
        if len(non_zero_brake) == 0:
            continue
        threshold = np.percentile(non_zero_brake, brake_threshold_percentile)

        # Find peaks with lower prominence to catch light braking
        peaks, properties = find_peaks(
            brake_smooth,
            height=threshold,
            distance=15,  # Slightly less distance between peaks
            prominence=3   # Lower prominence for lighter braking
        )

        for peak_idx in peaks:
            if peak_idx < len(lap_data):
                row = lap_data.iloc[peak_idx]
                all_peaks.append({
                    'lap': lap,
                    'latitude': row['latitude'],
                    'longitude': row['longitude'],
                    'brake_pressure': row[brake_col],
                })

    if not all_peaks:
        raise ValueError("No brake peaks found")

    peaks_df = pd.DataFrame(all_peaks)

    if verbose:
        print(f"Found {len(peaks_df)} brake peaks")
        print(f"Average: {len(peaks_df)/len(laps):.1f} per lap")

    # Cluster by GPS coordinates
    coords = peaks_df[['latitude', 'longitude']].values

    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    peaks_df['cluster'] = clustering.labels_

    # Filter noise
    peaks_df = peaks_df[peaks_df['cluster'] >= 0]

    if len(peaks_df) == 0:
        raise ValueError("All peaks filtered as noise")

    # Aggregate into corners
    corners = []
    for cluster_id in sorted(peaks_df['cluster'].unique()):
        cluster_data = peaks_df[peaks_df['cluster'] == cluster_id]

        corner = {
            'corner_id': len(corners) + 1,
            'latitude': cluster_data['latitude'].median(),
            'longitude': cluster_data['longitude'].median(),
            'max_brake': cluster_data['brake_pressure'].max(),
            'median_brake': cluster_data['brake_pressure'].median(),
            'n_observations': len(cluster_data),
        }

        # Classify by brake pressure
        if corner['max_brake'] < 30:
            corner['corner_type'] = 'light'
        elif corner['max_brake'] < 60:
            corner['corner_type'] = 'medium'
        else:
            corner['corner_type'] = 'heavy'

        corners.append(corner)

    corners_df = pd.DataFrame(corners)

    # Sort by position (using a rough track order based on GPS)
    # Indianapolis runs roughly: SW corner (start) -> NW -> NE -> SE -> back to SW
    # Sort by longitude first (west to east roughly), then latitude
    corners_df = corners_df.sort_values(['longitude', 'latitude']).reset_index(drop=True)
    corners_df['corner_id'] = range(1, len(corners_df) + 1)

    if verbose:
        print(f"\nFound {len(corners_df)} corners")
        print(f"  Light: {len(corners_df[corners_df['corner_type'] == 'light'])}")
        print(f"  Medium: {len(corners_df[corners_df['corner_type'] == 'medium'])}")
        print(f"  Heavy: {len(corners_df[corners_df['corner_type'] == 'heavy'])}")

    return corners_df


def main():
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("INDIANAPOLIS CORNER IDENTIFICATION - TUNED v2")
    print("=" * 70)

    vehicle = 55
    # Use more laps for better clustering
    laps = list(range(3, 24))  # Laps 3-23 (20 laps)

    print(f"\nVehicle: #{vehicle}")
    print(f"Laps: {laps[0]}-{laps[-1]} ({len(laps)} laps)")

    # Load data
    print("\n1. Loading GPS data...")
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)
    print(f"   GPS points: {len(gps):,}")

    print("\n2. Loading brake telemetry...")
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['pbrake_f'],
        wide_format=True,
        verbose=False
    )
    print(f"   Telemetry rows: {len(telemetry):,}")

    # Merge
    print("\n3. Merging data...")
    merged = gps.merge(
        telemetry[['timestamp', 'pbrake_f']],
        on='timestamp',
        how='inner'
    )
    print(f"   Merged: {len(merged):,} points")

    # Try multiple eps values to find the best one
    print("\n4. Identifying corners...")

    best_corners = None
    best_count = 0
    best_eps = 0

    # Try different eps values - finer granularity
    for eps in [0.00008, 0.00009, 0.00010, 0.00011, 0.00012, 0.00014, 0.00016]:
        try:
            corners = identify_corners_tuned(
                merged,
                eps=eps,
                min_samples=3,
                brake_threshold_percentile=50,
                verbose=False
            )

            n_corners = len(corners)
            print(f"   eps={eps}: {n_corners} corners")

            # Prefer count in range 11-14
            if 11 <= n_corners <= 14:
                # Perfect range
                if best_count < 11 or best_count > 14:
                    best_corners = corners
                    best_count = n_corners
                    best_eps = eps
                elif abs(n_corners - 12) < abs(best_count - 12):
                    # Prefer closer to 12
                    best_corners = corners
                    best_count = n_corners
                    best_eps = eps
            elif best_count == 0 or (best_count < 11 and n_corners > best_count) or (best_count > 14 and n_corners < best_count):
                best_corners = corners
                best_count = n_corners
                best_eps = eps

        except Exception as e:
            print(f"   eps={eps}: ERROR - {e}")

    if best_corners is None:
        print("\n❌ Failed to identify corners with any eps value")
        return

    print(f"\n✅ Best result: {best_count} corners with eps={best_eps}")

    # Show detailed results
    print("\n" + "=" * 70)
    print(f"CORNER DETAILS (eps={best_eps})")
    print("=" * 70)

    print(f"\nBy type:")
    print(f"  Light braking: {len(best_corners[best_corners['corner_type'] == 'light'])}")
    print(f"  Medium braking: {len(best_corners[best_corners['corner_type'] == 'medium'])}")
    print(f"  Heavy braking: {len(best_corners[best_corners['corner_type'] == 'heavy'])}")

    print(f"\nCorner list:")
    for _, row in best_corners.iterrows():
        print(f"  Corner {row['corner_id']:2d}: {row['corner_type']:6s} "
              f"({row['max_brake']:5.1f} brake) at ({row['latitude']:.5f}, {row['longitude']:.5f}) "
              f"[{row['n_observations']} obs]")

    # Validation
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    if best_count >= 12 and best_count <= 16:
        print(f"✅ SUCCESS: Found {best_count} corners (expected 12-16 for Indianapolis)")
    elif best_count >= 10:
        print(f"⚠️  ACCEPTABLE: Found {best_count} corners (expected 12-16, got {best_count})")
    else:
        print(f"❌ ISSUE: Found only {best_count} corners (expected 12-16)")

    # Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1_tuned.csv'

    best_corners.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")

    print("=" * 70)

    return best_corners


if __name__ == "__main__":
    main()
