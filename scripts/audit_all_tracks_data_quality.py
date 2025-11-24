"""
P0: Comprehensive data quality audit across ALL tracks.

This script performs the same level of scrutiny on all tracks that was done for Indianapolis.

Checks performed:
1. Data density (samples per lap for key signals)
2. Signal coverage (% of laps with valid data)
3. Value distributions (ranges, outliers)
4. Timestamp consistency
5. Cross-signal correlations (brake vs speed, etc.)

Usage:
    uv run python scripts/audit_all_tracks_data_quality.py
"""

from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


def get_all_tracks(data_dir: Path) -> List[Path]:
    """Get all track directories."""
    tracks_dir = data_dir / 'raw' / 'tracks'
    return [d for d in tracks_dir.iterdir() if d.is_dir()]


def load_telemetry_sample(race_dir: Path, vehicle_num: int = None) -> pd.DataFrame:
    """Load telemetry data for a race (sample one vehicle if not specified)."""
    # Try different patterns for telemetry files
    telemetry_files = list(race_dir.glob('*telemetry*.csv'))
    if not telemetry_files:
        telemetry_files = list(race_dir.glob('*telemetry*.CSV'))
    if not telemetry_files:
        telemetry_files = list(race_dir.glob('*Inlap*.CSV'))

    if not telemetry_files:
        return pd.DataFrame()

    # Load first file - use nrows to sample for speed
    try:
        # Try comma first (most telemetry files), then semicolon
        # Only load first 100k rows for quick audit
        try:
            df = pd.read_csv(telemetry_files[0], low_memory=False, nrows=100000)
        except:
            df = pd.read_csv(telemetry_files[0], sep=';', low_memory=False, nrows=100000)
        df.columns = df.columns.str.strip()

        if vehicle_num is None:
            # Sample first available vehicle
            if 'NUMBER' in df.columns:
                vehicle_num = df['NUMBER'].iloc[0]
            else:
                return df

        # Filter to single vehicle
        if 'NUMBER' in df.columns:
            df = df[df['NUMBER'] == vehicle_num]

        return df
    except Exception as e:
        print(f"  Error loading {telemetry_files[0].name}: {e}")
        return pd.DataFrame()


def audit_track(track_dir: Path) -> Dict:
    """Perform comprehensive audit of a single track."""
    track_name = track_dir.name
    results = {
        'track': track_name,
        'races': [],
        'issues': [],
        'summary': {}
    }

    # Key telemetry columns we need for Tier 1 metrics
    key_columns = {
        'speed': ['speed', 'Speed'],
        'throttle': ['aps', 'APS', 'throttle'],
        'brake_front': ['pbrake_f', 'PBRAKE_F', 'brake_f'],
        'brake_rear': ['pbrake_r', 'PBRAKE_R', 'brake_r'],
        'steering': ['Steering_Angle', 'steering_angle', 'steering'],
        'gps_lat': ['GPS_Latitude', 'gps_lat', 'lat'],
        'gps_lon': ['GPS_Longitude', 'gps_lon', 'lon'],
        'accel_x': ['accx_can', 'ACCX_CAN', 'accel_x'],
        'accel_y': ['accy_can', 'ACCY_CAN', 'accel_y'],
        'lap': ['LAP', 'lap', 'Lap'],
        'timestamp': ['UTC', 'timestamp', 'time']
    }

    for race_dir in sorted(track_dir.iterdir()):
        if not race_dir.is_dir():
            continue

        race_name = race_dir.name
        race_audit = {
            'race': race_name,
            'telemetry': {},
            'lap_data': {},
            'issues': []
        }

        # Load telemetry sample
        df = load_telemetry_sample(race_dir)

        if len(df) == 0:
            race_audit['issues'].append('No telemetry data found')
            results['races'].append(race_audit)
            continue

        race_audit['total_rows'] = len(df)

        # Find available columns
        available_cols = {}
        for key, possible_names in key_columns.items():
            for name in possible_names:
                if name in df.columns:
                    available_cols[key] = name
                    break

        race_audit['available_columns'] = list(available_cols.keys())
        missing_cols = set(key_columns.keys()) - set(available_cols.keys())
        if missing_cols:
            race_audit['issues'].append(f'Missing columns: {missing_cols}')

        # Audit each key signal
        for signal_key, col_name in available_cols.items():
            signal_audit = audit_signal(df, col_name, signal_key)
            race_audit['telemetry'][signal_key] = signal_audit

            # Flag issues
            if signal_audit['missing_pct'] > 10:
                race_audit['issues'].append(f'{signal_key}: {signal_audit["missing_pct"]:.1f}% missing')
            if signal_audit.get('outlier_pct', 0) > 5:
                race_audit['issues'].append(f'{signal_key}: {signal_audit["outlier_pct"]:.1f}% outliers')

        # Audit lap structure
        if 'lap' in available_cols:
            lap_col = available_cols['lap']
            lap_audit = audit_lap_structure(df, lap_col)
            race_audit['lap_data'] = lap_audit

            if lap_audit['samples_per_lap'] < 500:
                race_audit['issues'].append(f'Low data density: {lap_audit["samples_per_lap"]:.0f} samples/lap')

        # Check timestamp consistency
        if 'timestamp' in available_cols:
            ts_audit = audit_timestamps(df, available_cols['timestamp'])
            race_audit['timestamp'] = ts_audit

            if ts_audit.get('gaps_detected', 0) > 0:
                race_audit['issues'].append(f'Timestamp gaps: {ts_audit["gaps_detected"]}')

        # Cross-signal sanity checks
        cross_checks = audit_cross_signals(df, available_cols)
        race_audit['cross_checks'] = cross_checks

        for check, passed in cross_checks.items():
            if not passed:
                race_audit['issues'].append(f'Failed check: {check}')

        results['races'].append(race_audit)

    # Aggregate issues
    all_issues = []
    for race in results['races']:
        for issue in race.get('issues', []):
            all_issues.append(f"{race['race']}: {issue}")
    results['issues'] = all_issues

    return results


