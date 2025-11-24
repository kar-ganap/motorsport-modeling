"""
Feature Extractor for Counterfactual Analysis

Extracts controllable and uncontrollable features from race data.
"""

import pandas as pd
import numpy as np
from typing import Dict, List
from scipy import stats


def compute_lap_consistency(laps: pd.DataFrame) -> float:
    """
    Compute lap time consistency (lower std dev = more consistent).

    Args:
        laps: DataFrame with lap_time column

    Returns:
        Standard deviation of lap times (s)
    """
    if len(laps) < 3:
        return np.nan

    # Filter outliers
    median_lt = laps['lap_time'].median()
    clean = laps[laps['lap_time'] < median_lt * 1.3]

    if len(clean) < 3:
        return np.nan

    return clean['lap_time'].std()


def compute_degradation_rate(laps: pd.DataFrame) -> float:
    """
    Compute tire degradation rate (s/lap).

    Args:
        laps: DataFrame with lap_time and lap columns

    Returns:
        Degradation rate in s/lap (positive = getting slower)
    """
    if len(laps) < 3:
        return 0.0

    # Filter outliers
    median_lt = laps['lap_time'].median()
    clean = laps[laps['lap_time'] < median_lt * 1.3].copy()

    if len(clean) < 3:
        return 0.0

    slope, _, _, _, _ = stats.linregress(clean['lap'], clean['lap_time'])
    return slope


def detect_traffic_laps(driver_laps: pd.DataFrame, threshold: float = 1.5) -> int:
    """
    Count laps affected by traffic (legacy - uses gap columns if available).

    Args:
        driver_laps: Driver's lap data with gap_to_ahead, gap_to_behind
        threshold: Gap threshold in seconds

    Returns:
        Number of laps in traffic
    """
    in_traffic = False

    if 'gap_to_ahead' in driver_laps.columns:
        in_traffic |= (driver_laps['gap_to_ahead'] < threshold)

    if 'gap_to_behind' in driver_laps.columns:
        in_traffic |= (driver_laps['gap_to_behind'] < threshold)

    if isinstance(in_traffic, bool):
        return 0

    return int(in_traffic.sum())


def detect_traffic_from_telemetry(
    telemetry: pd.DataFrame,
    driver_num: int,
    laps: List[int],
    distance_threshold: float = 100.0,
    time_threshold: float = 0.3
) -> int:
    """
    Detect traffic using lap_distance data from telemetry.

    Uses lap_distance (distance along track) to detect when cars are close together.
    Simpler approach: for each lap, check if driver's average distance to nearest car
    is below threshold for significant portion of the lap.

    Args:
        telemetry: Full telemetry data with all drivers (pivoted to wide format)
        driver_num: Driver to analyze
        laps: List of laps to check
        distance_threshold: Distance threshold in meters (default 100m)
        time_threshold: Fraction of lap in traffic to count (default 30%)

    Returns:
        Number of laps affected by traffic
    """
    if 'lap_distance' not in telemetry.columns:
        # No distance data available, return 0
        return 0

    driver_data = telemetry[
        (telemetry['vehicle_number'] == driver_num) &
        (telemetry['lap'].isin(laps))
    ].copy()

    if len(driver_data) == 0:
        return 0

    traffic_laps = 0

    for lap_num in laps:
        # Get driver's lap data
        driver_lap = driver_data[driver_data['lap'] == lap_num].copy()

        if len(driver_lap) == 0:
            continue

        # Filter to rows with valid lap_distance
        driver_lap = driver_lap[driver_lap['lap_distance'].notna()]

        if len(driver_lap) < 10:  # Need minimum samples
            continue

        # Get all other cars for this lap
        other_cars = telemetry[
            (telemetry['vehicle_number'] != driver_num) &
            (telemetry['lap'] == lap_num) &
            (telemetry['lap_distance'].notna())
        ].copy()

        if len(other_cars) == 0:
            continue

        # For each driver sample, find distance to nearest car
        traffic_samples = 0
        total_samples = 0

        # Sample every 10th point for speed
        for idx in range(0, len(driver_lap), 10):
            row = driver_lap.iloc[idx]
            driver_dist = row['lap_distance']

            total_samples += 1

            # Find nearest car by lap_distance
            # Note: lap_distance resets each lap, so we can use simple distance
            distances = np.abs(other_cars['lap_distance'] - driver_dist)
            min_distance = distances.min()

            # If within threshold, count as traffic
            if min_distance < distance_threshold:
                traffic_samples += 1

        # If more than time_threshold of lap was in traffic, count the lap
        if total_samples > 0 and (traffic_samples / total_samples) > time_threshold:
            traffic_laps += 1

    return traffic_laps


