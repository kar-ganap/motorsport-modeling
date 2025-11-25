#!/usr/bin/env python3
"""
Precompute comparative analysis with LLM narratives for all races.

This script:
1. Loads corrected analytics files with fixed position data
2. Computes comparative metrics using beat-the-driver-ahead approach
3. Generates LLM narratives using OpenAI GPT-4o
4. Saves comparative parquet files

NOTE: This requires OpenAI API key and will make ~140-210 LLM calls.
"""

import pandas as pd
from pathlib import Path
from motorsport_modeling.analysis.comparative import (
    FieldBenchmark,
    compute_driver_metrics
)
from motorsport_modeling.analysis.narrative_generator import generate_comparative_narrative

# Configuration
TRACKS = ['barber', 'cota', 'indianapolis', 'road-america', 'sebring', 'sonoma', 'vir']
RACES = ['race1', 'race2']

BASE_DIR = Path(__file__).parent.parent
PROCESSED_DIR = BASE_DIR / "data" / "processed"


def process_race(track: str, race: str) -> bool:
    """
    Generate comparative analysis with LLM narratives for one race.

    Args:
        track: Track name
        race: Race name (race1 or race2)

    Returns:
        True if successful, False otherwise
    """
    print(f"\n{'='*70}")
    print(f"Processing {track}/{race}")
    print('='*70)

    try:
        # Load analytics file with corrected positions
        analytics_file = PROCESSED_DIR / track / f"{race}_analytics.parquet"

        if not analytics_file.exists():
            print(f"  ✗ Analytics file not found: {analytics_file}")
            return False

        race_data = pd.read_parquet(analytics_file)
        print(f"  Loaded {len(race_data)} rows from analytics")

        # Create field benchmarks
        benchmarks = FieldBenchmark(race_data)
        print(f"  Computed field benchmarks")

        # Get all drivers using their maximum completed lap (includes DNFs)
        # Group by driver and get their last lap data
        last_lap_data = race_data.loc[race_data.groupby('vehicle_number')['lap'].idxmax()]
        last_lap_data = last_lap_data.sort_values('position')
        drivers = last_lap_data['vehicle_number'].unique()

        print(f"  Found {len(drivers)} drivers (including DNFs)")

        # Compute metrics and generate narratives for each driver
        comparative_data = []

        for idx, driver_num in enumerate(drivers, 1):
            try:
                print(f"    [{idx}/{len(drivers)}] Driver #{int(driver_num)}...", end='', flush=True)

                # Compute metrics
                metrics = compute_driver_metrics(
                    driver_num=int(driver_num),
                    race_data=race_data,
                    benchmarks=benchmarks.benchmarks
                )

                # Generate LLM narrative
                narrative = generate_comparative_narrative(metrics, model="gpt-4o")

                # Create row for dataframe
                row = {
                    'vehicle_number': metrics.vehicle_number,
                    'final_position': metrics.final_position,
                    'gap_to_winner': metrics.gap_to_winner,
                    'gap_to_ahead': metrics.gap_to_ahead,
                    'ahead_vehicle': metrics.ahead_vehicle,
                    'ahead_pace_delta': metrics.ahead_pace_delta,
                    'ahead_deg_delta': metrics.ahead_deg_delta,
                    'ahead_traffic_delta': metrics.ahead_traffic_delta,
                    'driver_deg': metrics.driver_deg,
                    'field_deg': metrics.field_deg,
                    'traffic_laps': metrics.traffic_laps,
                    'traffic_cost': metrics.traffic_cost,
                    'early_pace': metrics.early_pace,
                    'mid_pace': metrics.mid_pace,
                    'late_pace': metrics.late_pace,
                    'ahead_early_pace': metrics.ahead_early_pace,
                    'ahead_mid_pace': metrics.ahead_mid_pace,
                    'ahead_late_pace': metrics.ahead_late_pace,
                    'narrative': narrative
                }

                comparative_data.append(row)
                print(f" ✓ P{metrics.final_position}")

            except Exception as e:
                print(f" ✗ Error: {e}")
                continue

        if len(comparative_data) == 0:
            print(f"  ✗ No comparative data generated")
            return False

        # Create DataFrame and save
        df = pd.DataFrame(comparative_data)
        df = df.sort_values('final_position').reset_index(drop=True)

        output_file = PROCESSED_DIR / track / f"{race}_comparative.parquet"
        df.to_parquet(output_file, index=False)

        print(f"  ✓ Saved {len(df)} drivers to {output_file.name}")

        # Verify no duplicate positions
        position_counts = df['final_position'].value_counts()
        duplicates = position_counts[position_counts > 1]
        if len(duplicates) > 0:
            print(f"  ⚠️  WARNING: Duplicate positions found: {duplicates.to_dict()}")
            return False
        else:
            print(f"  ✓ Verified: No duplicate positions")

        return True

    except Exception as e:
        print(f"  ✗ Error processing race: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Process all races."""
    print("="*70)
    print("PRECOMPUTING COMPARATIVE ANALYSIS WITH LLM NARRATIVES")
    print("="*70)
    print()
    print("NOTE: This will make ~140-210 OpenAI API calls")
    print("      Estimated cost: $2-5 depending on narrative length")
    print()

    success_count = 0
    fail_count = 0

    for track in TRACKS:
        for race in RACES:
            if process_race(track, race):
                success_count += 1
            else:
                fail_count += 1

    print("\n" + "="*70)
    print(f"COMPLETE: {success_count} races processed successfully")
    if fail_count > 0:
        print(f"          {fail_count} races failed")
    print("="*70)


if __name__ == "__main__":
    main()
