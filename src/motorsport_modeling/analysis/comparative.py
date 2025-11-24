"""
Comparative Performance Analysis Module

Provides honest, data-driven comparisons of driver performance against field benchmarks.
No speculation or counterfactual simulation - just objective metrics.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DriverMetrics:
    """Structured driver performance metrics for LLM narrative generation."""
    vehicle_number: int
    final_position: int
    gap_to_winner: float
    gap_to_ahead: float

    # Comparison to driver(s) who finished ahead
    ahead_vehicle: Optional[int]  # Vehicle number of driver who finished P-1
    ahead_pace_delta: float       # Average lap time difference (negative = we were slower)
    ahead_deg_delta: float        # Degradation rate difference (positive = we degraded more)
    ahead_traffic_delta: int      # Traffic laps difference

    # Degradation
    driver_deg: float      # s/lap degradation rate
    field_deg: float       # field average degradation (for context)

    # Traffic
    traffic_laps: int
    traffic_cost: float    # total seconds lost to traffic

    # Pace by stint (for identifying where time was lost)
    early_pace: float      # Average lap time laps 1-5
    mid_pace: float        # Average lap time laps 6-15
    late_pace: float       # Average lap time lap 16+

    # Ahead driver's pace (for comparison)
    ahead_early_pace: Optional[float]
    ahead_mid_pace: Optional[float]
    ahead_late_pace: Optional[float]


class FieldBenchmark:
    """
    Compute field-wide performance benchmarks for objective comparison.
    """

    def __init__(self, race_data: pd.DataFrame):
        """
        Initialize with full race data.

        Args:
            race_data: DataFrame with columns: vehicle_number, lap, lap_time, position, etc.
        """
        self.race_data = race_data
        self.benchmarks = self._compute_benchmarks()

    def _compute_benchmarks(self) -> pd.DataFrame:
        """
        Compute per-lap field statistics with safety checks for empty data.

        Returns:
            DataFrame with lap-level field statistics
        """
        import warnings

        per_lap = []

        for lap_num in sorted(self.race_data['lap'].unique()):
            lap_data = self.race_data[self.race_data['lap'] == lap_num].copy()

            # Need at least 3 drivers for meaningful statistics
            if len(lap_data) < 3:
                continue

            # Filter to clean laps (exclude outliers > 1.3x median)
            median_lt = lap_data['lap_time'].median()
            if pd.isna(median_lt):
                continue

            clean = lap_data[lap_data['lap_time'] < median_lt * 1.3]

            if len(clean) >= 3:  # Need minimum for statistics
                # Get top 5 by position
                top5 = clean[clean['position'] <= 5] if 'position' in clean.columns else clean.nsmallest(min(5, len(clean)), 'lap_time')

                # Suppress warnings for mean of potentially empty slice
                with warnings.catch_warnings():
                    warnings.simplefilter("ignore", category=RuntimeWarning)
                    top5_avg = top5['lap_time'].mean() if len(top5) > 0 else clean['lap_time'].min()

                per_lap.append({
                    'lap': lap_num,
                    'field_median': clean['lap_time'].median(),
                    'field_p25': clean['lap_time'].quantile(0.25),
                    'field_p75': clean['lap_time'].quantile(0.75),
                    'top5_avg': top5_avg,
                    'field_count': len(clean),
                })

        return pd.DataFrame(per_lap)

    def get_lap_benchmark(self, lap_num: int) -> Optional[Dict]:
        """Get benchmark data for specific lap."""
        lap_data = self.benchmarks[self.benchmarks['lap'] == lap_num]
        if len(lap_data) > 0:
            return lap_data.iloc[0].to_dict()
        return None


def compute_driver_deltas(
    driver_laps: pd.DataFrame,
    benchmarks: pd.DataFrame
) -> pd.DataFrame:
    """
    Compute driver's performance deltas vs field benchmarks.

    Args:
        driver_laps: DataFrame with driver's lap-by-lap data
        benchmarks: DataFrame from FieldBenchmark

    Returns:
        DataFrame with added delta columns
    """
    merged = driver_laps.merge(benchmarks, on='lap', how='left')

    merged['delta_vs_median'] = merged['lap_time'] - merged['field_median']
    merged['delta_vs_top5'] = merged['lap_time'] - merged['top5_avg']

    return merged


def segment_race(race_data: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Segment race into early/mid/late stints for comparison.

    Args:
        race_data: Full race data

    Returns:
        Dict with 'early', 'mid', 'late' DataFrames
    """
    max_lap = race_data['lap'].max()

    # Define segments
    early_end = min(5, max_lap)
    mid_start = early_end + 1
    mid_end = min(15, max_lap)
    late_start = mid_end + 1

    segments = {
        'early': race_data[race_data['lap'] <= early_end],
        'mid': race_data[race_data['lap'].between(mid_start, mid_end)],
        'late': race_data[race_data['lap'] >= late_start],
    }

    return segments