def compute_baseline_pace(driver_laps: pd.DataFrame, early_laps: int = 5) -> float:
    """
    Compute baseline pace from early stint (before degradation/fatigue).

    Args:
        driver_laps: Driver's lap data
        early_laps: Number of early laps to use for baseline

    Returns:
        Median lap time from early stint (s)
    """
    max_lap = driver_laps['lap'].max()
    early_end = min(early_laps, max_lap)
    early_stint = driver_laps[driver_laps['lap'] <= early_end]

    if len(early_stint) < 2:
        # Fallback to all laps if not enough early data
        return driver_laps['lap_time'].median()

    # Filter outliers
    median_lt = early_stint['lap_time'].median()
    clean = early_stint[early_stint['lap_time'] < median_lt * 1.3]

    if len(clean) < 2:
        return early_stint['lap_time'].median()

    return clean['lap_time'].median()


def extract_driver_features(
    driver_num: int,
    race_data: pd.DataFrame,
    stint: str = 'full',
    telemetry: pd.DataFrame = None
) -> Dict[str, float]:
    """
    Extract controllable features and compute deviation from baseline.

    Args:
        driver_num: Driver vehicle number
        race_data: Full race data (lap times)
        stint: Which stint to analyze ('early', 'mid', 'late', 'full')
        telemetry: Optional telemetry data for GPS-based traffic detection

    Returns:
        Dictionary with:
        - controllable_* features (degradation, consistency, traffic)
        - baseline_pace: early-stint pace (uncontrollable)
        - avg_lap_time: average lap time (for reference)
        - lap_time_delta: deviation from baseline (TARGET for model)
        - final_position: race result
    """
    driver_laps = race_data[race_data['vehicle_number'] == driver_num].copy()

    if len(driver_laps) == 0:
        raise ValueError(f"No data found for driver #{driver_num}")

    # Store full lap data for baseline computation
    full_laps = driver_laps.copy()

    # Filter by stint if requested (for degradation/consistency computation)
    max_lap = driver_laps['lap'].max()
    if stint == 'early':
        driver_laps = driver_laps[driver_laps['lap'] <= min(5, max_lap)]
    elif stint == 'mid':
        mid_start = min(6, max_lap)
        mid_end = min(15, max_lap)
        driver_laps = driver_laps[driver_laps['lap'].between(mid_start, mid_end)]
    elif stint == 'late':
        late_start = min(16, max_lap)
        driver_laps = driver_laps[driver_laps['lap'] >= late_start]

    # Get final state
    final_lap = driver_laps['lap'].max()
    final_state = driver_laps[driver_laps['lap'] == final_lap].iloc[0]

    # BASELINE PACE (from early stint - represents car + driver baseline)
    baseline_pace = compute_baseline_pace(full_laps)

    # TRAFFIC DETECTION
    # Use GPS-based detection if telemetry available, otherwise fallback to gap-based
    if telemetry is not None and len(telemetry) > 0:
        laps_to_check = list(driver_laps['lap'].unique())
        traffic_laps_count = detect_traffic_from_telemetry(telemetry, driver_num, laps_to_check)
    else:
        traffic_laps_count = detect_traffic_laps(driver_laps)

    # CONTROLLABLE FEATURES (driver can influence)
    controllable = {
        'degradation_rate': compute_degradation_rate(driver_laps),  # Tire management
        'consistency': compute_lap_consistency(driver_laps),         # Driving precision
        'traffic_laps': traffic_laps_count,                         # Positioning to avoid traffic
    }

    # AVERAGE PACE (for the analyzed stint)
    avg_lap_time = driver_laps['lap_time'].median()

    # DEVIATION FROM BASELINE (what controllable factors caused)
    # Positive = slower than baseline (degradation/traffic/inconsistency)
    lap_time_delta = avg_lap_time - baseline_pace

    # METADATA
    metadata = {
        'baseline_pace': baseline_pace,
        'avg_lap_time': avg_lap_time,
        'lap_time_delta': lap_time_delta,
        'final_position': int(final_state.get('position', 0)),
    }

    return {
        **{'controllable_' + k: v for k, v in controllable.items()},
        **metadata,
    }


