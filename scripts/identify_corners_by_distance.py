"""
Identify corners using lap distance instead of GPS clustering.

This approach:
1. Uses Laptrigger_lapdist_dls for precise corner ordering
2. Finds brake peaks along the lap distance
3. Clusters by distance (not GPS) for better separation
4. Orders corners sequentially around the track

Usage:
    uv run python scripts/identify_corners_by_distance.py
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


def identify_corners_by_lap_distance(
    telemetry_with_gps: pd.DataFrame,
    brake_col: str = 'pbrake_f',
    min_corners: int = 12,
    max_corners: int = 16,
    brake_threshold_percentile: float = 40,  # Lower threshold to catch more corners
    distance_eps: float = 50,  # meters - clustering distance
    verbose: bool = True
) -> pd.DataFrame:
    """
    Identify corners using lap distance for ordering and clustering.

    This method is more reliable than GPS-only clustering because:
    1. Lap distance is 1D (simpler clustering)
    2. Natural ordering around track
    3. Better separation of tight corner complexes
    """

    df = telemetry_with_gps.copy()

    # Ensure we have required columns
    required = ['lap', 'lap_distance', brake_col, 'latitude', 'longitude']
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")

    if verbose:
        print("=" * 60)
        print("CORNER IDENTIFICATION BY LAP DISTANCE")
        print("=" * 60)
        print(f"Input: {len(df):,} data points")

    # Get lap distance range (track length)
    track_length = df['lap_distance'].max()
    if verbose:
        print(f"Track length: {track_length:.0f}m")

    # Find brake peaks for each lap
    all_peaks = []
    laps = sorted(df['lap'].unique())

    if verbose:
        print(f"Analyzing {len(laps)} laps")

    for lap in laps:
        lap_data = df[df['lap'] == lap].sort_values('lap_distance').reset_index(drop=True)

        if len(lap_data) < 100:
            continue

        brake = lap_data[brake_col].values

        # Smooth brake data
        if len(brake) > 10:
            brake_series = pd.Series(brake)
            brake_smooth = brake_series.rolling(5, center=True).mean()
            # Fill NaN with original values
            brake_smooth = brake_smooth.fillna(brake_series).values
        else:
            brake_smooth = brake

        # Find peaks (braking events)
        # Use lower prominence to catch lighter braking corners
        threshold = np.percentile(brake_smooth[brake_smooth > 0], brake_threshold_percentile)
        peaks, properties = find_peaks(
            brake_smooth,
            height=threshold,
            distance=20,  # Minimum samples between peaks
            prominence=5   # Lower prominence
        )

        for peak_idx in peaks:
            if peak_idx < len(lap_data):
                row = lap_data.iloc[peak_idx]
                # Only include if lap_distance is valid
                if pd.notna(row['lap_distance']):
                    all_peaks.append({
                        'lap': lap,
                        'lap_distance': row['lap_distance'],
                        'latitude': row['latitude'],
                        'longitude': row['longitude'],
                        'brake_pressure': row[brake_col],
                    })

    if not all_peaks:
        raise ValueError("No brake peaks found")

    peaks_df = pd.DataFrame(all_peaks)

    if verbose:
        print(f"Found {len(peaks_df)} brake peaks across all laps")
        print(f"Average: {len(peaks_df)/len(laps):.1f} per lap")

    # Remove any rows with NaN lap_distance
    peaks_df = peaks_df.dropna(subset=['lap_distance'])

    if verbose and len(all_peaks) != len(peaks_df):
        print(f"Removed {len(all_peaks) - len(peaks_df)} peaks with missing lap_distance")

    # Cluster peaks by lap distance
    # Use 1D clustering on lap_distance
    distances = peaks_df['lap_distance'].values.reshape(-1, 1)

    # Adaptive eps based on track length and expected corners
    # If track is 3925m and we expect 14 corners, average spacing is 280m
    # Use eps = spacing / 3 to allow some variation
    expected_spacing = track_length / max_corners
    adaptive_eps = min(distance_eps, expected_spacing / 3)

    if verbose:
        print(f"Clustering eps: {adaptive_eps:.1f}m")

    clustering = DBSCAN(eps=adaptive_eps, min_samples=max(2, len(laps)//4)).fit(distances)
    peaks_df['cluster'] = clustering.labels_

    # Filter out noise (cluster = -1)
    peaks_df = peaks_df[peaks_df['cluster'] >= 0]

    if len(peaks_df) == 0:
        raise ValueError("All peaks filtered as noise")

    # Aggregate clusters into corners
    corners = []
    for cluster_id in sorted(peaks_df['cluster'].unique()):
        cluster_data = peaks_df[peaks_df['cluster'] == cluster_id]

        corner = {
            'cluster_id': cluster_id,
            'lap_distance': cluster_data['lap_distance'].median(),
            'latitude': cluster_data['latitude'].median(),
            'longitude': cluster_data['longitude'].median(),
            'max_brake': cluster_data['brake_pressure'].max(),
            'median_brake': cluster_data['brake_pressure'].median(),
            'n_observations': len(cluster_data),
        }
        corners.append(corner)

    corners_df = pd.DataFrame(corners)

    # Sort by lap distance (track order)
    corners_df = corners_df.sort_values('lap_distance').reset_index(drop=True)
    corners_df['corner_id'] = range(1, len(corners_df) + 1)

    # Classify by brake pressure
    def classify_braking(pressure):
        if pressure < 30:
            return 'light'
        elif pressure < 60:
            return 'medium'
        else:
            return 'heavy'

    corners_df['corner_type'] = corners_df['max_brake'].apply(classify_braking)

    # Check if we have enough corners
    n_corners = len(corners_df)
    if n_corners < min_corners:
        if verbose:
            print(f"\n⚠️  Only found {n_corners} corners (expected {min_corners}+)")
            print("   Trying with smaller eps...")

        # Retry with smaller eps
        smaller_eps = adaptive_eps * 0.6
        clustering_retry = DBSCAN(eps=smaller_eps, min_samples=max(2, len(laps)//5)).fit(distances)
        peaks_df['cluster'] = clustering_retry.labels_
        peaks_df_retry = peaks_df[peaks_df['cluster'] >= 0].copy()

        if len(peaks_df_retry['cluster'].unique()) > n_corners:
            # Rebuild corners with new clustering
            corners = []
            for cluster_id in sorted(peaks_df_retry['cluster'].unique()):
                cluster_data = peaks_df_retry[peaks_df_retry['cluster'] == cluster_id]
                corner = {
                    'cluster_id': cluster_id,
                    'lap_distance': cluster_data['lap_distance'].median(),
                    'latitude': cluster_data['latitude'].median(),
                    'longitude': cluster_data['longitude'].median(),
                    'max_brake': cluster_data['brake_pressure'].max(),
                    'median_brake': cluster_data['brake_pressure'].median(),
                    'n_observations': len(cluster_data),
                }
                corners.append(corner)

            corners_df = pd.DataFrame(corners)
            corners_df = corners_df.sort_values('lap_distance').reset_index(drop=True)
            corners_df['corner_id'] = range(1, len(corners_df) + 1)
            corners_df['corner_type'] = corners_df['max_brake'].apply(classify_braking)

            if verbose:
                print(f"   Retry found {len(corners_df)} corners")

    if verbose:
        print(f"\nClustered into {len(corners_df)} corners")

        # Summary
        print(f"\nCorner Summary:")
        print(f"  Light braking (<30): {len(corners_df[corners_df['corner_type'] == 'light'])}")
        print(f"  Medium braking (30-60): {len(corners_df[corners_df['corner_type'] == 'medium'])}")
        print(f"  Heavy braking (>60): {len(corners_df[corners_df['corner_type'] == 'heavy'])}")

        print(f"\nCorner Details (in track order):")
        for _, row in corners_df.iterrows():
            print(f"  Corner {row['corner_id']:2d}: {row['corner_type']:6s} "
                  f"({row['max_brake']:5.1f} brake) at {row['lap_distance']:6.0f}m "
                  f"[{row['n_observations']} obs]")

    return corners_df


def main():
    # Path to Race 1 telemetry
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("GPS CORNER IDENTIFICATION - Indianapolis Road Course")
    print("LAP DISTANCE-BASED DETECTION")
    print("=" * 70)

    vehicle = 55
    laps = list(range(3, 20))  # Use more laps for better clustering

    print(f"\nVehicle: #{vehicle}")
    print(f"Laps: {laps[0]}-{laps[-1]} ({len(laps)} laps)")

    # Step 1: Load GPS data
    print("\n1. Loading GPS data...")
    gps = load_gps_data(data_file, vehicle=vehicle, lap=laps, verbose=False)
    print(f"   GPS points: {len(gps):,}")

    # Step 2: Load brake and lap distance data
    print("\n2. Loading telemetry...")
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['pbrake_f', 'Laptrigger_lapdist_dls'],
        wide_format=True,
        verbose=False
    )
    print(f"   Telemetry rows: {len(telemetry):,}")

    # Check available columns
    print(f"   Telemetry columns: {list(telemetry.columns)}")

    # Rename lap distance column for clarity
    if 'Laptrigger_lapdist_dls' in telemetry.columns:
        telemetry = telemetry.rename(columns={'Laptrigger_lapdist_dls': 'lap_distance'})
        lap_dist_col = 'lap_distance'
    else:
        print("\n❌ ERROR: Lap distance data not available!")
        print(f"   Available columns: {list(telemetry.columns)}")
        return

    # Step 3: Merge GPS with telemetry
    print("\n3. Merging data...")

    # Use telemetry as base (it has the lap_distance we need)
    # Merge GPS coordinates onto it
    merged = telemetry.merge(
        gps[['timestamp', 'latitude', 'longitude']],
        on='timestamp',
        how='inner'
    )

    print(f"   Merged: {len(merged):,} points")
    print(f"   Merged columns: {list(merged.columns)}")

    # Check lap distance coverage
    if 'lap_distance' in merged.columns:
        non_null_dist = merged['lap_distance'].notna().sum()
        print(f"   Lap distance range: {merged['lap_distance'].min():.0f} - {merged['lap_distance'].max():.0f}m")
        print(f"   Valid lap_distance: {non_null_dist:,} ({100*non_null_dist/len(merged):.1f}%)")
    else:
        print("   ⚠️  lap_distance not in merged data")

    # Step 4: Identify corners
    print("\n4. Identifying corners...")
    corners = identify_corners_by_lap_distance(
        merged,
        brake_col='pbrake_f',
        min_corners=12,
        max_corners=16,
        brake_threshold_percentile=40,
        distance_eps=80,  # meters
        verbose=True
    )

    # Step 5: Validate
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    if len(corners) >= 12:
        print(f"✅ SUCCESS: Found {len(corners)} corners (expected 12-16)")
    elif len(corners) >= 10:
        print(f"⚠️  Found {len(corners)} corners (expected 12-16, acceptable)")
    else:
        print(f"❌ ISSUE: Found only {len(corners)} corners (expected 12-16)")

    # Check corner spacing
    if len(corners) > 1:
        distances = corners['lap_distance'].diff().dropna()
        print(f"\nCorner spacing:")
        print(f"  Min: {distances.min():.0f}m")
        print(f"  Max: {distances.max():.0f}m")
        print(f"  Mean: {distances.mean():.0f}m")

        # Flag any suspiciously large gaps
        large_gaps = distances[distances > 500]
        if len(large_gaps) > 0:
            print(f"\n⚠️  Large gaps (>500m) detected:")
            for i, gap in large_gaps.items():
                print(f"     Corner {i} -> {i+1}: {gap:.0f}m")

    # Step 6: Save results
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)
    output_file = output_dir / 'corners_race1_distance.csv'

    corners.to_csv(output_file, index=False)
    print(f"\n💾 Corners saved to: {output_file}")

    print("=" * 70)

    return corners


if __name__ == "__main__":
    main()
