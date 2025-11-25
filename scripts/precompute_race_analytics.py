"""
Precompute COMPLETE race features for Race Analytics dashboard.

This includes:
- All laps (including lap 1 where available)
- Sector times (s1, s2, s3) merged from endurance files
- All position/gap/fighting features from prepare_race_features

Output: data/processed/{track}/{race}_analytics.parquet
"""

import pandas as pd
from pathlib import Path
from motorsport_modeling.models.feature_engineering import prepare_race_features

# Configuration
TRACKS = ['barber', 'cota', 'indianapolis', 'road-america', 'sebring', 'sonoma', 'vir']
RACES = ['race1', 'race2']

BASE_DIR = Path(__file__).parent.parent
RAW_DATA_DIR = BASE_DIR / "data" / "raw" / "tracks"
PROCESSED_DIR = BASE_DIR / "data" / "processed"

# Track metadata (total laps per race)
TRACK_METADATA = {
    'barber': {'race1': 55, 'race2': 54},
    'cota': {'race1': 40, 'race2': 40},
    'indianapolis': {'race1': 29, 'race2': 29},
    'road-america': {'race1': 34, 'race2': 34},
    'sebring': {'race1': 35, 'race2': 35},
    'sonoma': {'race1': 40, 'race2': 40},
    'vir': {'race1': 40, 'race2': 40}
}


def find_endurance_file(track_dir: Path, race: str) -> Path:
    """Find the endurance file with sectors using multiple naming patterns."""
    race_num = race[-1]

    patterns = [
        track_dir / f"23_AnalysisEnduranceWithSections_Race {race_num}.CSV",
        track_dir / f"23_AnalysisEnduranceWithSections_Race {race_num}_Anonymized.CSV",
        track_dir / f"23_AnalysisEnduranceWithSections_ Race {race_num}_Anonymized.CSV",
    ]

    for pattern in patterns:
        if pattern.exists():
            return pattern

    return None


def load_sectors(endurance_file: Path) -> pd.DataFrame:
    """Load sector times from endurance file."""
    if not endurance_file or not endurance_file.exists():
        return None

    try:
        df = pd.read_csv(endurance_file, sep=';')
        df.columns = df.columns.str.strip()

        sector_cols = ['NUMBER', 'LAP_NUMBER', 'S1_SECONDS', 'S2_SECONDS', 'S3_SECONDS']
        if not all(col in df.columns for col in sector_cols):
            return None

        sector_data = df[sector_cols].copy()
        sector_data.columns = ['vehicle_number', 'lap', 's1', 's2', 's3']

        for col in ['s1', 's2', 's3']:
            sector_data[col] = pd.to_numeric(sector_data[col], errors='coerce')

        sector_data = sector_data.drop_duplicates(subset=['vehicle_number', 'lap'], keep='first')
        return sector_data
    except Exception as e:
        print(f"  Warning: Could not load sectors - {e}")
        return None


def process_race(track: str, race: str) -> bool:
    """Process a single race and save complete features."""
    print(f"\nProcessing {track}/{race}...")

    try:
        track_dir = RAW_DATA_DIR / track / race
        total_laps = TRACK_METADATA[track][race]

        # Find lap time file
        lap_time_files = list(track_dir.glob("*lap_time*.csv"))
        if not lap_time_files:
            print(f"  ✗ No lap time file found")
            return False

        # Find endurance file
        endurance_file = find_endurance_file(track_dir, race)

        # Use the existing prepare_race_features function
        print(f"  Generating features using prepare_race_features...")
        race_data = prepare_race_features(
            lap_time_file=lap_time_files[0],
            total_laps=total_laps,
            endurance_file=endurance_file,
            verbose=False
        )
        print(f"  Generated {len(race_data)} rows")
        print(f"  Laps: {race_data['lap'].min()} to {race_data['lap'].max()}")

        # Check if sectors are already included
        has_sectors = all(col in race_data.columns for col in ['s1', 's2', 's3'])
        if has_sectors:
            print(f"  Sector data already included")
        elif endurance_file:
            # Add sectors if not already included
            print(f"  Merging additional sector data...")
            sectors = load_sectors(endurance_file)
            if sectors is not None:
                race_data = race_data.merge(sectors, on=['vehicle_number', 'lap'], how='left')
                print(f"  Added sector data ({len(sectors)} records)")

        # Save
        output_dir = PROCESSED_DIR / track
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"{race}_analytics.parquet"

        race_data.to_parquet(output_file, index=False)
        print(f"  ✓ Saved {len(race_data)} rows to {output_file.name}")
        print(f"  Columns: {list(race_data.columns)}")

        return True

    except Exception as e:
        print(f"  ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Process all races."""
    print("=" * 70)
    print("PRECOMPUTING COMPLETE RACE FEATURES FOR ANALYTICS DASHBOARD")
    print("=" * 70)

    success_count = 0
    fail_count = 0

    for track in TRACKS:
        for race in RACES:
            if process_race(track, race):
                success_count += 1
            else:
                fail_count += 1

    print("\n" + "=" * 70)
    print(f"COMPLETE: {success_count} races processed, {fail_count} failed")
    print("=" * 70)


if __name__ == "__main__":
    main()