def extract_race_features(
    race_data: pd.DataFrame,
    stint: str = 'full',
    telemetry: pd.DataFrame = None,
    analytics_data: pd.DataFrame = None
) -> pd.DataFrame:
    """
    Extract features for all drivers in a race.

    Args:
        race_data: Full race data (lap times)
        stint: Which stint to analyze
        telemetry: Optional telemetry data for GPS-based traffic detection
        analytics_data: Optional analytics DataFrame with corrected positions

    Returns:
        DataFrame with one row per driver and feature columns
    """
    # Always calculate fallback positions first (this is the most reliable method)
    # Get max laps completed per driver
    max_laps_per_driver = race_data.groupby('vehicle_number')['lap'].max().reset_index()
    max_laps_per_driver.columns = ['vehicle_number', 'max_laps']

    # Get total time per driver
    total_times = race_data.groupby('vehicle_number')['lap_time'].sum().reset_index()
    total_times.columns = ['vehicle_number', 'total_time']

    # Merge and sort by: (1) max laps DESC, (2) total time ASC
    standings = max_laps_per_driver.merge(total_times, on='vehicle_number')
    standings = standings.sort_values(
        ['max_laps', 'total_time'],
        ascending=[False, True]
    )
    standings['final_position'] = range(1, len(standings) + 1)

    # Create a lookup dict from calculated positions
    position_lookup = dict(zip(standings['vehicle_number'], standings['final_position']))

    # If analytics data is provided, override positions for drivers that exist in analytics
    # (but keep fallback for drivers not in analytics)
    if analytics_data is not None:
        final_lap = analytics_data['lap'].max()
        analytics_final = analytics_data[analytics_data['lap'] == final_lap][['vehicle_number', 'position']]
        analytics_positions = dict(zip(analytics_final['vehicle_number'], analytics_final['position']))

        # Update position_lookup with analytics positions (only for drivers that exist in analytics)
        for veh_num, pos in analytics_positions.items():
            position_lookup[veh_num] = pos

    features = []

    for driver_num in sorted(race_data['vehicle_number'].unique()):
        try:
            driver_features = extract_driver_features(driver_num, race_data, stint, telemetry)
            driver_features['vehicle_number'] = driver_num
            # Override final_position with looked-up value (from analytics if available, fallback otherwise)
            driver_features['final_position'] = position_lookup.get(driver_num, 0)
            features.append(driver_features)
        except Exception as e:
            print(f"Warning: Could not extract features for driver #{driver_num}: {e}")

    df = pd.DataFrame(features)

    # Fill NaN consistency values with field median
    # This handles drivers with <3 laps who can't compute consistency
    if 'controllable_consistency' in df.columns:
        median_consistency = df['controllable_consistency'].median()
        if pd.notna(median_consistency):
            nan_count = df['controllable_consistency'].isna().sum()
            if nan_count > 0:
                df['controllable_consistency'] = df['controllable_consistency'].fillna(median_consistency)
                print(f"  Filled {nan_count} NaN consistency value(s) with field median ({median_consistency:.3f}s)")

    return df
