"""
Feature engineering for lap time prediction model.

This module computes:
- Race positions per lap
- Gaps to ahead/behind/leader
- Rolling telemetry summaries
- Race context features
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Union, List, Optional, Dict
import warnings

from motorsport_modeling.data.loaders import (
    load_lap_times,
    get_race_weather_summary,
    load_endurance_analysis
)


def compute_race_positions(
    lap_times: pd.DataFrame,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Compute race position for each driver at each lap.

    Position is determined by timestamp when car crosses finish line.
    Earlier timestamp = better position.

    Parameters
    ----------
    lap_times : pd.DataFrame
        DataFrame with vehicle_number, lap, timestamp, lap_time
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns: cumulative_time, position
    """
    df = lap_times.copy()

    # Calculate cumulative time for each vehicle (for gap calculations)
    df = df.sort_values(['vehicle_number', 'lap'])
    df['cumulative_time'] = df.groupby('vehicle_number')['lap_time'].cumsum()

    # Calculate position at each lap considering drivers who completed different lap counts
    # Drivers who complete more laps finish ahead of those who complete fewer laps
    # Among drivers on the same lap, earlier timestamp = better position
    max_laps_per_driver = df.groupby('vehicle_number')['lap'].max()
    df['max_lap_completed'] = df['vehicle_number'].map(max_laps_per_driver)

    # For each lap, rank by: (1) max laps completed (DESC), (2) timestamp (ASC)
    # This ensures drivers who DNF early are ranked behind those who continue
    df['position'] = df.groupby('lap').apply(
        lambda x: x.assign(
            position=x[['max_lap_completed', 'timestamp']].apply(
                lambda row: (-row['max_lap_completed'], row['timestamp']), axis=1
            ).rank(method='first')
        )['position']
    ).reset_index(level=0, drop=True).astype(int)

    # Clean up temporary column
    df = df.drop(columns=['max_lap_completed'])

    if verbose:
        # Show final positions (last lap for each vehicle)
        final_lap = df.groupby('vehicle_number')['lap'].max().min()  # Common final lap
        final_positions = df[df['lap'] == final_lap].sort_values('position')
        if len(final_positions) > 0:
            top3 = final_positions.head(3)['vehicle_number'].tolist()
            print(f"Top 3 at lap {final_lap}: {top3}")

    return df


