"""
Tier 1 Core Metrics for driver performance analysis.

These metrics provide fundamental measures of driver performance:
1. Consistency (lap time standard deviation)
2. Coasting time (percentage of lap not on throttle or brake)
3. Braking performance (peak pressure and brake pulses)
4. Throttle timing (responsiveness after slow points)
5. Steering smoothness (jerk/rate of change)

Usage:
    from motorsport_modeling.metrics.tier1 import (
        calculate_consistency,
        calculate_coasting_time,
        analyze_braking_performance,
        calculate_throttle_timing,
        calculate_steering_smoothness,
        calculate_all_tier1_metrics
    )
"""

import pandas as pd
import numpy as np
from typing import Union, List, Optional, Dict, Any
from pathlib import Path
from scipy.signal import find_peaks


def calculate_consistency(
    lap_times: Union[pd.Series, List[float], np.ndarray],
    exclude_first_n: int = 1,
    exclude_last_n: int = 0,
    verbose: bool = False
) -> Dict[str, float]:
    """
    Calculate lap time consistency (lower is better).

    Measures how consistently a driver can repeat lap times, excluding
    outliers like in-lap, out-lap, and safety car laps.

    Parameters
    ----------
    lap_times : array-like
        Lap times in seconds
    exclude_first_n : int, default=1
        Exclude first N laps (out-lap, tire warming)
    exclude_last_n : int, default=0
        Exclude last N laps (in-lap)
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        - std: Standard deviation of lap times
        - cv: Coefficient of variation (std/mean)
        - range: Max - min lap time
        - mean: Mean lap time
        - n_laps: Number of laps analyzed
    """
    lap_times = np.array(lap_times)

    # Exclude specified laps
    if exclude_first_n > 0:
        lap_times = lap_times[exclude_first_n:]
    if exclude_last_n > 0:
        lap_times = lap_times[:-exclude_last_n]

    if len(lap_times) < 3:
        raise ValueError(f"Need at least 3 laps for consistency, got {len(lap_times)}")

    # Filter extreme outliers (>3 sigma or >10s slower than median)
    median_time = np.median(lap_times)
    lap_times = lap_times[lap_times < median_time + 10]  # Max 10s slower than median

    if len(lap_times) < 3:
        raise ValueError("Too few laps after outlier filtering")

    std = np.std(lap_times)
    mean = np.mean(lap_times)
    cv = std / mean
    range_val = np.max(lap_times) - np.min(lap_times)

    result = {
        'std': std,
        'cv': cv,
        'range': range_val,
        'mean': mean,
        'n_laps': len(lap_times)
    }

    if verbose:
        print(f"Consistency Analysis:")
        print(f"  Laps analyzed: {len(lap_times)}")
        print(f"  Mean lap time: {mean:.3f}s")
        print(f"  Std deviation: {std:.3f}s")
        print(f"  CV: {cv:.4f}")
        print(f"  Range: {range_val:.3f}s")

    return result


def calculate_coasting_time(
    telemetry: pd.DataFrame,
    throttle_col: str = 'ath',
    brake_col: str = 'pbrake_f',
    throttle_threshold: float = 5.0,  # % throttle considered "off"
    brake_threshold: float = 2.0,     # bar considered "off"
    verbose: bool = False
) -> Dict[str, float]:
    """
    Calculate percentage of time spent coasting (no throttle, no brake).

    Coasting is generally inefficient in racing - you should be either
    accelerating or braking. High coasting time indicates hesitation
    or poor commitment.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data with throttle and brake columns
    throttle_col : str, default='ath'
        Column name for throttle position (0-100%)
    brake_col : str, default='pbrake_f'
        Column name for brake pressure (bar)
    throttle_threshold : float, default=5.0
        Throttle below this is considered "off"
    brake_threshold : float, default=2.0
        Brake below this is considered "off"
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        - coasting_pct: Percentage of time coasting
        - throttle_pct: Percentage of time on throttle
        - brake_pct: Percentage of time on brake
        - overlap_pct: Percentage with both throttle and brake
        - n_points: Number of data points analyzed
    """
    df = telemetry.copy()

    # Ensure columns exist
    if throttle_col not in df.columns:
        raise ValueError(f"Throttle column '{throttle_col}' not found")
    if brake_col not in df.columns:
        raise ValueError(f"Brake column '{brake_col}' not found")

    # Get valid rows
    df = df.dropna(subset=[throttle_col, brake_col])

    if len(df) == 0:
        raise ValueError("No valid telemetry data after removing NaN")

    # Classify each point
    throttle_on = df[throttle_col] > throttle_threshold
    brake_on = df[brake_col] > brake_threshold

    coasting = ~throttle_on & ~brake_on
    overlap = throttle_on & brake_on

    n_points = len(df)

    result = {
        'coasting_pct': 100 * coasting.sum() / n_points,
        'throttle_pct': 100 * throttle_on.sum() / n_points,
        'brake_pct': 100 * brake_on.sum() / n_points,
        'overlap_pct': 100 * overlap.sum() / n_points,
        'n_points': n_points
    }

    if verbose:
        print(f"Coasting Analysis:")
        print(f"  Data points: {n_points}")
        print(f"  Throttle on: {result['throttle_pct']:.1f}%")
        print(f"  Brake on: {result['brake_pct']:.1f}%")
        print(f"  Coasting: {result['coasting_pct']:.1f}%")
        print(f"  Overlap: {result['overlap_pct']:.1f}%")

    return result


