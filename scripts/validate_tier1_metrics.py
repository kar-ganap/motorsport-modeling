"""
Validate Tier 1 metrics by comparing winner (#55) to backmarkers.

Success criteria from plan:
- All 5 metrics calculate successfully
- Winner scores better than P19 on ≥4 metrics

Usage:
    uv run python scripts/validate_tier1_metrics.py
"""

from pathlib import Path
import pandas as pd
import numpy as np

from motorsport_modeling.data import load_telemetry, get_available_vehicles
from motorsport_modeling.metrics import (
    calculate_all_tier1_metrics,
    compare_drivers
)


def get_lap_times(
    data_file: Path,
    vehicle: int,
    laps: list
) -> list:
    """
    Calculate lap times from telemetry timestamps.

    This is a simple approximation using the first and last
    timestamp of each lap.
    """
    # Load minimal data to get timestamps
    df = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['ath'],  # Just need any parameter for timestamps
        wide_format=True,
        verbose=False
    )

    lap_times = []
    for lap in sorted(df['lap'].unique()):
        lap_data = df[df['lap'] == lap]
        if len(lap_data) > 10:
            start = lap_data['timestamp'].min()
            end = lap_data['timestamp'].max()
            duration = (end - start).total_seconds()
            if 60 < duration < 300:  # Sanity check: 1-5 minutes
                lap_times.append(duration)

    return lap_times


def load_driver_data(
    data_file: Path,
    vehicle: int,
    laps: list,
    verbose: bool = False
) -> tuple:
    """Load telemetry and lap times for a driver."""

    if verbose:
        print(f"\nLoading data for vehicle #{vehicle}...")

    # Load telemetry with all needed parameters
    # Actual parameter names: aps (throttle), pbrake_f (brake), Steering_Angle, speed
    telemetry = load_telemetry(
        data_file,
        vehicle=vehicle,
        lap=laps,
        parameters=['aps', 'pbrake_f', 'Steering_Angle', 'speed'],
        wide_format=True,
        verbose=False
    )

    # Rename columns to match expected names in metrics
    if 'aps' in telemetry.columns:
        telemetry = telemetry.rename(columns={'aps': 'ath'})
    if 'Steering_Angle' in telemetry.columns:
        telemetry = telemetry.rename(columns={'Steering_Angle': 'steer_angle'})

    if verbose:
        print(f"  Telemetry: {len(telemetry):,} rows")

    # Get lap times
    lap_times = get_lap_times(data_file, vehicle, laps)

    if verbose:
        print(f"  Lap times: {len(lap_times)} laps")

    return telemetry, lap_times


def main():
    data_file = Path(__file__).parent.parent / 'data' / 'raw' / 'R1_indianapolis_motor_speedway_telemetry.csv'

    if not data_file.exists():
        print(f"ERROR: {data_file} not found")
        return

    print("=" * 70)
    print("TIER 1 METRICS VALIDATION")
    print("=" * 70)

    # Get available vehicles
    vehicles = get_available_vehicles(data_file)
    print(f"\nAvailable vehicles: {vehicles}")

    # Winner and backmarkers
    winner = 55
    # Pick a few backmarkers to compare (not always the same every race)
    # Let's use vehicle 2 (runner-up) and last in list as comparison
    runner_up = 2
    backmarker = vehicles[-1] if vehicles[-1] != winner else vehicles[-2]

    print(f"\nComparing:")
    print(f"  Winner: #{winner}")
    print(f"  Runner-up: #{runner_up}")
    print(f"  Backmarker: #{backmarker}")

    # Use laps 3-20 to avoid out-lap and in-lap effects
    laps = list(range(3, 21))
    print(f"  Laps: {laps[0]}-{laps[-1]}")

    # Load data and calculate metrics
    print("\n" + "=" * 70)
    print(f"WINNER (#{winner})")
    print("=" * 70)

    winner_telem, winner_laps = load_driver_data(data_file, winner, laps, verbose=True)
    winner_metrics = calculate_all_tier1_metrics(winner_telem, winner_laps, verbose=True)

    print("\n" + "=" * 70)
    print(f"BACKMARKER (#{backmarker})")
    print("=" * 70)

    backmarker_telem, backmarker_laps = load_driver_data(data_file, backmarker, laps, verbose=True)
    backmarker_metrics = calculate_all_tier1_metrics(backmarker_telem, backmarker_laps, verbose=True)

    print("\n" + "=" * 70)
    print(f"RUNNER-UP (#{runner_up})")
    print("=" * 70)

    runner_telem, runner_laps = load_driver_data(data_file, runner_up, laps, verbose=True)
    runner_metrics = calculate_all_tier1_metrics(runner_telem, runner_laps, verbose=True)

    # Compare winner vs backmarker
    print("\n" + "=" * 70)
    print("COMPARISON: WINNER vs BACKMARKER")
    print("=" * 70)

    comparison = compare_drivers(winner_metrics, backmarker_metrics, verbose=True)

    # Validation
    print("\n" + "=" * 70)
    print("VALIDATION RESULTS")
    print("=" * 70)

    a_wins = comparison['overall']['a_wins']
    b_wins = comparison['overall']['b_wins']
    total_metrics = a_wins + b_wins

    print(f"\nWinner beats backmarker on {a_wins}/{total_metrics} metrics")

    if a_wins >= 4:
        print("✅ SUCCESS: Winner scores better on ≥4 metrics")
    elif a_wins >= 3:
        print("⚠️  ACCEPTABLE: Winner scores better on 3 metrics")
    else:
        print("❌ ISSUE: Winner does not outscore backmarker on most metrics")
        print("   This may indicate metric definitions need adjustment")

    # Also compare winner vs runner-up (should be closer)
    print("\n" + "=" * 70)
    print("COMPARISON: WINNER vs RUNNER-UP")
    print("=" * 70)

    runner_comparison = compare_drivers(winner_metrics, runner_metrics, verbose=True)

    print("\n" + "=" * 70)
    print("DETAILED METRICS TABLE")
    print("=" * 70)

    # Create a summary table
    print("\n{:<25} {:>12} {:>12} {:>12}".format(
        "Metric", f"#{winner}", f"#{runner_up}", f"#{backmarker}"
    ))
    print("-" * 70)

    # Consistency
    for driver_name, metrics in [
        (f"#{winner}", winner_metrics),
        (f"#{runner_up}", runner_metrics),
        (f"#{backmarker}", backmarker_metrics)
    ]:
        if metrics['consistency']:
            print(f"Lap time σ ({driver_name}): {metrics['consistency']['std']:.3f}s")
        if metrics['coasting']:
            print(f"Coasting ({driver_name}): {metrics['coasting']['coasting_pct']:.1f}%")
        if metrics['braking']:
            print(f"Max brake ({driver_name}): {metrics['braking']['max_brake']:.1f} bar")
        if metrics['throttle']:
            print(f"Full throttle ({driver_name}): {metrics['throttle']['full_throttle_pct']:.1f}%")
        if metrics['steering']:
            print(f"Smoothness ({driver_name}): {metrics['steering']['smoothness_score']:.1f}")
        print()

    print("=" * 70)

    return winner_metrics, runner_metrics, backmarker_metrics


if __name__ == "__main__":
    main()