def audit_signal(df: pd.DataFrame, col_name: str, signal_key: str) -> Dict:
    """Audit a single signal column."""
    result = {
        'column': col_name,
        'total_count': len(df),
    }

    # Get the column data
    data = df[col_name]

    # Missing values
    missing = data.isna().sum()
    result['missing_count'] = int(missing)
    result['missing_pct'] = 100 * missing / len(df) if len(df) > 0 else 0

    # For numeric columns
    if pd.api.types.is_numeric_dtype(data):
        valid_data = data.dropna()

        if len(valid_data) > 0:
            result['min'] = float(valid_data.min())
            result['max'] = float(valid_data.max())
            result['mean'] = float(valid_data.mean())
            result['std'] = float(valid_data.std())
            result['median'] = float(valid_data.median())

            # Percentiles
            result['p5'] = float(valid_data.quantile(0.05))
            result['p95'] = float(valid_data.quantile(0.95))

            # Check for outliers (beyond 3 std or signal-specific)
            outliers = detect_outliers(valid_data, signal_key)
            result['outlier_count'] = int(outliers.sum())
            result['outlier_pct'] = 100 * outliers.sum() / len(valid_data)

            # Check for suspicious values
            result['zero_pct'] = 100 * (valid_data == 0).sum() / len(valid_data)
            result['negative_pct'] = 100 * (valid_data < 0).sum() / len(valid_data)

    return result


def detect_outliers(data: pd.Series, signal_key: str) -> pd.Series:
    """Detect outliers based on signal type."""
    # Signal-specific ranges
    expected_ranges = {
        'speed': (0, 350),  # km/h
        'throttle': (0, 100),  # percentage
        'brake_front': (0, 200),  # bar
        'brake_rear': (0, 200),  # bar
        'steering': (-720, 720),  # degrees
        'accel_x': (-5, 5),  # g
        'accel_y': (-5, 5),  # g
        'gps_lat': (-90, 90),
        'gps_lon': (-180, 180),
    }

    if signal_key in expected_ranges:
        low, high = expected_ranges[signal_key]
        return (data < low) | (data > high)
    else:
        # Default: 3 std from mean
        mean = data.mean()
        std = data.std()
        return (data < mean - 3*std) | (data > mean + 3*std)