def detect_traffic_laps(driver_laps: pd.DataFrame, threshold: float = 1.5) -> pd.DataFrame:
    """
    Identify laps where driver was in traffic.

    Args:
        driver_laps: Driver's lap data with gap_to_ahead, gap_to_behind
        threshold: Gap threshold in seconds

    Returns:
        DataFrame with 'in_traffic' boolean column added
    """
    driver_laps = driver_laps.copy()

    # Traffic = close gap ahead OR behind
    driver_laps['in_traffic'] = False

    if 'gap_to_ahead' in driver_laps.columns:
        driver_laps['in_traffic'] |= (driver_laps['gap_to_ahead'] < threshold)

    if 'gap_to_behind' in driver_laps.columns:
        driver_laps['in_traffic'] |= (driver_laps['gap_to_behind'] < threshold)

    return driver_laps


def compute_degradation_rate(laps: pd.DataFrame) -> float:
    """
    Compute pace degradation rate (s/lap).

    Args:
        laps: DataFrame with lap_time and lap columns

    Returns:
        Degradation rate in s/lap (positive = getting slower)
    """
    if len(laps) < 3:
        return 0.0

    # Linear regression: lap_time ~ lap_number
    from scipy import stats

    # Filter clean laps
    median_lt = laps['lap_time'].median()
    clean = laps[laps['lap_time'] < median_lt * 1.3].copy()

    if len(clean) < 3:
        return 0.0

    slope, _, _, _, _ = stats.linregress(clean['lap'], clean['lap_time'])

    return slope


