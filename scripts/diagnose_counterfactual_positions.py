"""
Diagnostic Script: Investigate P0 Position Bug in Counterfactuals

This script traces through the entire counterfactual generation pipeline
to identify where positions are being incorrectly set to 0.
"""

from pathlib import Path
import pandas as pd
from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.counterfactual import extract_race_features, LapTimeModel, generate_all_interventions, interventions_to_dataframe


def diagnose_position_bug():
    """Comprehensive diagnosis of position calculation issues."""

    print("="*80)
    print("DIAGNOSTIC: P0 POSITION BUG IN COUNTERFACTUALS")
    print("="*80)
    print()

    # Use Indianapolis race1 as test case
    track = 'indianapolis'
    race = 'race1'
    data_dir = Path(f'data/raw/tracks/{track}/{race}')

    # Step 1: Load raw lap_times data
    print("STEP 1: Load raw lap_times data")
    print("-" * 80)
    lap_times = load_lap_times(data_dir)
    print(f"Columns in lap_times: {lap_times.columns.tolist()}")
    print(f"Total rows: {len(lap_times)}")

    # Check if 'position' column exists
    if 'position' in lap_times.columns:
        print("\n✓ 'position' column EXISTS in lap_times")
        print(f"Sample positions for vehicle 2: {lap_times[lap_times['vehicle_number'] == 2]['position'].unique()}")
        print(f"Sample positions for vehicle 3: {lap_times[lap_times['vehicle_number'] == 3]['position'].unique()}")
    else:
        print("\n✗ 'position' column DOES NOT EXIST in lap_times")

    print()

    # Step 2: Check analytics data availability
    print("STEP 2: Check analytics data availability")
    print("-" * 80)
    analytics_file = Path('data/processed') / track / f'{race}_analytics.parquet'

    if analytics_file.exists():
        analytics_data = pd.read_parquet(analytics_file)
        print(f"✓ Analytics file EXISTS: {analytics_file}")
        print(f"  Columns: {analytics_data.columns.tolist()}")
        print(f"  Total rows: {len(analytics_data)}")

        if 'position' in analytics_data.columns:
            print("\n  Position data in analytics:")
            final_lap = analytics_data['lap'].max()
            final_positions = analytics_data[analytics_data['lap'] == final_lap][['vehicle_number', 'position']].sort_values('position')
            print(f"  Final lap ({final_lap}) positions:")
            print(final_positions.head(10).to_string(index=False))
        else:
            print("\n  ✗ 'position' column not in analytics data")
    else:
        print(f"✗ Analytics file DOES NOT EXIST: {analytics_file}")
        analytics_data = None

    print()

    # Step 3: Extract features (this is where positions should be set)
    print("STEP 3: Extract features from lap_times")
    print("-" * 80)

    # Load telemetry for traffic detection
    try:
        telemetry = load_telemetry(data_dir, laps=list(range(1, 21)), pivot_to_wide=True, verbose=False)
        print(f"✓ Loaded telemetry: {telemetry.shape}")
    except Exception as e:
        print(f"✗ Failed to load telemetry: {e}")
        telemetry = None

    # Extract features WITH analytics_data
    print("\nExtracting features WITH analytics_data...")
    features_with_analytics = extract_race_features(lap_times, stint='full', telemetry=telemetry, analytics_data=analytics_data)
    print(f"  Extracted {len(features_with_analytics)} driver features")
    print("\n  Sample positions WITH analytics:")
    print(features_with_analytics[['vehicle_number', 'final_position']].sort_values('final_position').head(10).to_string(index=False))

    # Count P0 positions
    p0_count_with = (features_with_analytics['final_position'] == 0).sum()
    print(f"\n  Drivers with P0 position: {p0_count_with}/{len(features_with_analytics)}")

    # Extract features WITHOUT analytics_data (fallback)
    print("\nExtracting features WITHOUT analytics_data (fallback)...")
    features_without_analytics = extract_race_features(lap_times, stint='full', telemetry=telemetry, analytics_data=None)
    print(f"  Extracted {len(features_without_analytics)} driver features")
    print("\n  Sample positions WITHOUT analytics (fallback calculation):")
    print(features_without_analytics[['vehicle_number', 'final_position']].sort_values('final_position').head(10).to_string(index=False))

    # Count P0 positions
    p0_count_without = (features_without_analytics['final_position'] == 0).sum()
    print(f"\n  Drivers with P0 position: {p0_count_without}/{len(features_without_analytics)}")

    print()

    # Step 4: Check extract_driver_features function behavior
    print("STEP 4: Test extract_driver_features for specific drivers")
    print("-" * 80)

    from motorsport_modeling.counterfactual.feature_extractor import extract_driver_features

    # Test on a driver that shows P0 (vehicle 3)
    print("\nTesting vehicle 3 (shows P0 in counterfactuals):")
    try:
        driver_3_features = extract_driver_features(3, lap_times, stint='full', telemetry=telemetry)
        print(f"  vehicle_number: {driver_3_features.get('vehicle_number')}")
        print(f"  final_position: {driver_3_features.get('final_position')}")
        print(f"  avg_lap_time: {driver_3_features.get('avg_lap_time')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    # Test on a driver that shows correct position (vehicle 2)
    print("\nTesting vehicle 2 (shows P6 in counterfactuals):")
    try:
        driver_2_features = extract_driver_features(2, lap_times, stint='full', telemetry=telemetry)
        print(f"  vehicle_number: {driver_2_features.get('vehicle_number')}")
        print(f"  final_position: {driver_2_features.get('final_position')}")
        print(f"  avg_lap_time: {driver_2_features.get('avg_lap_time')}")
    except Exception as e:
        print(f"  ERROR: {e}")

    print()

    # Step 5: Check lap_times data for these specific drivers
    print("STEP 5: Inspect lap_times data for vehicles 2 and 3")
    print("-" * 80)

    for veh in [2, 3]:
        print(f"\nVehicle {veh}:")
        veh_laps = lap_times[lap_times['vehicle_number'] == veh].copy()
        print(f"  Total laps: {len(veh_laps)}")
        print(f"  Max lap: {veh_laps['lap'].max()}")

        # Check final lap
        final_lap_num = veh_laps['lap'].max()
        final_lap_data = veh_laps[veh_laps['lap'] == final_lap_num].iloc[0]
        print(f"  Final lap ({final_lap_num}) data:")
        print(f"    lap_time: {final_lap_data.get('lap_time')}")

        if 'position' in final_lap_data.index:
            print(f"    position: {final_lap_data.get('position')}")
        else:
            print(f"    position: [column does not exist]")

    print()

    # Step 6: Test counterfactual generation end-to-end
    print("STEP 6: Test counterfactual generation pipeline")
    print("-" * 80)

    # Use features_with_analytics (the correct one)
    features = features_with_analytics.copy()

    # Add gap_to_winner if needed
    if 'gap_to_winner' not in features.columns:
        winner_time = features[features['final_position'] == 1]['avg_lap_time'].values
        if len(winner_time) > 0:
            winner_time = winner_time[0] * 20
            features['gap_to_winner'] = (features['avg_lap_time'] * 20) - winner_time
        else:
            features['gap_to_winner'] = 0.0

    # Train model
    print("\nTraining model...")
    model = LapTimeModel()
    model.fit(features, verbose=False)
    print(f"  Model R²: {model.validation.r2_score:.3f}")

    # Generate interventions
    print("\nGenerating interventions...")
    scenarios = generate_all_interventions(model, features, num_laps=20)
    print(f"  Generated {len(scenarios)} scenarios")

    # Convert to DataFrame
    df = interventions_to_dataframe(scenarios)

    # Check positions in output
    print("\n  Sample positions in counterfactual output:")
    print(df[['vehicle_number', 'original_position']].head(10).to_string(index=False))

    p0_count_output = (df['original_position'] == 0).sum()
    print(f"\n  Drivers with P0 in counterfactual output: {p0_count_output}/{len(df)}")

    print()

    # Step 7: Final diagnosis
    print("="*80)
    print("DIAGNOSIS SUMMARY")
    print("="*80)

    if p0_count_with > 0:
        print(f"✗ PROBLEM FOUND: {p0_count_with} drivers have P0 position in features (WITH analytics)")
        print("  Root cause: extract_race_features is not correctly setting positions")
    elif p0_count_without > 0:
        print(f"✗ PROBLEM FOUND: {p0_count_without} drivers have P0 position in features (WITHOUT analytics)")
        print("  Root cause: Fallback position calculation is incorrect")
    elif p0_count_output > 0:
        print(f"✗ PROBLEM FOUND: {p0_count_output} drivers have P0 position in counterfactual output")
        print("  Root cause: interventions_to_dataframe or generate_interventions is corrupting positions")
    else:
        print("✓ No P0 positions found in this test")
        print("  Issue may be intermittent or specific to certain races")

    print()


if __name__ == '__main__':
    diagnose_position_bug()