def audit_lap_structure(df: pd.DataFrame, lap_col: str) -> Dict:
    """Audit lap data structure."""
    result = {}

    laps = df[lap_col].dropna()

    if len(laps) == 0:
        return {'error': 'No lap data'}

    result['min_lap'] = int(laps.min())
    result['max_lap'] = int(laps.max())
    result['unique_laps'] = int(laps.nunique())
    result['total_samples'] = len(laps)
    result['samples_per_lap'] = len(laps) / max(laps.nunique(), 1)

    # Check for lap gaps
    lap_counts = laps.value_counts().sort_index()
    result['min_samples_in_lap'] = int(lap_counts.min())
    result['max_samples_in_lap'] = int(lap_counts.max())
    result['cv_samples'] = lap_counts.std() / lap_counts.mean() if lap_counts.mean() > 0 else 0

    # Check for missing laps
    expected_laps = set(range(int(laps.min()), int(laps.max()) + 1))
    actual_laps = set(laps.unique().astype(int))
    missing_laps = expected_laps - actual_laps
    result['missing_laps'] = list(missing_laps)

    return result


def audit_timestamps(df: pd.DataFrame, ts_col: str) -> Dict:
    """Audit timestamp consistency."""
    result = {}

    try:
        # Try to parse timestamps
        timestamps = pd.to_datetime(df[ts_col], errors='coerce')
        valid_ts = timestamps.dropna().sort_values()

        if len(valid_ts) < 2:
            return {'error': 'Insufficient timestamp data'}

        # Calculate time deltas
        deltas = valid_ts.diff().dropna()
        delta_seconds = deltas.dt.total_seconds()

        result['mean_delta_ms'] = float(delta_seconds.mean() * 1000)
        result['std_delta_ms'] = float(delta_seconds.std() * 1000)
        result['min_delta_ms'] = float(delta_seconds.min() * 1000)
        result['max_delta_ms'] = float(delta_seconds.max() * 1000)

        # Detect gaps (> 1 second)
        gaps = delta_seconds > 1.0
        result['gaps_detected'] = int(gaps.sum())

        # Detect negative deltas (timestamp going backwards)
        negative = delta_seconds < 0
        result['negative_deltas'] = int(negative.sum())

    except Exception as e:
        result['error'] = str(e)

    return result


def audit_cross_signals(df: pd.DataFrame, available_cols: Dict) -> Dict:
    """Cross-signal sanity checks."""
    checks = {}

    # Check 1: Speed and throttle correlation
    if 'speed' in available_cols and 'throttle' in available_cols:
        speed = df[available_cols['speed']].dropna()
        throttle = df[available_cols['throttle']].dropna()

        # At high speed, throttle should generally be high
        if len(speed) > 100:
            high_speed_mask = speed > speed.quantile(0.9)
            if high_speed_mask.sum() > 0:
                # Align indices
                common_idx = speed.index.intersection(throttle.index)
                high_speed_throttle = throttle.loc[common_idx][high_speed_mask.loc[common_idx]]
                if len(high_speed_throttle) > 0:
                    checks['high_speed_throttle'] = high_speed_throttle.mean() > 50

    # Check 2: Brake and speed inverse relationship
    if 'speed' in available_cols and 'brake_front' in available_cols:
        speed = df[available_cols['speed']].dropna()
        brake = df[available_cols['brake_front']].dropna()

        if len(brake) > 100:
            high_brake_mask = brake > brake.quantile(0.9)
            if high_brake_mask.sum() > 0:
                common_idx = speed.index.intersection(brake.index)
                if len(common_idx) > 0:
                    high_brake_speed = speed.loc[common_idx][high_brake_mask.loc[common_idx]]
                    # When braking hard, speed should be decreasing (not at max)
                    if len(high_brake_speed) > 0:
                        checks['brake_speed_inverse'] = high_brake_speed.mean() < speed.mean()

    # Check 3: GPS coordinates in valid range
    if 'gps_lat' in available_cols and 'gps_lon' in available_cols:
        lat = df[available_cols['gps_lat']].dropna()
        lon = df[available_cols['gps_lon']].dropna()

        if len(lat) > 0 and len(lon) > 0:
            # Check coordinates are in reasonable range (US tracks)
            checks['gps_valid_range'] = (
                (lat.min() > 20) and (lat.max() < 50) and  # US latitude
                (lon.min() > -130) and (lon.max() < -70)   # US longitude
            )

    # Check 4: Acceleration values reasonable
    if 'accel_x' in available_cols and 'accel_y' in available_cols:
        ax = df[available_cols['accel_x']].dropna()
        ay = df[available_cols['accel_y']].dropna()

        if len(ax) > 0 and len(ay) > 0:
            # Combined G shouldn't exceed ~4G regularly
            checks['g_force_reasonable'] = (
                (ax.abs().quantile(0.99) < 4) and
                (ay.abs().quantile(0.99) < 4)
            )

    return checks