def analyze_braking_performance(
    telemetry: pd.DataFrame,
    brake_col: str = 'pbrake_f',
    min_brake_pressure: float = 20.0,
    verbose: bool = False
) -> Dict[str, float]:
    """
    Analyze braking performance metrics.

    Measures peak brake pressure and counts brake pulses (releasing and
    reapplying brake during a single braking event), which indicates
    lack of confidence or trail braking technique issues.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data with brake column
    brake_col : str, default='pbrake_f'
        Column name for brake pressure (bar)
    min_brake_pressure : float, default=20.0
        Minimum pressure to consider as braking
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        - max_brake: Maximum brake pressure (bar)
        - mean_brake: Mean brake pressure when braking
        - n_braking_events: Number of distinct braking zones
        - pulse_count: Number of brake pulses (release and reapply)
        - pulse_per_event: Average pulses per braking event
    """
    df = telemetry.copy()

    if brake_col not in df.columns:
        raise ValueError(f"Brake column '{brake_col}' not found")

    brake = df[brake_col].dropna().values

    if len(brake) == 0:
        raise ValueError("No brake data found")

    # Overall max brake
    max_brake = np.max(brake)

    # Mean when braking
    braking_mask = brake > min_brake_pressure
    if braking_mask.sum() > 0:
        mean_brake = np.mean(brake[braking_mask])
    else:
        mean_brake = 0

    # Count braking events (transitions from not-braking to braking)
    braking = brake > min_brake_pressure
    braking_diff = np.diff(braking.astype(int))
    n_braking_events = np.sum(braking_diff == 1)  # 0 -> 1 transitions

    # Count pulses within braking events
    # A pulse is when brake drops significantly and comes back up
    pulse_count = 0
    in_braking_zone = False
    min_in_zone = 0

    for i in range(1, len(brake)):
        if brake[i] > min_brake_pressure and not in_braking_zone:
            # Started braking
            in_braking_zone = True
            min_in_zone = brake[i]
        elif brake[i] > min_brake_pressure and in_braking_zone:
            # Still braking - check for pulse
            if brake[i] < min_in_zone * 0.5:  # Dropped to <50% of previous
                min_in_zone = brake[i]
            elif brake[i] > min_in_zone * 1.3:  # Rose >30% after drop
                pulse_count += 1
                min_in_zone = brake[i]
            else:
                min_in_zone = max(min_in_zone, brake[i])
        elif brake[i] <= min_brake_pressure:
            # Stopped braking
            in_braking_zone = False

    pulse_per_event = pulse_count / max(n_braking_events, 1)

    result = {
        'max_brake': max_brake,
        'mean_brake': mean_brake,
        'n_braking_events': n_braking_events,
        'pulse_count': pulse_count,
        'pulse_per_event': pulse_per_event
    }

    if verbose:
        print(f"Braking Performance:")
        print(f"  Max pressure: {max_brake:.1f} bar")
        print(f"  Mean (when braking): {mean_brake:.1f} bar")
        print(f"  Braking events: {n_braking_events}")
        print(f"  Brake pulses: {pulse_count}")
        print(f"  Pulses per event: {pulse_per_event:.2f}")

    return result


