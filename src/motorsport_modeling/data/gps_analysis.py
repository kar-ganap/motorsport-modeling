"""
GPS analysis utilities for corner identification and racing line analysis.

This module provides functions to:
- Identify corners from GPS coordinates and speed data
- Cluster corner locations across multiple laps
- Extract racing lines and compare them
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from scipy.signal import find_peaks
from sklearn.cluster import DBSCAN
import warnings


def identify_corners_from_gps(
    gps_data: pd.DataFrame,
    speed_col: str = 'speed',
    lat_col: str = 'latitude',
    lon_col: str = 'longitude',
    min_corners: int = 8,
    max_corners: int = 15,
    speed_threshold_percentile: float = 40,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Identify corners from GPS data by clustering speed minima.

    Corners are detected as locations where speed is locally minimum
    (braking zones/apex). Multiple laps are used to identify consistent
    corner locations.

    Parameters
    ----------
    gps_data : pd.DataFrame
        GPS data with columns: latitude, longitude, speed, lap, vehicle_number
    speed_col : str, default='speed'
        Name of speed column
    lat_col : str, default='latitude'
        Name of latitude column
    lon_col : str, default='longitude'
        Name of longitude column
    min_corners : int, default=8
        Minimum expected corners per lap
    max_corners : int, default=15
        Maximum expected corners per lap
    speed_threshold_percentile : float, default=40
        Only consider speed minima below this percentile as potential corners
    verbose : bool, default=False
        Print progress and diagnostics

    Returns
    -------
    pd.DataFrame
        Corner information with columns:
        - corner_id: Unique corner identifier (1, 2, 3, ...)
        - latitude: Mean latitude of corner
        - longitude: Mean longitude of corner
        - min_speed: Typical minimum speed at corner
        - corner_type: 'slow', 'medium', or 'fast' based on speed

    Examples
    --------
    >>> from motorsport_modeling.data import load_gps_data
    >>> gps = load_gps_data('data.csv', vehicle=55, lap=[5,6,7])
    >>> corners = identify_corners_from_gps(gps, verbose=True)
    >>> print(f"Found {len(corners)} corners")
    """
    if verbose:
        print("=" * 60)
        print("GPS CORNER IDENTIFICATION")
        print("=" * 60)
        print(f"Input: {len(gps_data):,} GPS points")

    # Ensure we have speed data
    if speed_col not in gps_data.columns:
        # If speed is in wide format, we need to handle it
        # For now, raise error
        raise ValueError(f"Speed column '{speed_col}' not found in GPS data")

    # Step 1: Find speed minima for each lap
    speed_minima = []

    laps = gps_data['lap'].unique()
    if verbose:
        print(f"Analyzing {len(laps)} laps")

    for lap in laps:
        lap_data = gps_data[gps_data['lap'] == lap].copy()

        if len(lap_data) < 50:
            # Not enough data points for this lap
            continue

        # Sort by timestamp to ensure correct order
        lap_data = lap_data.sort_values('timestamp')

        # Find local minima in speed
        # Use negative speed to find minima with find_peaks
        speeds = lap_data[speed_col].values

        # Skip if too many NaN values
        if np.isnan(speeds).sum() > len(speeds) * 0.5:
            continue

        # Interpolate NaN values
        speeds = pd.Series(speeds).interpolate().values

        # Only consider speeds below threshold
        speed_threshold = np.percentile(speeds, speed_threshold_percentile)

        # Find peaks in -speed (i.e., minima in speed)
        # Require minimum distance between peaks (avoid detecting same corner twice)
        min_distance = len(speeds) // (max_corners * 2)  # Rough estimate
        peaks, properties = find_peaks(
            -speeds,
            distance=max(min_distance, 10),
            prominence=5  # Require at least 5 km/h drop
        )

        # Filter to only low-speed peaks
        low_speed_peaks = peaks[speeds[peaks] < speed_threshold]

        # Get GPS coordinates at these minima
        for peak_idx in low_speed_peaks:
            if peak_idx < len(lap_data):
                row = lap_data.iloc[peak_idx]
                speed_minima.append({
                    'lap': lap,
                    'latitude': row[lat_col],
                    'longitude': row[lon_col],
                    'speed': row[speed_col],
                    'vehicle_number': row.get('vehicle_number', None)
                })

    if len(speed_minima) == 0:
        raise ValueError("No speed minima found. Check data quality.")

    speed_minima_df = pd.DataFrame(speed_minima)

    if verbose:
        print(f"Found {len(speed_minima)} speed minima across all laps")
        print(f"Average: {len(speed_minima) / len(laps):.1f} per lap")

    # Step 2: Cluster minima to identify unique corners
    # Use DBSCAN to cluster nearby minima (same corner across different laps)

    coords = speed_minima_df[[lat_col, lon_col]].values

    # Epsilon: maximum distance between points in same cluster
    # For GPS coordinates, ~0.0001 degrees ≈ 11 meters
    # Corners should be within ~20 meters of each other across laps
    eps = 0.0002  # ~22 meters

    clustering = DBSCAN(eps=eps, min_samples=max(2, len(laps) // 3)).fit(coords)
    speed_minima_df['cluster'] = clustering.labels_

    # Remove noise points (cluster = -1)
    clustered = speed_minima_df[speed_minima_df['cluster'] >= 0].copy()

    if len(clustered) == 0:
        warnings.warn("DBSCAN found no valid clusters. Trying larger epsilon.")
        # Retry with larger epsilon
        eps = 0.0004
        clustering = DBSCAN(eps=eps, min_samples=2).fit(coords)
        speed_minima_df['cluster'] = clustering.labels_
        clustered = speed_minima_df[speed_minima_df['cluster'] >= 0].copy()

    n_clusters = len(clustered['cluster'].unique())

    if verbose:
        print(f"Clustered into {n_clusters} unique corners")

    # Check if we have reasonable number of corners
    if n_clusters < min_corners:
        warnings.warn(
            f"Found only {n_clusters} corners, expected at least {min_corners}. "
            "Track may have fewer corners or data quality issues."
        )
    elif n_clusters > max_corners:
        warnings.warn(
            f"Found {n_clusters} corners, expected at most {max_corners}. "
            "May need to adjust clustering parameters."
        )

    # Step 3: Calculate corner statistics
    corners = []

    for cluster_id in sorted(clustered['cluster'].unique()):
        cluster_data = clustered[clustered['cluster'] == cluster_id]

        corner_info = {
            'corner_id': len(corners) + 1,  # 1-indexed
            'latitude': cluster_data[lat_col].mean(),
            'longitude': cluster_data[lon_col].mean(),
            'min_speed': cluster_data[speed_col].median(),
            'speed_std': cluster_data[speed_col].std(),
            'n_observations': len(cluster_data),
        }

        # Classify corner type by speed
        if corner_info['min_speed'] < 60:
            corner_info['corner_type'] = 'slow'
        elif corner_info['min_speed'] < 90:
            corner_info['corner_type'] = 'medium'
        else:
            corner_info['corner_type'] = 'fast'

        corners.append(corner_info)

    corners_df = pd.DataFrame(corners)

    # Sort corners by track position (approximate by latitude + longitude)
    # This gives a rough ordering around the track
    # Better would be to use lap distance if available
    corners_df = corners_df.sort_values(['latitude', 'longitude']).reset_index(drop=True)
    corners_df['corner_id'] = range(1, len(corners_df) + 1)

    if verbose:
        print("\nCorner Summary:")
        print(f"  Slow corners (<60 km/h): {len(corners_df[corners_df['corner_type'] == 'slow'])}")
        print(f"  Medium corners (60-90 km/h): {len(corners_df[corners_df['corner_type'] == 'medium'])}")
        print(f"  Fast corners (>90 km/h): {len(corners_df[corners_df['corner_type'] == 'fast'])}")
        print("\nCorner Details:")
        for _, corner in corners_df.iterrows():
            print(f"  Corner {corner['corner_id']}: {corner['corner_type']:6s} "
                  f"({corner['min_speed']:.1f} km/h) "
                  f"at ({corner['latitude']:.5f}, {corner['longitude']:.5f})")
        print("=" * 60)

    return corners_df


def get_corner_at_position(
    corners: pd.DataFrame,
    latitude: float,
    longitude: float,
    max_distance: float = 0.0005
) -> Optional[int]:
    """
    Find which corner (if any) is at a given GPS position.

    Parameters
    ----------
    corners : pd.DataFrame
        Output from identify_corners_from_gps()
    latitude : float
        GPS latitude
    longitude : float
        GPS longitude
    max_distance : float, default=0.0005
        Maximum distance (in degrees) to consider as "at corner"
        ~0.0005 degrees ≈ 55 meters

    Returns
    -------
    int or None
        Corner ID if position is near a corner, None otherwise

    Examples
    --------
    >>> corner_id = get_corner_at_position(corners, 39.795, -86.235)
    >>> if corner_id:
    ...     print(f"Currently at corner {corner_id}")
    """
    # Calculate distance to each corner
    distances = np.sqrt(
        (corners['latitude'] - latitude)**2 +
        (corners['longitude'] - longitude)**2
    )

    min_distance = distances.min()

    if min_distance < max_distance:
        corner_idx = distances.idxmin()
        return corners.loc[corner_idx, 'corner_id']

    return None


def extract_corner_telemetry(
    telemetry: pd.DataFrame,
    gps_data: pd.DataFrame,
    corners: pd.DataFrame,
    corner_id: int,
    window_distance: float = 100,  # meters
    verbose: bool = False
) -> pd.DataFrame:
    """
    Extract telemetry data for a specific corner.

    Gets telemetry from braking zone through apex to corner exit.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide-format telemetry data
    gps_data : pd.DataFrame
        GPS data with lat/lon
    corners : pd.DataFrame
        Corner definitions from identify_corners_from_gps()
    corner_id : int
        Which corner to extract (1-indexed)
    window_distance : float, default=100
        Distance (meters) before/after corner to include
        ~0.001 degrees latitude ≈ 111 meters
    verbose : bool, default=False
        Print extraction info

    Returns
    -------
    pd.DataFrame
        Telemetry data near the specified corner

    Examples
    --------
    >>> corner_data = extract_corner_telemetry(
    ...     telemetry, gps, corners, corner_id=5
    ... )
    >>> # Analyze braking at corner 5
    >>> max_brake = corner_data['pbrake_f'].max()
    """
    corner = corners[corners['corner_id'] == corner_id].iloc[0]

    # Convert distance to approximate degrees
    # 1 degree latitude ≈ 111 km
    window_deg = window_distance / 111000

    # Find GPS points near corner
    near_corner = (
        (np.abs(gps_data['latitude'] - corner['latitude']) < window_deg) &
        (np.abs(gps_data['longitude'] - corner['longitude']) < window_deg)
    )

    corner_gps = gps_data[near_corner]

    if len(corner_gps) == 0:
        raise ValueError(f"No GPS data found near corner {corner_id}")

    # Merge with telemetry based on timestamp
    # This assumes both dataframes have timestamp column
    corner_telemetry = telemetry.merge(
        corner_gps[['timestamp', 'latitude', 'longitude']],
        on='timestamp',
        how='inner'
    )

    if verbose:
        print(f"Corner {corner_id}: Extracted {len(corner_telemetry)} telemetry points")

    return corner_telemetry


def validate_corner_identification(
    corners: pd.DataFrame,
    expected_range: Tuple[int, int] = (8, 15),
    track_name: str = "Unknown"
) -> bool:
    """
    Validate that corner identification results are reasonable.

    Parameters
    ----------
    corners : pd.DataFrame
        Output from identify_corners_from_gps()
    expected_range : tuple of int, default=(8, 15)
        (min_corners, max_corners) expected for track
    track_name : str, default="Unknown"
        Track name for error messages

    Returns
    -------
    bool
        True if validation passes

    Raises
    ------
    ValueError
        If corner identification failed validation
    """
    n_corners = len(corners)
    min_expected, max_expected = expected_range

    if n_corners < min_expected:
        raise ValueError(
            f"{track_name}: Found only {n_corners} corners, "
            f"expected at least {min_expected}. "
            "Data quality or clustering parameters may need adjustment."
        )

    if n_corners > max_expected:
        warnings.warn(
            f"{track_name}: Found {n_corners} corners, "
            f"expected at most {max_expected}. "
            "May be detecting false corners."
        )

    # Check for reasonable speed distribution
    if (corners['min_speed'] < 30).sum() > n_corners * 0.5:
        warnings.warn(
            f"{track_name}: More than 50% of corners have very low speeds (<30 km/h). "
            "This may indicate data quality issues."
        )

    # All checks passed
    return True