def compute_gaps(
    race_data: pd.DataFrame,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Compute gaps to adjacent cars and leader.

    Gaps are computed using timestamp differences at each lap crossing,
    which reflects actual on-track gaps.

    Parameters
    ----------
    race_data : pd.DataFrame
        DataFrame with vehicle_number, lap, timestamp, position
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns:
        - gap_to_leader: seconds behind P1
        - gap_to_ahead: seconds behind car in front
        - gap_to_behind: seconds ahead of car behind
    """
    df = race_data.copy()

    gaps_ahead = []
    gaps_behind = []
    gaps_leader = []

    for lap in df['lap'].unique():
        lap_data = df[df['lap'] == lap].sort_values('position')

        if len(lap_data) == 0:
            continue

        # Leader's timestamp (earliest crossing)
        leader_timestamp = lap_data['timestamp'].min()

        for idx, row in lap_data.iterrows():
            # Gap to leader (in seconds)
            gap_leader = (row['timestamp'] - leader_timestamp).total_seconds()
            gaps_leader.append((idx, gap_leader))

            # Gap to car ahead
            pos = row['position']
            ahead = lap_data[lap_data['position'] == pos - 1]
            if len(ahead) > 0:
                gap_ahead = (row['timestamp'] - ahead['timestamp'].iloc[0]).total_seconds()
            else:
                gap_ahead = 0.0
            gaps_ahead.append((idx, gap_ahead))

            # Gap to car behind
            behind = lap_data[lap_data['position'] == pos + 1]
            if len(behind) > 0:
                gap_behind = (behind['timestamp'].iloc[0] - row['timestamp']).total_seconds()
            else:
                gap_behind = 999.0  # No car behind
            gaps_behind.append((idx, gap_behind))

    # Add to dataframe
    df['gap_to_leader'] = 0.0
    df['gap_to_ahead'] = 0.0
    df['gap_to_behind'] = 0.0

    for idx, val in gaps_leader:
        df.loc[idx, 'gap_to_leader'] = val
    for idx, val in gaps_ahead:
        df.loc[idx, 'gap_to_ahead'] = val
    for idx, val in gaps_behind:
        df.loc[idx, 'gap_to_behind'] = val

    # Cap gap_to_behind at reasonable value
    df['gap_to_behind'] = df['gap_to_behind'].clip(upper=60.0)

    if verbose:
        print(f"Gap statistics:")
        print(f"  Mean gap to leader: {df['gap_to_leader'].mean():.2f}s")
        print(f"  Mean gap to ahead: {df['gap_to_ahead'].mean():.2f}s")

    return df


def compute_gap_deltas(
    race_data: pd.DataFrame,
    window: int = 3,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Compute rate of change of gaps over rolling window.

    Parameters
    ----------
    race_data : pd.DataFrame
        DataFrame with gaps computed
    window : int
        Rolling window size
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns:
        - gap_delta_ahead: change in gap to car ahead
        - gap_delta_behind: change in gap to car behind
        - is_fighting: boolean, gap < 1s to adjacent car
    """
    df = race_data.copy()

    # Sort by vehicle and lap
    df = df.sort_values(['vehicle_number', 'lap'])

    # Compute deltas
    df['gap_delta_ahead'] = df.groupby('vehicle_number')['gap_to_ahead'].diff(window)
    df['gap_delta_behind'] = df.groupby('vehicle_number')['gap_to_behind'].diff(window)

    # Fill NaN with 0
    df['gap_delta_ahead'] = df['gap_delta_ahead'].fillna(0)
    df['gap_delta_behind'] = df['gap_delta_behind'].fillna(0)

    # Is fighting (within 1 second of adjacent car)
    df['is_fighting'] = (df['gap_to_ahead'] < 1.0) | (df['gap_to_behind'] < 1.0)

    if verbose:
        fighting_pct = 100 * df['is_fighting'].sum() / len(df)
        print(f"Fighting (gap < 1s): {fighting_pct:.1f}% of laps")

    return df


def add_race_context(
    race_data: pd.DataFrame,
    total_laps: int = 26,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Add race context features.

    Parameters
    ----------
    race_data : pd.DataFrame
        DataFrame with core race data
    total_laps : int
        Total laps in race
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns:
        - laps_remaining
        - race_progress (0-1)
        - fuel_load_estimate (normalized)
    """
    df = race_data.copy()

    df['laps_remaining'] = total_laps - df['lap']
    df['race_progress'] = df['lap'] / total_laps

    # Fuel load estimate: starts at 1.0, decreases linearly
    df['fuel_load_estimate'] = 1.0 - df['race_progress']

    if verbose:
        print(f"Race context added. Total laps: {total_laps}")

    return df


def add_lag_features(
    race_data: pd.DataFrame,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Add lag features: previous lap time, rolling averages.

    These features capture driver momentum and current pace.

    Parameters
    ----------
    race_data : pd.DataFrame
        DataFrame with lap times
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Input DataFrame with added columns:
        - prev_lap_time: lap time from previous lap
        - rolling_avg_3: rolling mean of last 3 lap times
        - lap_time_diff: change from previous lap
    """
    df = race_data.copy()

    # Sort by vehicle and lap for proper lag calculation
    df = df.sort_values(['vehicle_number', 'lap'])

    # Previous lap time (strict shift - no current lap info)
    df['prev_lap_time'] = df.groupby('vehicle_number')['lap_time'].shift(1)

    # Rolling average of PREVIOUS laps only (shift then roll to prevent leakage)
    # This computes mean of laps N-3, N-2, N-1 when predicting lap N
    df['rolling_avg_3'] = df.groupby('vehicle_number')['lap_time'].transform(
        lambda x: x.shift(1).rolling(window=3, min_periods=1).mean()
    )

    # Lap time difference from previous
    df['lap_time_diff'] = df['lap_time'] - df['prev_lap_time']

    # DO NOT fill with current lap time - that's data leakage!
    # Leave as NaN for first lap - model should handle missing values
    # Or use a reasonable default (e.g., field median from training data)
    df['lap_time_diff'] = df['lap_time_diff'].fillna(0)

    if verbose:
        print(f"Lag features added: prev_lap_time, rolling_avg_3, lap_time_diff")

    return df


def prepare_race_features(
    lap_time_file: Union[str, Path],
    total_laps: int = 26,
    weather_file: Optional[Union[str, Path]] = None,
    endurance_file: Optional[Union[str, Path]] = None,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Complete feature preparation pipeline.

    Parameters
    ----------
    lap_time_file : str or Path
        Path to lap time CSV
    total_laps : int
        Total laps in race
    weather_file : str or Path, optional
        Path to weather CSV for race conditions
    endurance_file : str or Path, optional
        Path to endurance analysis CSV for flag status
    verbose : bool
        Print progress

    Returns
    -------
    pd.DataFrame
        Complete feature matrix ready for modeling
    """
    if verbose:
        print("=" * 60)
        print("FEATURE ENGINEERING PIPELINE")
        print("=" * 60)

    # Step 1: Load and compute lap times
    if verbose:
        print("\n1. Loading lap times...")
    lap_times = load_lap_times(lap_time_file, max_lap=total_laps, verbose=verbose)

    # Step 2: Compute positions
    if verbose:
        print("\n2. Computing race positions...")
    race_data = compute_race_positions(lap_times, verbose=verbose)

    # Step 3: Compute gaps
    if verbose:
        print("\n3. Computing gaps...")
    race_data = compute_gaps(race_data, verbose=verbose)

    # Step 4: Compute gap deltas
    if verbose:
        print("\n4. Computing gap deltas...")
    race_data = compute_gap_deltas(race_data, verbose=verbose)

    # Step 5: Add race context
    if verbose:
        print("\n5. Adding race context...")
    race_data = add_race_context(race_data, total_laps=total_laps, verbose=verbose)

    # Step 6: Add lag features (previous lap time, rolling average)
    if verbose:
        print("\n6. Adding lag features...")
    race_data = add_lag_features(race_data, verbose=verbose)

    # Step 7: Add weather features (if provided)
    if weather_file is not None:
        if verbose:
            print("\n7. Adding weather features...")
        weather = get_race_weather_summary(weather_file, verbose=verbose)
        for key, value in weather.items():
            race_data[key] = value
        if verbose:
            print(f"  Added: {list(weather.keys())}")

    # Step 8: Add flag status and top speed (if provided)
    if endurance_file is not None:
        if verbose:
            print("\n8. Adding flag status and top speed...")
        endurance = load_endurance_analysis(endurance_file, verbose=verbose)

        # Columns to merge from endurance data
        merge_cols = ['vehicle_number', 'lap', 'is_under_yellow']

        # Add top_speed if available
        if 'top_speed' in endurance.columns:
            merge_cols.append('top_speed')

        # Merge on vehicle_number and lap
        merge_data = endurance[merge_cols].copy()
        race_data = race_data.merge(
            merge_data,
            on=['vehicle_number', 'lap'],
            how='left'
        )

        # Fill missing flags with 0 (assume green flag)
        race_data['is_under_yellow'] = race_data['is_under_yellow'].fillna(0).astype(int)

        # Fill missing top_speed with median
        if 'top_speed' in race_data.columns:
            race_data['top_speed'] = race_data['top_speed'].fillna(race_data['top_speed'].median())

        if verbose:
            yellow_pct = 100 * race_data['is_under_yellow'].sum() / len(race_data)
            print(f"  Under yellow: {yellow_pct:.1f}% of laps")
            if 'top_speed' in race_data.columns:
                print(f"  Top speed range: {race_data['top_speed'].min():.1f} - {race_data['top_speed'].max():.1f} km/h")

    # Final cleanup
    race_data = race_data.sort_values(['lap', 'position']).reset_index(drop=True)

    if verbose:
        print("\n" + "=" * 60)
        print(f"Feature matrix: {len(race_data)} rows × {len(race_data.columns)} columns")
        print(f"Vehicles: {race_data['vehicle_number'].nunique()}")
        print(f"Laps: {race_data['lap'].min()} - {race_data['lap'].max()}")
        print("=" * 60)

    return race_data


def get_feature_columns() -> Dict[str, List[str]]:
    """
    Get lists of feature columns by category.

    Returns
    -------
    dict
        Dictionary with keys: core, race_context, telemetry, target
    """
    return {
        'core': ['lap', 'vehicle_number'],
        'race_context': [
            'position',
            'gap_to_leader',
            'gap_to_ahead',
            'gap_to_behind',
            'gap_delta_ahead',
            'gap_delta_behind',
            'is_fighting',
            'laps_remaining',
            'race_progress',
            'fuel_load_estimate'
        ],
        'telemetry': [
            # To be added when telemetry summaries are computed
        ],
        'target': ['lap_time']
    }
