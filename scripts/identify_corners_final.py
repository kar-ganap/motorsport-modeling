"""
Final corner identification with optimized parameters based on diagnosis.

Key changes from previous attempts:
1. Lower min_samples for DBSCAN (to catch sparser eastern section)
2. Lower brake threshold (to catch medium braking corners)
3. Use all laps for maximum data

Usage:
    uv run python scripts/identify_corners_final.py
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


def identify_corners_final(
    gps_with_brake: pd.DataFrame,
    brake_col: str = 'pbrake_f',
    eps: float = 0.00009,  # Best from previous testing
    min_samples: int = 2,  # Lower to catch sparser areas
    brake_threshold_percentile: float = 40,  # Lower to catch medium braking
    verbose: bool = True
) -> pd.DataFrame:
    """Identify corners with optimized parameters."""

    df = gps_with_brake.copy()

    if verbose:
        print("=" * 60)
        print("CORNER IDENTIFICATION (FINAL)")
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

        # Get threshold - use a lower percentile
        non_zero_brake = brake_smooth[brake_smooth > 0]
        if len(non_zero_brake) == 0:
            continue
        threshold = np.percentile(non_zero_brake, brake_threshold_percentile)

        # Find peaks with lower requirements
        peaks, properties = find_peaks(
            brake_smooth,
            height=max(threshold, 10),  # At least 10 bar
            distance=10,  # Reduced distance between peaks
            prominence=2   # Lower prominence
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

    # Cluster by GPS coordinates with lower min_samples
    coords = peaks_df[['latitude', 'longitude']].values

    clustering = DBSCAN(eps=eps, min_samples=min_samples).fit(coords)
    peaks_df['cluster'] = clustering.labels_

    # Filter noise but be less aggressive
    peaks_df_clustered = peaks_df[peaks_df['cluster'] >= 0]

    if len(peaks_df_clustered) == 0:
        if verbose:
            print("All peaks filtered as noise - trying with eps*1.5")
        clustering = DBSCAN(eps=eps*1.5, min_samples=min_samples).fit(coords)
        peaks_df['cluster'] = clustering.labels_
        peaks_df_clustered = peaks_df[peaks_df['cluster'] >= 0]

    if len(peaks_df_clustered) == 0:
        raise ValueError("All peaks filtered as noise")

    # Aggregate into corners
    corners = []
    for cluster_id in sorted(peaks_df_clustered['cluster'].unique()):
        cluster_data = peaks_df_clustered[peaks_df_clustered['cluster'] == cluster_id]

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

    # Sort by track position - this is tricky
    # Indianapolis runs clockwise, so we need a better ordering
    # Use angle from center of track
    center_lat = corners_df['latitude'].mean()
    center_lon = corners_df['longitude'].mean()

    # Calculate angle from center (counterclockwise from east)
    corners_df['angle'] = np.arctan2(
        corners_df['latitude'] - center_lat,
        corners_df['longitude'] - center_lon
    )

    # Sort by angle (this gives rough track order)
    corners_df = corners_df.sort_values('angle').reset_index(drop=True)
    corners_df['corner_id'] = range(1, len(corners_df) + 1)
    corners_df = corners_df.drop(columns=['angle'])

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
    print("INDIANAPOLIS CORNER IDENTIFICATION - FINAL")
    print("=" * 70)

    vehicle = 55
    # Use ALL available laps for maximum data
    laps = list(range(2, 26))  # Laps 2-25 (24 laps - almost all race)

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

    # Identify corners
    print("\n4. Identifying corners...")
    corners = identify_corners_final(
        merged,
        eps=0.00009,
        min_samples=2,  # Lower to catch eastern section
        brake_threshold_percentile=40,
        verbose=True
    )

    # Show results
    print("\n" + "=" * 70)
    print(f"CORNER DETAILS")
    print("=" * 70)

    print(f"\nCorner list (in track order):")
    for _, row in corners.iterrows():
        print(f"  Corner {row['corner_id']:2d}: {row['corner_type']:6s} "
              f"({row['max_brake']:5.1f} brake) at ({row['latitude']:.5f}, {row['longitude']:.5f}) "
              f"[{row['n_observations']} obs]")

    # Validation
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    if 12 <= len(corners) <= 16:
        print(f"✅ SUCCESS: Found {len(corners)} corners (expected 12-16)")
    elif 10 <= len(corners) <= 18:
        print(f"⚠️  ACCEPTABLE: Found {len(corners)} corners (expected 12-16)")
    else:
        print(f"❌ ISSUE: Found {len(corners)} corners (expected 12-16)")

    # Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1_final.csv'

    corners.to_csv(output_file, index=False)
    print(f"\n💾 Saved to: {output_file}")

    print("=" * 70)

    return corners


if __name__ == "__main__":
    main()
