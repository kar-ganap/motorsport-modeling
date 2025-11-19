"""
Prepare lap time features from all tracks for multi-track modeling.

This script:
1. Loads lap time data from all 7 tracks
2. Computes race features (positions, gaps, context)
3. Adds weather and flag status
4. Combines into a single dataset for cross-track modeling

Usage:
    uv run python scripts/prepare_multitrack_features.py
"""

from pathlib import Path
import pandas as pd
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from motorsport_modeling.models.feature_engineering import prepare_race_features


# Track configurations
TRACKS = {
    'barber': {
        'name': 'Barber Motorsports Park',
        'total_laps': {'race1': 20, 'race2': 20},  # Approximate, will be determined from data
        'lap_time_pattern': 'R{race}_barber_lap_time.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
    'cota': {
        'name': 'Circuit of the Americas',
        'total_laps': {'race1': 15, 'race2': 15},
        'lap_time_pattern': 'COTA_lap_time_R{race}.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',  # Note: Race 2 has extra space
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
    'indianapolis': {
        'name': 'Indianapolis Motor Speedway',
        'total_laps': {'race1': 26, 'race2': 26},
        'lap_time_pattern': 'R{race}_indianapolis_motor_speedway_lap_time.csv',
        'weather_pattern': '26_Weather_Race {race}.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}.CSV',
    },
    'road-america': {
        'name': 'Road America',
        'total_laps': {'race1': 12, 'race2': 12},
        'lap_time_pattern': 'road_america_lap_time_R{race}.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
    'sebring': {
        'name': 'Sebring International Raceway',
        'total_laps': {'race1': 16, 'race2': 16},
        'lap_time_pattern': 'sebring_lap_time_R{race}.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
    'sonoma': {
        'name': 'Sonoma Raceway',
        'total_laps': {'race1': 18, 'race2': 18},
        'lap_time_pattern': 'sonoma_lap_time_R{race}.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
    'vir': {
        'name': 'Virginia International Raceway',
        'total_laps': {'race1': 15, 'race2': 15},
        'lap_time_pattern': 'vir_lap_time_R{race}.csv',
        'weather_pattern': '26_Weather_Race {race}_Anonymized.CSV',
        'endurance_pattern': '23_AnalysisEnduranceWithSections_Race {race}_Anonymized.CSV',
    },
}


def find_file(base_path: Path, pattern: str, race_num: int) -> Path:
    """Find a file matching the pattern, handling variations."""
    # Try exact pattern first
    race_str = str(race_num)
    filename = pattern.format(race=race_str)
    filepath = base_path / filename

    if filepath.exists():
        return filepath

    # Try alternate patterns
    alternates = [
        pattern.format(race=race_str).replace('Race ', 'Race_ '),  # COTA Race 2 has space
        pattern.format(race=race_str).replace('_Race ', '_ Race '),
    ]

    for alt in alternates:
        alt_path = base_path / alt
        if alt_path.exists():
            return alt_path

    # Search by glob
    search_pattern = f"*{race_str}*lap_time*" if 'lap_time' in pattern else f"*{race_str}*"
    matches = list(base_path.glob(search_pattern))
    if matches:
        return matches[0]

    return None


def process_track_race(
    track_id: str,
    race_num: int,
    tracks_dir: Path,
    verbose: bool = True
) -> pd.DataFrame:
    """Process a single track/race combination."""
    track_config = TRACKS[track_id]
    race_key = f'race{race_num}'
    race_dir = tracks_dir / track_id / race_key

    if not race_dir.exists():
        if verbose:
            print(f"  Skipping {track_id} race {race_num}: directory not found")
        return None

    # Find lap time file
    lap_time_file = find_file(
        race_dir,
        track_config['lap_time_pattern'],
        race_num
    )

    if lap_time_file is None:
        if verbose:
            print(f"  Skipping {track_id} race {race_num}: lap time file not found")
        return None

    # Find weather file
    weather_file = find_file(
        race_dir,
        track_config['weather_pattern'],
        race_num
    )

    # Find endurance file
    endurance_file = find_file(
        race_dir,
        track_config['endurance_pattern'],
        race_num
    )

    # Determine total laps from data
    try:
        lap_df = pd.read_csv(lap_time_file)
        max_lap = int(lap_df['lap'].max())
        # Use configured total or detected max
        total_laps = min(max_lap, track_config['total_laps'].get(race_key, max_lap))
    except Exception as e:
        if verbose:
            print(f"  Error reading {lap_time_file}: {e}")
        return None

    if verbose:
        print(f"\n  Processing {track_config['name']} Race {race_num}...")
        print(f"    Lap file: {lap_time_file.name}")
        print(f"    Weather: {'Yes' if weather_file else 'No'}")
        print(f"    Endurance: {'Yes' if endurance_file else 'No'}")
        print(f"    Total laps: {total_laps}")

    try:
        # Process features
        features = prepare_race_features(
            lap_time_file,
            total_laps=total_laps,
            weather_file=weather_file,
            endurance_file=endurance_file,
            verbose=False
        )

        # Add track and race identifiers
        features['track'] = track_id
        features['track_name'] = track_config['name']
        features['race_num'] = race_num
        features['race_id'] = f"{track_id}_r{race_num}"

        if verbose:
            print(f"    Generated {len(features)} samples")

        return features

    except Exception as e:
        if verbose:
            print(f"    Error processing: {e}")
        return None


def main():
    tracks_dir = Path(__file__).parent.parent / 'data' / 'raw' / 'tracks'
    output_dir = Path(__file__).parent.parent / 'data' / 'processed'
    output_dir.mkdir(exist_ok=True)

    print("=" * 70)
    print("MULTI-TRACK FEATURE ENGINEERING")
    print("=" * 70)

    all_features = []

    for track_id in TRACKS.keys():
        print(f"\n{'='*60}")
        print(f"Track: {TRACKS[track_id]['name']}")
        print("=" * 60)

        for race_num in [1, 2]:
            features = process_track_race(
                track_id,
                race_num,
                tracks_dir,
                verbose=True
            )

            if features is not None:
                all_features.append(features)

    # Combine all features
    print("\n" + "=" * 70)
    print("COMBINING DATASETS")
    print("=" * 70)

    if not all_features:
        print("ERROR: No data was processed successfully!")
        return

    combined = pd.concat(all_features, ignore_index=True)

    # Summary
    print(f"\nTotal samples: {len(combined)}")
    print(f"Tracks: {combined['track'].nunique()}")
    print(f"Races: {combined['race_id'].nunique()}")
    print(f"Vehicles: {combined['vehicle_number'].nunique()}")

    # Weather summary
    if 'air_temp' in combined.columns:
        print("\nWeather range:")
        print(f"  Air temp: {combined['air_temp'].min():.1f}°C - {combined['air_temp'].max():.1f}°C")
        print(f"  Track temp: {combined['track_temp'].min():.1f}°C - {combined['track_temp'].max():.1f}°C")

    # Flag status summary
    if 'is_under_yellow' in combined.columns:
        yellow_pct = 100 * combined['is_under_yellow'].sum() / len(combined)
        print(f"\nYellow flag: {yellow_pct:.1f}% of laps")

    # Per-track summary
    print("\nPer-track summary:")
    for track in combined['track'].unique():
        track_data = combined[combined['track'] == track]
        print(f"  {track}: {len(track_data)} samples, "
              f"mean lap time {track_data['lap_time'].mean():.1f}s")

    # Save combined dataset
    output_file = output_dir / 'multitrack_features.csv'
    combined.to_csv(output_file, index=False)
    print(f"\nSaved: {output_file}")

    # Also save per-track files for analysis
    for track in combined['track'].unique():
        track_data = combined[combined['track'] == track]
        track_file = output_dir / f'{track}_features.csv'
        track_data.to_csv(track_file, index=False)
        print(f"Saved: {track_file}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

    return combined


if __name__ == "__main__":
    main()
