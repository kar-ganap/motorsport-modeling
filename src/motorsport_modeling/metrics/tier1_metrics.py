"""
Tier 1 Technique Metrics for real-time driver coaching.

Metrics:
1. Consistency - σ of lap times
2. Coasting % - time neither on throttle nor brake
3. Braking smoothness - brake pressure oscillations per corner
4. Throttle timing - time from apex to full throttle
5. G-force utilization - mean combined G

Usage:
    from motorsport_modeling.metrics.tier1_metrics import compute_all_metrics

    metrics = compute_all_metrics(telemetry_df, lap_times_df)
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, Tuple


def compute_consistency(
    lap_times: pd.DataFrame,
    vehicle_number: int,
    exclude_first_n: int = 2
) -> Dict:
    """
    Compute lap time consistency (standard deviation).

    Lower σ = more consistent driver.

    Parameters
    ----------
    lap_times : pd.DataFrame
        DataFrame with vehicle_number, lap, lap_time columns
    vehicle_number : int
        Car number to analyze
    exclude_first_n : int
        Exclude first N laps (warmup)

    Returns
    -------
    dict
        - std: standard deviation of lap times (seconds)
        - cv: coefficient of variation (%)
        - mean: mean lap time
        - n_laps: number of laps analyzed
    """
    driver_laps = lap_times[lap_times['vehicle_number'] == vehicle_number].copy()

    # Exclude warmup laps
    driver_laps = driver_laps[driver_laps['lap'] > exclude_first_n]

    if len(driver_laps) < 3:
        return {'std': np.nan, 'cv': np.nan, 'mean': np.nan, 'n_laps': 0}

    # Get lap time column
    if 'lap_time' in driver_laps.columns:
        times = driver_laps['lap_time']
    elif 'value' in driver_laps.columns:
        times = driver_laps['value'] / 1000  # Convert ms to seconds
    else:
        return {'std': np.nan, 'cv': np.nan, 'mean': np.nan, 'n_laps': 0}

    times = times.dropna()

    return {
        'std': float(times.std()),
        'cv': float(100 * times.std() / times.mean()),
        'mean': float(times.mean()),
        'n_laps': len(times)
    }


def compute_coasting_pct(
    telemetry: pd.DataFrame,
    vehicle_number: int,
    lap: Optional[int] = None,
    throttle_threshold: float = 5.0,
    brake_threshold: float = 5.0
) -> Dict:
    """
    Compute coasting percentage - time neither on throttle nor brake.

    From data_guide.md: "Count time with ath < 5 AND pbrake_f < 5"

    Higher coasting % may indicate:
    - Conserving tires
    - Loss of confidence
    - Anticipating corner entry

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry with throttle/aps/ath and pbrake_f columns
    vehicle_number : int
        Car number
    lap : int, optional
        Specific lap (if None, compute for all laps)
    throttle_threshold : float
        Throttle below this = off (default 5%)
    brake_threshold : float
        Brake below this = off (default 5 bar)

    Returns
    -------
    dict
        - coasting_pct: percentage of time coasting
        - total_samples: number of samples analyzed
    """
    df = telemetry[telemetry['vehicle_number'] == vehicle_number].copy()

    if lap is not None:
        df = df[df['lap'] == lap]

    if len(df) == 0:
        return {'coasting_pct': np.nan, 'total_samples': 0}

    # Get throttle column
    throttle_col = None
    for col in ['throttle', 'ath', 'aps']:
        if col in df.columns:
            throttle_col = col
            break

    if throttle_col is None or 'pbrake_f' not in df.columns:
        return {'coasting_pct': np.nan, 'total_samples': 0}

    # Calculate coasting
    throttle_off = df[throttle_col] < throttle_threshold
    brake_off = df['pbrake_f'] < brake_threshold
    coasting = throttle_off & brake_off

    # Only count valid samples (both signals present)
    valid = df[throttle_col].notna() & df['pbrake_f'].notna()

    if valid.sum() == 0:
        return {'coasting_pct': np.nan, 'total_samples': 0}

    coasting_pct = 100 * coasting.sum() / valid.sum()

    return {
        'coasting_pct': float(coasting_pct),
        'total_samples': int(valid.sum())
    }


def compute_braking_smoothness(
    telemetry: pd.DataFrame,
    vehicle_number: int,
    lap: Optional[int] = None,
    oscillation_threshold: float = 5.0
) -> Dict:
    """
    Compute braking consistency - CV of peak brake pressure across braking events.

    Lower CV = more consistent braking = better technique.

    This measures how repeatable a driver's braking is. Pro drivers hit
    similar peak pressures at each corner; inconsistent drivers vary wildly.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry with pbrake_f column
    vehicle_number : int
        Car number
    lap : int, optional
        Specific lap
    oscillation_threshold : float
        Not used (kept for API compatibility)

    Returns
    -------
    dict
        - peak_brake_cv: coefficient of variation of peak brake pressures
        - mean_peak_brake: mean peak brake pressure (bar)
        - braking_events: number of distinct braking zones
        - oscillations_per_event: (deprecated) kept for compatibility
    """
    df = telemetry[telemetry['vehicle_number'] == vehicle_number].copy()

    if lap is not None:
        df = df[df['lap'] == lap]

    if 'pbrake_f' not in df.columns or len(df) == 0:
        return {
            'peak_brake_cv': np.nan,
            'mean_peak_brake': np.nan,
            'braking_events': np.nan,
            'oscillations_per_event': np.nan
        }

    # Sort by time
    if 'time' in df.columns:
        df = df.sort_values('time')
    elif 'meta_time' in df.columns:
        df = df.sort_values('meta_time')

    brake = df['pbrake_f'].dropna().values

    if len(brake) < 10:
        return {
            'peak_brake_cv': np.nan,
            'mean_peak_brake': np.nan,
            'braking_events': 0,
            'oscillations_per_event': 0
        }

    # Find braking events and their peak pressures
    braking = brake > 10  # Significant braking threshold
    braking_starts = np.where(np.diff(braking.astype(int)) == 1)[0]
    braking_ends = np.where(np.diff(braking.astype(int)) == -1)[0]

    # Align starts and ends
    if len(braking_starts) == 0 or len(braking_ends) == 0:
        return {
            'peak_brake_cv': np.nan,
            'mean_peak_brake': np.nan,
            'braking_events': 0,
            'oscillations_per_event': 0
        }

    # Ensure we have complete events
    if braking_ends[0] < braking_starts[0]:
        braking_ends = braking_ends[1:]
    if len(braking_starts) > len(braking_ends):
        braking_starts = braking_starts[:len(braking_ends)]

    # Get peak pressure for each braking event
    peak_pressures = []
    for start, end in zip(braking_starts, braking_ends):
        if end > start:
            peak = brake[start:end].max()
            if peak > 15:  # Must be significant braking
                peak_pressures.append(peak)

    if len(peak_pressures) < 3:
        return {
            'peak_brake_cv': np.nan,
            'mean_peak_brake': np.nan,
            'braking_events': len(peak_pressures),
            'oscillations_per_event': 0
        }

    peak_pressures = np.array(peak_pressures)
    mean_peak = peak_pressures.mean()
    cv = peak_pressures.std() / mean_peak * 100 if mean_peak > 0 else np.nan

    return {
        'peak_brake_cv': float(cv),
        'mean_peak_brake': float(mean_peak),
        'braking_events': len(peak_pressures),
        'oscillations_per_event': float(cv)  # Use CV as the main metric
    }


def compute_throttle_timing(
    telemetry: pd.DataFrame,
    vehicle_number: int,
    lap: Optional[int] = None,
    full_throttle_threshold: float = 90.0
) -> Dict:
    """
    Compute throttle quality metrics based on research-validated patterns.

    Key metrics:
    1. Lift-off count: Number of throttle decreases during acceleration phases
       - "throttle should only be going up, never down, 99% of the time"
       - Fewer lift-offs = better traction management
    2. Full throttle percentage: Time spent at >90% throttle
       - F1-validated metric, correlates with lap time
    3. Throttle efficiency: Correlation between throttle and longitudinal G

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry with throttle and accx_can columns
    vehicle_number : int
        Car number
    lap : int, optional
        Specific lap
    full_throttle_threshold : float
        Throttle above this = full (default 90%)

    Returns
    -------
    dict
        - lift_off_count: number of throttle lift-offs during acceleration
        - full_throttle_pct: percentage of time at full throttle
        - throttle_efficiency: correlation of throttle vs longitudinal G
        - mean_apex_to_throttle_ms: lift_off_count (for backward compatibility)
        - corners_detected: number of throttle application events
    """
    df = telemetry[telemetry['vehicle_number'] == vehicle_number].copy()

    if lap is not None:
        df = df[df['lap'] == lap]

    # Get throttle column
    throttle_col = None
    for col in ['throttle', 'ath', 'aps']:
        if col in df.columns:
            throttle_col = col
            break

    if throttle_col is None:
        return {
            'lift_off_count': np.nan,
            'full_throttle_pct': np.nan,
            'throttle_efficiency': np.nan,
            'mean_apex_to_throttle_ms': np.nan,
            'corners_detected': 0
        }

    if len(df) < 20:
        return {
            'lift_off_count': np.nan,
            'full_throttle_pct': np.nan,
            'throttle_efficiency': np.nan,
            'mean_apex_to_throttle_ms': np.nan,
            'corners_detected': 0
        }

    # Sort by time
    time_col = 'time' if 'time' in df.columns else 'meta_time'
    if time_col not in df.columns:
        return {
            'lift_off_count': np.nan,
            'full_throttle_pct': np.nan,
            'throttle_efficiency': np.nan,
            'mean_apex_to_throttle_ms': np.nan,
            'corners_detected': 0
        }

    df = df.sort_values(time_col).reset_index(drop=True)

    throttle = df[throttle_col].dropna().values

    if len(throttle) < 20:
        return {
            'lift_off_count': np.nan,
            'full_throttle_pct': np.nan,
            'throttle_efficiency': np.nan,
            'mean_apex_to_throttle_ms': np.nan,
            'corners_detected': 0
        }

    # =========================================================================
    # Metric 1: Lift-off count during acceleration phases
    # =========================================================================
    # Find acceleration phases (throttle > 20% and generally increasing)
    in_acceleration = throttle > 20
    throttle_change = np.diff(throttle)

    # Count significant lift-offs (>5% decrease) during acceleration
    lift_offs = 0
    for i in range(1, len(throttle)):
        if in_acceleration[i] and in_acceleration[i-1]:
            # We're in an acceleration phase
            if throttle[i] < throttle[i-1] - 5:  # Significant decrease
                lift_offs += 1

    # Normalize by number of throttle applications
    low_throttle = throttle < 20
    applications = np.diff(low_throttle.astype(int)) == -1
    n_applications = max(1, int(applications.sum()))

    lift_off_per_application = lift_offs / n_applications

    # =========================================================================
    # Metric 2: Full throttle percentage
    # =========================================================================
    full_throttle_samples = (throttle >= full_throttle_threshold).sum()
    full_throttle_pct = 100 * full_throttle_samples / len(throttle)

    # =========================================================================
    # Metric 3: Throttle efficiency (throttle vs longitudinal G correlation)
    # =========================================================================
    throttle_efficiency = np.nan
    if 'accx_can' in df.columns:
        # Get aligned data
        valid_mask = df[throttle_col].notna() & df['accx_can'].notna()
        if valid_mask.sum() > 10:
            throttle_valid = df.loc[valid_mask, throttle_col].values
            accx_valid = df.loc[valid_mask, 'accx_can'].values

            # Only consider when throttle is being applied (>20%)
            accel_mask = throttle_valid > 20
            if accel_mask.sum() > 10:
                # Correlation: higher throttle should give higher forward G
                corr = np.corrcoef(throttle_valid[accel_mask],
                                   accx_valid[accel_mask])[0, 1]
                throttle_efficiency = float(corr) if not np.isnan(corr) else np.nan

    return {
        'lift_off_count': float(lift_off_per_application),
        'full_throttle_pct': float(full_throttle_pct),
        'throttle_efficiency': throttle_efficiency,
        'mean_apex_to_throttle_ms': float(lift_off_per_application),  # Backward compat
        'corners_detected': n_applications
    }


def compute_g_force_utilization(
    telemetry: pd.DataFrame,
    vehicle_number: int,
    lap: Optional[int] = None
) -> Dict:
    """
    Compute G-force utilization - mean combined lateral + longitudinal G.

    Higher G = extracting more grip from tires.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry with accx_can, accy_can columns
    vehicle_number : int
        Car number
    lap : int, optional
        Specific lap

    Returns
    -------
    dict
        - mean_combined_g: mean sqrt(ax^2 + ay^2)
        - max_combined_g: maximum combined G
        - mean_lateral_g: mean |ay|
        - mean_longitudinal_g: mean |ax|
    """
    df = telemetry[telemetry['vehicle_number'] == vehicle_number].copy()

    if lap is not None:
        df = df[df['lap'] == lap]

    if 'accx_can' not in df.columns or 'accy_can' not in df.columns:
        return {
            'mean_combined_g': np.nan,
            'max_combined_g': np.nan,
            'mean_lateral_g': np.nan,
            'mean_longitudinal_g': np.nan
        }

    ax = df['accx_can'].dropna()
    ay = df['accy_can'].dropna()

    # Align indices
    common_idx = ax.index.intersection(ay.index)
    ax = ax.loc[common_idx]
    ay = ay.loc[common_idx]

    if len(ax) == 0:
        return {
            'mean_combined_g': np.nan,
            'max_combined_g': np.nan,
            'mean_lateral_g': np.nan,
            'mean_longitudinal_g': np.nan
        }

    combined_g = np.sqrt(ax**2 + ay**2)

    return {
        'mean_combined_g': float(combined_g.mean()),
        'max_combined_g': float(combined_g.max()),
        'mean_lateral_g': float(ay.abs().mean()),
        'mean_longitudinal_g': float(ax.abs().mean())
    }


def compute_all_metrics(
    telemetry: pd.DataFrame,
    lap_times: pd.DataFrame,
    vehicle_number: int,
    lap: Optional[int] = None
) -> Dict:
    """
    Compute all Tier 1 metrics for a driver.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry
    lap_times : pd.DataFrame
        Lap times with vehicle_number, lap, lap_time/value columns
    vehicle_number : int
        Car number
    lap : int, optional
        Specific lap (if None, uses all laps for some metrics)

    Returns
    -------
    dict
        All Tier 1 metrics
    """
    metrics = {
        'vehicle_number': vehicle_number,
        'lap': lap
    }

    # 1. Consistency (uses all laps)
    consistency = compute_consistency(lap_times, vehicle_number)
    metrics['consistency_std'] = consistency['std']
    metrics['consistency_cv'] = consistency['cv']

    # 2. Coasting %
    coasting = compute_coasting_pct(telemetry, vehicle_number, lap)
    metrics['coasting_pct'] = coasting['coasting_pct']

    # 3. Braking smoothness
    braking = compute_braking_smoothness(telemetry, vehicle_number, lap)
    metrics['brake_oscillations'] = braking['oscillation_count']
    metrics['brake_oscillations_per_event'] = braking['oscillations_per_event']

    # 4. Throttle timing
    throttle = compute_throttle_timing(telemetry, vehicle_number, lap)
    metrics['apex_to_throttle_ms'] = throttle['mean_apex_to_throttle_ms']

    # 5. G-force utilization
    g_force = compute_g_force_utilization(telemetry, vehicle_number, lap)
    metrics['mean_combined_g'] = g_force['mean_combined_g']
    metrics['max_combined_g'] = g_force['max_combined_g']

    return metrics


def compute_metrics_for_race(
    telemetry: pd.DataFrame,
    lap_times: pd.DataFrame,
    per_lap: bool = False
) -> pd.DataFrame:
    """
    Compute all metrics for all drivers in a race.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Wide format telemetry for entire race
    lap_times : pd.DataFrame
        Lap times for entire race
    per_lap : bool
        If True, compute metrics per lap; if False, aggregate over race

    Returns
    -------
    pd.DataFrame
        Metrics for all drivers (and laps if per_lap=True)
    """
    results = []

    vehicles = telemetry['vehicle_number'].unique()

    for veh in vehicles:
        if per_lap:
            laps = telemetry[telemetry['vehicle_number'] == veh]['lap'].unique()
            for lap in laps:
                metrics = compute_all_metrics(telemetry, lap_times, veh, lap)
                results.append(metrics)
        else:
            metrics = compute_all_metrics(telemetry, lap_times, veh, None)
            results.append(metrics)

    return pd.DataFrame(results)