def calculate_throttle_timing(
    telemetry: pd.DataFrame,
    throttle_col: str = 'ath',
    speed_col: str = 'speed',
    full_throttle_threshold: float = 95.0,
    verbose: bool = False
) -> Dict[str, float]:
    """
    Calculate throttle application timing after slow points.

    Measures how quickly a driver gets back to full throttle after
    minimum speed points (apex or chicane). Fast throttle application
    indicates commitment and confidence.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data with throttle and speed columns
    throttle_col : str, default='ath'
        Column name for throttle position (0-100%)
    speed_col : str, default='speed'
        Column name for speed (km/h)
    full_throttle_threshold : float, default=95.0
        Throttle above this is "full throttle"
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        - mean_time_to_full: Mean time from apex to full throttle (seconds)
        - median_time_to_full: Median time to full throttle
        - n_corners: Number of corners analyzed
        - full_throttle_pct: Percentage of time at full throttle
    """
    df = telemetry.copy()

    if throttle_col not in df.columns:
        raise ValueError(f"Throttle column '{throttle_col}' not found")

    # Calculate full throttle percentage regardless of speed data
    throttle = df[throttle_col].dropna().values
    full_throttle_pct = 100 * np.sum(throttle >= full_throttle_threshold) / len(throttle)

    # If we don't have speed data, return limited metrics
    if speed_col not in df.columns or df[speed_col].isna().all():
        result = {
            'mean_time_to_full': np.nan,
            'median_time_to_full': np.nan,
            'n_corners': 0,
            'full_throttle_pct': full_throttle_pct
        }

        if verbose:
            print(f"Throttle Timing (limited - no speed data):")
            print(f"  Full throttle: {full_throttle_pct:.1f}%")
            print(f"  Note: Speed data not available for apex detection")

        return result

    # Get timestamps and ensure proper sorting
    df = df.dropna(subset=[throttle_col, speed_col, 'timestamp']).copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    if len(df) < 100:
        raise ValueError(f"Insufficient data points: {len(df)}")

    # Find speed minima (apexes) using peak finding on inverted speed
    speed = df[speed_col].values

    # Smooth speed for cleaner peaks
    speed_smooth = pd.Series(speed).rolling(5, center=True).mean().fillna(pd.Series(speed)).values

    # Find minima (peaks in inverted speed)
    min_speed = np.min(speed_smooth)
    max_speed = np.max(speed_smooth)
    speed_range = max_speed - min_speed

    if speed_range < 10:
        # Very little speed variation - can't detect corners
        result = {
            'mean_time_to_full': np.nan,
            'median_time_to_full': np.nan,
            'n_corners': 0,
            'full_throttle_pct': full_throttle_pct
        }
        return result

    minima_indices, _ = find_peaks(
        -speed_smooth,
        height=-max_speed + 0.3 * speed_range,  # Only significant minima
        distance=50  # At least 50 points between corners
    )

    # For each minimum, find time to full throttle
    times_to_full = []
    timestamps = pd.to_datetime(df['timestamp'])

    for apex_idx in minima_indices:
        # Look forward from apex
        found_full_throttle = False
        for i in range(apex_idx, min(apex_idx + 200, len(df))):
            if df[throttle_col].iloc[i] >= full_throttle_threshold:
                # Calculate time delta
                time_delta = (timestamps.iloc[i] - timestamps.iloc[apex_idx]).total_seconds()
                if time_delta > 0 and time_delta < 10:  # Sanity check
                    times_to_full.append(time_delta)
                found_full_throttle = True
                break

    if len(times_to_full) == 0:
        result = {
            'mean_time_to_full': np.nan,
            'median_time_to_full': np.nan,
            'n_corners': 0,
            'full_throttle_pct': full_throttle_pct
        }
    else:
        result = {
            'mean_time_to_full': np.mean(times_to_full),
            'median_time_to_full': np.median(times_to_full),
            'n_corners': len(times_to_full),
            'full_throttle_pct': full_throttle_pct
        }

    if verbose:
        print(f"Throttle Timing:")
        print(f"  Corners analyzed: {result['n_corners']}")
        if result['n_corners'] > 0:
            print(f"  Mean time to full throttle: {result['mean_time_to_full']:.3f}s")
            print(f"  Median time to full throttle: {result['median_time_to_full']:.3f}s")
        print(f"  Full throttle: {full_throttle_pct:.1f}%")

    return result