def print_audit_results(results: Dict):
    """Print formatted audit results."""
    track = results['track']

    print(f"\n{'='*70}")
    print(f"TRACK: {track.upper()}")
    print(f"{'='*70}")

    total_issues = len(results['issues'])
    status = "PASS" if total_issues == 0 else f"ISSUES ({total_issues})"
    print(f"Status: {status}")

    for race_audit in results['races']:
        race = race_audit['race']
        print(f"\n  {race}:")
        print(f"    Rows: {race_audit.get('total_rows', 'N/A')}")
        print(f"    Available signals: {race_audit.get('available_columns', [])}")

        # Key metrics
        if 'lap_data' in race_audit and race_audit['lap_data']:
            lap_data = race_audit['lap_data']
            if 'samples_per_lap' in lap_data:
                print(f"    Samples/lap: {lap_data['samples_per_lap']:.0f}")
            if 'unique_laps' in lap_data:
                print(f"    Laps: {lap_data.get('min_lap', '?')}-{lap_data.get('max_lap', '?')} ({lap_data['unique_laps']} unique)")

        # Signal summaries
        if 'telemetry' in race_audit:
            for signal, audit in race_audit['telemetry'].items():
                if 'missing_pct' in audit and audit['missing_pct'] > 0:
                    print(f"    {signal}: {audit['missing_pct']:.1f}% missing", end='')
                    if 'min' in audit and 'max' in audit:
                        print(f", range [{audit['min']:.1f}, {audit['max']:.1f}]", end='')
                    print()

        # Issues
        if race_audit.get('issues'):
            print(f"    Issues:")
            for issue in race_audit['issues']:
                print(f"      - {issue}")

    # Summary of all issues
    if results['issues']:
        print(f"\n  ALL ISSUES:")
        for issue in results['issues']:
            print(f"    - {issue}")


def main():
    data_dir = Path(__file__).parent.parent / 'data'

    print("="*70)
    print("P0: COMPREHENSIVE DATA QUALITY AUDIT - ALL TRACKS")
    print("="*70)
    print("\nPerforming same level of scrutiny as Indianapolis on all tracks...")

    tracks = get_all_tracks(data_dir)
    print(f"\nFound {len(tracks)} tracks to audit")

    all_results = []
    total_issues = 0

    for track_dir in sorted(tracks):
        results = audit_track(track_dir)
        all_results.append(results)
        print_audit_results(results)
        total_issues += len(results['issues'])

    # Summary
    print("\n" + "="*70)
    print("AUDIT SUMMARY")
    print("="*70)

    print(f"\nTracks audited: {len(tracks)}")
    print(f"Total issues found: {total_issues}")

    # Issues by track
    print("\nIssues by track:")
    for results in sorted(all_results, key=lambda x: len(x['issues']), reverse=True):
        track = results['track']
        n_issues = len(results['issues'])
        status = "OK" if n_issues == 0 else f"{n_issues} issues"
        print(f"  {track}: {status}")

    # Critical issues that would block Tier 1 metrics
    print("\n" + "="*70)
    print("CRITICAL ISSUES FOR TIER 1 METRICS")
    print("="*70)

    critical_signals = ['speed', 'throttle', 'brake_front', 'accel_x', 'accel_y']

    for results in all_results:
        track = results['track']
        critical = []

        for race in results['races']:
            available = race.get('available_columns', [])
            missing_critical = [s for s in critical_signals if s not in available]

            if missing_critical:
                critical.append(f"{race['race']}: Missing {missing_critical}")

            # Check for high missing %
            for signal in critical_signals:
                if signal in race.get('telemetry', {}):
                    missing_pct = race['telemetry'][signal].get('missing_pct', 0)
                    if missing_pct > 20:
                        critical.append(f"{race['race']}: {signal} has {missing_pct:.0f}% missing")

        if critical:
            print(f"\n{track}:")
            for issue in critical:
                print(f"  - {issue}")

    print("\n" + "="*70)
    print("AUDIT COMPLETE")
    print("="*70)

    # Return summary for further processing
    return all_results


if __name__ == "__main__":
    main()
