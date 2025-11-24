"""
Precompute Counterfactual Interventions for All Races

Generates "what if" scenarios for all drivers across all tracks and races.
"""

from pathlib import Path
import pandas as pd
from motorsport_modeling.data.telemetry_loader import load_telemetry, load_lap_times
from motorsport_modeling.counterfactual import (
    extract_race_features,
    LapTimeModel,
    generate_all_interventions,
    interventions_to_dataframe
)


def process_race_counterfactuals(track: str, race: str, num_laps: int = 20) -> bool:
    """
    Process counterfactual interventions for a single race.

    Args:
        track: Track name
        race: Race name
        num_laps: Number of race laps

    Returns:
        True if successful, False otherwise
    """
    data_dir = Path(f'data/raw/tracks/{track}/{race}')
    output_dir = Path('data/processed') / track
    output_dir.mkdir(parents=True, exist_ok=True)

    output_file = output_dir / f'{race}_counterfactuals.parquet'

    print(f'\n{"="*70}')
    print(f'Processing: {track}/{race}')
    print('='*70)

    try:
        # Load data
        print('Loading race data...')
        lap_times = load_lap_times(data_dir)

        # Load telemetry for traffic detection
        print('Loading telemetry...')
        try:
            telemetry = load_telemetry(data_dir, laps=list(range(1, num_laps + 1)),
                                      pivot_to_wide=True, verbose=False)
        except Exception as e:
            print(f'  Warning: Could not load telemetry: {e}')
            print('  Proceeding without traffic detection...')
            telemetry = None

        # Extract features
        print('Extracting features...')
        features = extract_race_features(lap_times, stint='full', telemetry=telemetry)
        print(f'  Extracted features for {len(features)} drivers')

        if len(features) < 10:
            print(f'  Warning: Only {len(features)} drivers - may not have enough data for model')
            print('  Skipping this race...')
            return False

        # Add gap_to_winner column (needed for position gain estimation)
        if 'gap_to_winner' not in features.columns:
            # Calculate from final positions
            winner_time = features[features['final_position'] == 1]['avg_lap_time'].values
            if len(winner_time) > 0:
                winner_time = winner_time[0] * num_laps
                features['gap_to_winner'] = (features['avg_lap_time'] * num_laps) - winner_time
            else:
                features['gap_to_winner'] = 0.0

        # Train model
        print('Training counterfactual model...')
        model = LapTimeModel()
        model.fit(features, verbose=False)

        print(f'  Model R²: {model.validation.r2_score:.3f}')
        print(f'  Model MAE: {model.validation.mae:.3f}s')

        # Generate interventions
        print('Generating counterfactual interventions...')
        scenarios = generate_all_interventions(model, features, num_laps=num_laps)
        print(f'  Generated scenarios for {len(scenarios)} drivers')

        # Convert to DataFrame
        df = interventions_to_dataframe(scenarios)

        # Add metadata
        df['track'] = track
        df['race'] = race
        df['num_laps'] = num_laps
        df['model_r2'] = model.validation.r2_score
        df['model_mae'] = model.validation.mae

        # Save
        df.to_parquet(output_file, index=False)
        print(f'  Saved to: {output_file}')

        # Print summary stats
        print('\nSummary Statistics:')
        print(f'  Average time savings: {df["total_time_savings"].mean():.2f}s')
        print(f'  Max time savings: {df["total_time_savings"].max():.2f}s')
        print(f'  Drivers with position gain: {(df["predicted_position_gain"] > 0).sum()}/{len(df)}')

        return True

    except Exception as e:
        print(f'ERROR processing {track}/{race}: {e}')
        import traceback
        traceback.print_exc()
        return False


def main():
    """Process all races."""
    # Define all races (using actual track names from data/raw/tracks)
    races = [
        ('barber', 'race1', 20),
        ('barber', 'race2', 20),
        ('cota', 'race1', 20),
        ('cota', 'race2', 20),
        ('indianapolis', 'race1', 20),
        ('indianapolis', 'race2', 20),
        ('road-america', 'race1', 20),
        ('road-america', 'race2', 20),
        ('sebring', 'race1', 20),
        ('sebring', 'race2', 20),
        ('sonoma', 'race1', 20),
        ('sonoma', 'race2', 20),
        ('vir', 'race1', 20),
        ('vir', 'race2', 20),
    ]

    print('='*70)
    print('COUNTERFACTUAL INTERVENTION GENERATION')
    print('='*70)
    print(f'Processing {len(races)} races...')
    print()

    successful = []
    failed = []

    for track, race, num_laps in races:
        success = process_race_counterfactuals(track, race, num_laps)

        if success:
            successful.append(f'{track}/{race}')
        else:
            failed.append(f'{track}/{race}')

    # Summary
    print('\n' + '='*70)
    print('PROCESSING COMPLETE')
    print('='*70)
    print(f'Successful: {len(successful)}/{len(races)}')
    if failed:
        print(f'\nFailed races:')
        for race in failed:
            print(f'  - {race}')

    print(f'\nCounterfactual data saved to: data/processed/<track>/<race>_counterfactuals.parquet')


if __name__ == '__main__':
    main()