def calculate_steering_smoothness(
    telemetry: pd.DataFrame,
    steering_col: str = 'steer_angle',
    verbose: bool = False
) -> Dict[str, float]:
    """
    Calculate steering smoothness (jerk - rate of change of steering angle).

    Smooth steering indicates better car control and tire management.
    High jerk (sudden steering inputs) indicates corrections and
    potential over-driving.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data with steering column and timestamp
    steering_col : str, default='steer_angle'
        Column name for steering angle (degrees)
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        - mean_jerk: Mean absolute rate of steering change
        - max_jerk: Maximum steering jerk
        - std_jerk: Standard deviation of jerk
        - smoothness_score: 100 - normalized jerk (higher is smoother)
    """
    df = telemetry.copy()

    if steering_col not in df.columns:
        raise ValueError(f"Steering column '{steering_col}' not found")

    # Sort by timestamp and get steering angle
    df = df.dropna(subset=[steering_col, 'timestamp']).copy()
    df = df.sort_values('timestamp').reset_index(drop=True)

    if len(df) < 10:
        raise ValueError(f"Insufficient data points: {len(df)}")

    steering = df[steering_col].values
    timestamps = pd.to_datetime(df['timestamp'])

    # Calculate time deltas in seconds
    time_deltas = timestamps.diff().dt.total_seconds().values[1:]

    # Calculate steering rate of change (velocity)
    steering_diff = np.diff(steering)

    # Avoid division by zero
    valid_mask = time_deltas > 0
    steering_rate = np.zeros_like(steering_diff)
    steering_rate[valid_mask] = steering_diff[valid_mask] / time_deltas[valid_mask]

    # Calculate jerk (rate of change of rate)
    jerk = np.abs(np.diff(steering_rate))

    if len(jerk) == 0:
        raise ValueError("Cannot calculate jerk - insufficient data")

    mean_jerk = np.mean(jerk)
    max_jerk = np.max(jerk)
    std_jerk = np.std(jerk)

    # Normalize to 0-100 score (higher is smoother)
    # Typical racing jerk is 0-1000 deg/s^2, so scale accordingly
    smoothness_score = max(0, 100 - mean_jerk / 10)

    result = {
        'mean_jerk': mean_jerk,
        'max_jerk': max_jerk,
        'std_jerk': std_jerk,
        'smoothness_score': smoothness_score
    }

    if verbose:
        print(f"Steering Smoothness:")
        print(f"  Mean jerk: {mean_jerk:.1f} deg/s^2")
        print(f"  Max jerk: {max_jerk:.1f} deg/s^2")
        print(f"  Std jerk: {std_jerk:.1f} deg/s^2")
        print(f"  Smoothness score: {smoothness_score:.1f}/100")

    return result