def compute_driver_metrics(
    driver_num: int,
    race_data: pd.DataFrame,
    benchmarks: pd.DataFrame
) -> DriverMetrics:
    """
    Compute comprehensive driver performance metrics with "beat-the-driver-ahead" comparison.

    Args:
        driver_num: Driver vehicle number
        race_data: Full race data
        benchmarks: Field benchmarks from FieldBenchmark

    Returns:
        DriverMetrics object with all computed values
    """
    driver_laps = race_data[race_data['vehicle_number'] == driver_num].copy()

    if len(driver_laps) == 0:
        raise ValueError(f"No data found for driver #{driver_num}")

    # Final position and gaps
    final_lap = driver_laps['lap'].max()
    final_state = driver_laps[driver_laps['lap'] == final_lap].iloc[0]
    final_position = int(final_state.get('position', 0))
    gap_to_ahead = final_state.get('gap_to_ahead', 0.0)

    # Gap to winner
    winner_laps = race_data[race_data['position'] == 1]
    if len(winner_laps) > 0:
        winner_time = winner_laps['cumulative_time'].max()
        driver_time = driver_laps['cumulative_time'].max()
        gap_to_winner = driver_time - winner_time if pd.notna(winner_time) and pd.notna(driver_time) else 0.0
    else:
        gap_to_winner = 0.0

    # Find comparison driver
    # For P1: compare to P2 (to show what made them faster)
    # For others: compare to P-1 (to show what cost them a position)
    if final_position == 1:
        comparison_position = 2
    else:
        comparison_position = final_position - 1

    ahead_vehicle = None
    ahead_laps = None

    if comparison_position >= 1:
        # Find vehicle that finished in comparison_position
        comparison_final = race_data[race_data['lap'] == final_lap]
        comparison_candidates = comparison_final[comparison_final['position'] == comparison_position]

        if len(comparison_candidates) > 0:
            ahead_vehicle = int(comparison_candidates.iloc[0]['vehicle_number'])
            ahead_laps = race_data[race_data['vehicle_number'] == ahead_vehicle].copy()

    # Segment race for both drivers
    segments = segment_race(driver_laps)

    # Compute pace by stint (absolute lap times, not deltas)
    early_pace = segments['early']['lap_time'].median() if len(segments['early']) > 0 else np.nan
    mid_pace = segments['mid']['lap_time'].median() if len(segments['mid']) > 0 else np.nan
    late_pace = segments['late']['lap_time'].median() if len(segments['late']) > 0 else np.nan

    # Degradation
    driver_deg = compute_degradation_rate(driver_laps)

    # Field degradation (average of all drivers, with safety check)
    field_degradations = []
    for veh in race_data['vehicle_number'].unique():
        veh_laps = race_data[race_data['vehicle_number'] == veh]
        if len(veh_laps) >= 5:  # Need minimum laps
            deg = compute_degradation_rate(veh_laps)
            if not np.isnan(deg):
                field_degradations.append(deg)

    field_deg = np.mean(field_degradations) if len(field_degradations) > 0 else 0.0

    # Traffic analysis
    driver_laps = detect_traffic_laps(driver_laps)
    traffic_laps_count = int(driver_laps['in_traffic'].sum())

    # Traffic cost: difference in pace between traffic and clean air
    traffic_laps_data = driver_laps[driver_laps['in_traffic'] == True]
    clean_laps_data = driver_laps[driver_laps['in_traffic'] == False]

    if len(traffic_laps_data) > 0 and len(clean_laps_data) > 0:
        traffic_avg = traffic_laps_data['lap_time'].median()
        clean_avg = clean_laps_data['lap_time'].median()
        traffic_cost_per_lap = traffic_avg - clean_avg
        traffic_cost = traffic_cost_per_lap * len(traffic_laps_data)
    else:
        traffic_cost = 0.0

    # Compute ahead driver metrics if available
    ahead_early_pace = None
    ahead_mid_pace = None
    ahead_late_pace = None
    ahead_pace_delta = 0.0
    ahead_deg_delta = 0.0
    ahead_traffic_delta = 0

    if ahead_laps is not None and len(ahead_laps) > 0:
        ahead_segments = segment_race(ahead_laps)
        ahead_early_pace = ahead_segments['early']['lap_time'].median() if len(ahead_segments['early']) > 0 else np.nan
        ahead_mid_pace = ahead_segments['mid']['lap_time'].median() if len(ahead_segments['mid']) > 0 else np.nan
        ahead_late_pace = ahead_segments['late']['lap_time'].median() if len(ahead_segments['late']) > 0 else np.nan

        # Average pace delta (negative = we were slower)
        ahead_pace_delta = driver_laps['lap_time'].median() - ahead_laps['lap_time'].median()

        # Degradation delta (positive = we degraded more)
        ahead_deg = compute_degradation_rate(ahead_laps)
        ahead_deg_delta = driver_deg - ahead_deg

        # Traffic delta
        ahead_laps_with_traffic = detect_traffic_laps(ahead_laps)
        ahead_traffic_count = int(ahead_laps_with_traffic['in_traffic'].sum())
        ahead_traffic_delta = traffic_laps_count - ahead_traffic_count

    return DriverMetrics(
        vehicle_number=driver_num,
        final_position=final_position,
        gap_to_winner=float(gap_to_winner),
        gap_to_ahead=float(gap_to_ahead),
        ahead_vehicle=ahead_vehicle,
        ahead_pace_delta=float(ahead_pace_delta),
        ahead_deg_delta=float(ahead_deg_delta),
        ahead_traffic_delta=int(ahead_traffic_delta),
        driver_deg=float(driver_deg),
        field_deg=float(field_deg),
        traffic_laps=traffic_laps_count,
        traffic_cost=float(traffic_cost),
        early_pace=float(early_pace) if not np.isnan(early_pace) else 0.0,
        mid_pace=float(mid_pace) if not np.isnan(mid_pace) else 0.0,
        late_pace=float(late_pace) if not np.isnan(late_pace) else 0.0,
        ahead_early_pace=float(ahead_early_pace) if ahead_early_pace is not None and not np.isnan(ahead_early_pace) else None,
        ahead_mid_pace=float(ahead_mid_pace) if ahead_mid_pace is not None and not np.isnan(ahead_mid_pace) else None,
        ahead_late_pace=float(ahead_late_pace) if ahead_late_pace is not None and not np.isnan(ahead_late_pace) else None,
    )