def calculate_all_tier1_metrics(
    telemetry: pd.DataFrame,
    lap_times: Optional[Union[pd.Series, List[float]]] = None,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Calculate all Tier 1 metrics for a driver.

    Parameters
    ----------
    telemetry : pd.DataFrame
        Telemetry data with all required columns
    lap_times : array-like, optional
        Lap times in seconds. If None, consistency metric is skipped.
    verbose : bool, default=False
        Print detailed output

    Returns
    -------
    dict
        Dictionary containing all Tier 1 metrics:
        - consistency: Lap time consistency metrics
        - coasting: Coasting time metrics
        - braking: Braking performance metrics
        - throttle: Throttle timing metrics
        - steering: Steering smoothness metrics
        - summary: Summary scores for easy comparison
    """
    results = {}

    if verbose:
        print("=" * 60)
        print("TIER 1 METRICS")
        print("=" * 60)

    # 1. Consistency
    if lap_times is not None:
        try:
            results['consistency'] = calculate_consistency(
                lap_times, verbose=verbose
            )
        except ValueError as e:
            if verbose:
                print(f"Consistency: SKIPPED - {e}")
            results['consistency'] = None
    else:
        results['consistency'] = None

    # 2. Coasting time
    try:
        results['coasting'] = calculate_coasting_time(
            telemetry, verbose=verbose
        )
    except (ValueError, KeyError) as e:
        if verbose:
            print(f"Coasting: SKIPPED - {e}")
        results['coasting'] = None

    # 3. Braking performance
    try:
        results['braking'] = analyze_braking_performance(
            telemetry, verbose=verbose
        )
    except (ValueError, KeyError) as e:
        if verbose:
            print(f"Braking: SKIPPED - {e}")
        results['braking'] = None

    # 4. Throttle timing
    try:
        results['throttle'] = calculate_throttle_timing(
            telemetry, verbose=verbose
        )
    except (ValueError, KeyError) as e:
        if verbose:
            print(f"Throttle: SKIPPED - {e}")
        results['throttle'] = None

    # 5. Steering smoothness
    try:
        results['steering'] = calculate_steering_smoothness(
            telemetry, verbose=verbose
        )
    except (ValueError, KeyError) as e:
        if verbose:
            print(f"Steering: SKIPPED - {e}")
        results['steering'] = None

    # Create summary scores
    summary = {}

    if results['consistency']:
        summary['consistency_score'] = 100 - results['consistency']['std'] * 20  # Lower std = higher score
    else:
        summary['consistency_score'] = None

    if results['coasting']:
        # Use throttle_pct as efficiency score (more throttle = more aggressive)
        summary['efficiency_score'] = results['coasting']['throttle_pct']
    else:
        summary['efficiency_score'] = None

    if results['braking']:
        # Lower pulses per event = more confident braking
        # Score: (1 - pulse_per_event) * 50 to give 0-50 range
        summary['braking_score'] = max(0, 50 - results['braking']['pulse_per_event'] * 50)
    else:
        summary['braking_score'] = None

    if results['throttle']:
        summary['throttle_score'] = results['throttle']['full_throttle_pct']
        # Add throttle timing score - faster is better (lower time = higher score)
        if results['throttle']['median_time_to_full'] and not np.isnan(results['throttle']['median_time_to_full']):
            # Score from 0-100, where 0.2s = 100, 2s = 0
            summary['throttle_timing_score'] = max(0, 100 - (results['throttle']['median_time_to_full'] - 0.2) * 55.5)
        else:
            summary['throttle_timing_score'] = None
    else:
        summary['throttle_score'] = None
        summary['throttle_timing_score'] = None

    if results['steering']:
        summary['smoothness_score'] = results['steering']['smoothness_score']
    else:
        summary['smoothness_score'] = None

    results['summary'] = summary

    if verbose:
        print("\n" + "=" * 60)
        print("SUMMARY SCORES")
        print("=" * 60)
        for key, value in summary.items():
            if value is not None:
                print(f"  {key}: {value:.1f}")
            else:
                print(f"  {key}: N/A")

    return results


# Convenience functions for comparison
def compare_drivers(
    metrics_a: Dict[str, Any],
    metrics_b: Dict[str, Any],
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Compare Tier 1 metrics between two drivers.

    Parameters
    ----------
    metrics_a : dict
        Tier 1 metrics for driver A
    metrics_b : dict
        Tier 1 metrics for driver B
    verbose : bool, default=False
        Print comparison

    Returns
    -------
    dict
        Comparison results showing which driver is better in each metric
    """
    comparison = {}

    summary_a = metrics_a.get('summary', {})
    summary_b = metrics_b.get('summary', {})

    # For each summary metric, determine who's better
    # Higher is better for all summary scores
    for metric in ['consistency_score', 'efficiency_score', 'braking_score',
                   'throttle_score', 'throttle_timing_score', 'smoothness_score']:
        val_a = summary_a.get(metric)
        val_b = summary_b.get(metric)

        if val_a is not None and val_b is not None:
            delta = val_a - val_b
            comparison[metric] = {
                'driver_a': val_a,
                'driver_b': val_b,
                'delta': delta,
                'winner': 'A' if delta > 0 else 'B' if delta < 0 else 'tie'
            }
        else:
            comparison[metric] = {
                'driver_a': val_a,
                'driver_b': val_b,
                'delta': None,
                'winner': 'unknown'
            }

    # Count wins
    a_wins = sum(1 for m in comparison.values() if m['winner'] == 'A')
    b_wins = sum(1 for m in comparison.values() if m['winner'] == 'B')

    comparison['overall'] = {
        'a_wins': a_wins,
        'b_wins': b_wins,
        'overall_winner': 'A' if a_wins > b_wins else 'B' if b_wins > a_wins else 'tie'
    }

    if verbose:
        print("=" * 60)
        print("DRIVER COMPARISON")
        print("=" * 60)
        for metric, result in comparison.items():
            if metric == 'overall':
                continue
            if result['delta'] is not None:
                winner = 'A ✓' if result['winner'] == 'A' else 'B ✓' if result['winner'] == 'B' else 'TIE'
                print(f"  {metric}:")
                print(f"    A: {result['driver_a']:.1f}  B: {result['driver_b']:.1f}  → {winner}")

        print(f"\nOverall: A wins {a_wins}, B wins {b_wins}")
        print(f"Winner: Driver {comparison['overall']['overall_winner']}")

    return comparison
