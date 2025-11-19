"""
Unified telemetry loader handling all data format variations.

Handles:
- Long format (most tracks): telemetry_name/telemetry_value columns
- JSON format (Sebring R2): JSON array in value column
- Lap 32768 corruption: recalculates from timestamps
- Signal naming: aps vs ath for throttle
- Vehicle ID edge cases: car number 000

Usage:
    from motorsport_modeling.data.telemetry_loader import load_telemetry

    # Load single vehicle
    df = load_telemetry(race_dir, vehicle_number=72)

    # Load all vehicles
    df = load_telemetry(race_dir)
"""

from pathlib import Path
import pandas as pd
import numpy as np
import json
from typing import Optional, Union, List


def load_telemetry(
    race_dir: Union[str, Path],
    vehicle_number: Optional[int] = None,
    laps: Optional[List[int]] = None,
    pivot_to_wide: bool = True,
    use_meta_time: bool = True,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Load and normalize telemetry data from a race directory.

    Parameters
    ----------
    race_dir : str or Path
        Path to race directory containing telemetry CSV
    vehicle_number : int, optional
        Filter to specific car number. If None, loads all vehicles.
    laps : list of int, optional
        Filter to specific laps. If None, loads all laps.
    pivot_to_wide : bool
        If True, pivot from long to wide format (one column per signal)
    use_meta_time : bool
        If True, use meta_time for timing (more reliable than ECU timestamp)
    verbose : bool
        Print progress information

    Returns
    -------
    pd.DataFrame
        Telemetry data in wide format with columns:
        - time: timestamp (meta_time or timestamp)
        - lap: lap number
        - vehicle_number: car number
        - speed, aps, pbrake_f, pbrake_r, accx_can, accy_can, Steering_Angle, gear, nmot
        - Plus GPS columns if available: gps_lat, gps_lon, lap_distance
    """
    race_dir = Path(race_dir)

    # Find telemetry file
    telem_files = list(race_dir.glob('*telemetry*.csv'))
    if not telem_files:
        raise FileNotFoundError(f"No telemetry file found in {race_dir}")

    telem_file = telem_files[0]
    if verbose:
        print(f"Loading telemetry from: {telem_file.name}")

    # Load data
    df = pd.read_csv(telem_file, low_memory=False)
    df.columns = df.columns.str.strip()

    if verbose:
        print(f"  Raw rows: {len(df):,}")

    # Detect and handle format
    if 'telemetry_name' in df.columns:
        # Standard long format
        df = _process_long_format(df)
    elif 'value' in df.columns and df['value'].dtype == object:
        # Check if JSON format (Sebring R2)
        sample = str(df['value'].iloc[0])
        if sample.startswith('[{'):
            df = _process_json_format(df, verbose)
        else:
            df = _process_long_format(df)
    else:
        raise ValueError(f"Unknown telemetry format in {telem_file}")

    # Fix vehicle identification
    df = _fix_vehicle_identification(df)

    # Filter by vehicle if specified
    if vehicle_number is not None:
        df = df[df['vehicle_number'] == vehicle_number]
        if verbose:
            print(f"  Filtered to vehicle #{vehicle_number}: {len(df):,} rows")

    # Fix lap 32768 corruption
    df = _fix_lap_corruption(df, race_dir, verbose)

    # Filter by laps if specified
    if laps is not None:
        df = df[df['lap'].isin(laps)]
        if verbose:
            print(f"  Filtered to laps {laps}: {len(df):,} rows")

    # Select timestamp column
    if use_meta_time and 'meta_time' in df.columns:
        df['time'] = pd.to_datetime(df['meta_time'], errors='coerce')
    else:
        df['time'] = pd.to_datetime(df['timestamp'], errors='coerce')

    # Pivot to wide format if requested
    if pivot_to_wide:
        df = _pivot_to_wide(df, verbose)

    # Normalize signal names
    df = _normalize_signal_names(df)

    # Sort by time and vehicle
    if 'time' in df.columns:
        df = df.sort_values(['vehicle_number', 'lap', 'time']).reset_index(drop=True)

    if verbose:
        print(f"  Final shape: {df.shape}")
        if len(df) > 0:
            if 'vehicle_number' in df.columns:
                print(f"  Vehicles: {sorted(df['vehicle_number'].dropna().unique())}")
            if 'lap' in df.columns and df['lap'].notna().any():
                print(f"  Laps: {int(df['lap'].min())}-{int(df['lap'].max())}")

    return df


def _process_long_format(df: pd.DataFrame) -> pd.DataFrame:
    """Process standard long format telemetry."""
    # Rename telemetry columns for consistency
    if 'telemetry_name' in df.columns:
        df = df.rename(columns={
            'telemetry_name': 'signal',
            'telemetry_value': 'value'
        })
    return df


def _process_json_format(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Process JSON format telemetry (Sebring R2).

    The 'value' column contains JSON arrays like:
    [{"name":"accx_can","value":0.5},{"name":"speed","value":145.3}]
    """
    if verbose:
        print("  Detected JSON format - parsing...")

    rows = []

    for _, row in df.iterrows():
        try:
            signals = json.loads(row['value'])

            # Extract vehicle_number from vehicle_id if not present
            vehicle_num = row.get('vehicle_number')
            if pd.isna(vehicle_num) and 'vehicle_id' in row:
                # Extract from GR86-XXX-YY format
                vid = str(row.get('vehicle_id', ''))
                if '-' in vid:
                    parts = vid.split('-')
                    if len(parts) >= 3:
                        try:
                            vehicle_num = int(parts[-1])
                        except ValueError:
                            vehicle_num = 0

            base_data = {
                'lap': row.get('lap'),
                'timestamp': row.get('timestamp'),
                'meta_time': row.get('meta_time'),
                'vehicle_id': row.get('vehicle_id'),
                'vehicle_number': vehicle_num,
            }

            for signal in signals:
                new_row = base_data.copy()
                new_row['signal'] = signal['name']
                new_row['value'] = signal['value']
                rows.append(new_row)

        except (json.JSONDecodeError, KeyError, TypeError):
            continue

    result = pd.DataFrame(rows)

    # Ensure vehicle_number is numeric
    if 'vehicle_number' in result.columns:
        result['vehicle_number'] = pd.to_numeric(result['vehicle_number'], errors='coerce')

    if verbose:
        print(f"  Parsed {len(result):,} signal readings from JSON")

    return result


def _fix_vehicle_identification(df: pd.DataFrame) -> pd.DataFrame:
    """
    Fix vehicle identification when car number is 000.

    Extract chassis number from vehicle_id (e.g., GR86-004-78 -> 004)
    and use it when vehicle_number is 0 or missing.
    """
    if 'vehicle_number' not in df.columns:
        if 'vehicle_id' in df.columns:
            # Extract car number from vehicle_id
            df['vehicle_number'] = df['vehicle_id'].str.extract(r'-(\d+)$')[0].astype(int)
        else:
            df['vehicle_number'] = 0

    # Fix zeros by using chassis number
    if 'vehicle_id' in df.columns:
        zero_mask = df['vehicle_number'] == 0
        if zero_mask.any():
            # Extract chassis number (middle part of GR86-XXX-YY)
            chassis = df.loc[zero_mask, 'vehicle_id'].str.extract(r'-(\d+)-')[0]
            df.loc[zero_mask, 'vehicle_number'] = pd.to_numeric(chassis, errors='coerce')

    return df


def _fix_lap_corruption(
    df: pd.DataFrame,
    race_dir: Path,
    verbose: bool = True
) -> pd.DataFrame:
    """
    Fix lap 32768 corruption by recalculating from lap timing files.
    """
    # Check for corruption
    if 'lap' not in df.columns:
        return df

    max_lap = df['lap'].max()
    if max_lap < 100:  # No corruption
        return df

    if verbose:
        print(f"  Detected lap corruption (max lap = {max_lap})")

    # Try to load lap start times
    lap_start_files = list(race_dir.glob('*lap_start*.csv'))
    if not lap_start_files:
        if verbose:
            print("  WARNING: Cannot fix - no lap_start file found")
        # Filter out corrupted laps
        df = df[df['lap'] < 100]
        return df

    try:
        lap_starts = pd.read_csv(lap_start_files[0])
        lap_starts['timestamp'] = pd.to_datetime(lap_starts['timestamp'])

        # Get time column from telemetry
        if 'meta_time' in df.columns:
            df['_time'] = pd.to_datetime(df['meta_time'], errors='coerce')
        else:
            df['_time'] = pd.to_datetime(df['timestamp'], errors='coerce')

        # Recalculate lap numbers
        # For each row, find which lap it belongs to based on timestamp
        # This is expensive but necessary for corrupted data

        # Group by vehicle and reassign laps
        fixed_laps = []

        for veh in df['vehicle_number'].unique():
            veh_df = df[df['vehicle_number'] == veh].copy()
            veh_starts = lap_starts[lap_starts['vehicle_number'] == veh].sort_values('timestamp')

            if len(veh_starts) == 0:
                # Keep original (filtered) laps
                veh_df = veh_df[veh_df['lap'] < 100]
                fixed_laps.append(veh_df)
                continue

            # Create lap boundaries
            veh_starts_list = veh_starts['timestamp'].tolist()
            veh_laps_list = veh_starts['lap'].tolist()

            # Assign laps based on timestamp
            veh_df['lap'] = pd.cut(
                veh_df['_time'],
                bins=[pd.Timestamp.min] + veh_starts_list + [pd.Timestamp.max],
                labels=[0] + veh_laps_list,
                include_lowest=True
            )

            fixed_laps.append(veh_df)

        df = pd.concat(fixed_laps, ignore_index=True)
        df = df.drop(columns=['_time'], errors='ignore')

        # Convert lap to numeric
        df['lap'] = pd.to_numeric(df['lap'], errors='coerce')

        if verbose:
            print(f"  Fixed lap numbers: now {int(df['lap'].min())}-{int(df['lap'].max())}")

    except Exception as e:
        if verbose:
            print(f"  WARNING: Failed to fix laps: {e}")
        # Filter out corrupted laps
        df = df[df['lap'] < 100]

    return df


def _pivot_to_wide(df: pd.DataFrame, verbose: bool = True) -> pd.DataFrame:
    """
    Pivot from long format to wide format.

    Long format:
        time, vehicle_number, lap, signal, value
        10:00:01, 72, 5, speed, 145.3
        10:00:01, 72, 5, aps, 100

    Wide format:
        time, vehicle_number, lap, speed, aps, ...
        10:00:01, 72, 5, 145.3, 100, ...
    """
    if 'signal' not in df.columns:
        return df  # Already wide

    # Identify index columns
    index_cols = ['vehicle_number', 'lap']

    # Use meta_time or timestamp as time index
    if 'meta_time' in df.columns:
        index_cols.append('meta_time')
    elif 'timestamp' in df.columns:
        index_cols.append('timestamp')

    # Remove any duplicate index columns
    index_cols = list(dict.fromkeys(index_cols))

    # Pivot
    try:
        wide_df = df.pivot_table(
            index=index_cols,
            columns='signal',
            values='value',
            aggfunc='first'  # Take first value if duplicates
        ).reset_index()

        # Flatten column names
        wide_df.columns = [str(c) for c in wide_df.columns]

        if verbose:
            print(f"  Pivoted to wide format: {len(wide_df):,} rows, {len(wide_df.columns)} columns")

        return wide_df

    except Exception as e:
        if verbose:
            print(f"  WARNING: Failed to pivot: {e}")
        return df


def _normalize_signal_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normalize signal names for consistency.

    - ath -> throttle (throttle blade position)
    - aps -> throttle_pedal (accelerator pedal position)
    - VBOX_Long_Minutes -> gps_lon
    - VBOX_Lat_Min -> gps_lat
    - Laptrigger_lapdist_dls -> lap_distance
    """
    rename_map = {
        'VBOX_Long_Minutes': 'gps_lon',
        'VBOX_Lat_Min': 'gps_lat',
        'Laptrigger_lapdist_dls': 'lap_distance',
    }

    # Apply renames
    df = df.rename(columns=rename_map)

    # Create unified throttle column
    # Prefer ath (actual throttle), fall back to aps (pedal)
    if 'ath' in df.columns and 'aps' not in df.columns:
        df['throttle'] = df['ath']
    elif 'aps' in df.columns and 'ath' not in df.columns:
        df['throttle'] = df['aps']
    elif 'ath' in df.columns and 'aps' in df.columns:
        # Keep both, create unified column preferring ath
        df['throttle'] = df['ath']
        df['throttle_pedal'] = df['aps']

    return df


def get_available_signals(race_dir: Union[str, Path]) -> List[str]:
    """
    Get list of available telemetry signals in a race directory.

    Parameters
    ----------
    race_dir : str or Path
        Path to race directory

    Returns
    -------
    list
        List of signal names available
    """
    race_dir = Path(race_dir)

    telem_files = list(race_dir.glob('*telemetry*.csv'))
    if not telem_files:
        return []

    # Load small sample
    df = pd.read_csv(telem_files[0], nrows=10000)
    df.columns = df.columns.str.strip()

    if 'telemetry_name' in df.columns:
        return sorted(df['telemetry_name'].unique())
    elif 'value' in df.columns:
        # JSON format
        try:
            sample = json.loads(df['value'].iloc[0])
            return sorted([s['name'] for s in sample])
        except:
            pass

    return []


def load_lap_times(race_dir: Union[str, Path]) -> pd.DataFrame:
    """
    Load lap times from a race directory.

    Prefers AnalysisEndurance file (has actual lap times) over lap_time file.

    Parameters
    ----------
    race_dir : str or Path
        Path to race directory

    Returns
    -------
    pd.DataFrame
        Lap times with columns: vehicle_number, lap, lap_time
    """
    race_dir = Path(race_dir)

    # Try AnalysisEndurance file first (has actual lap times)
    endurance_files = list(race_dir.glob('*AnalysisEndurance*.CSV'))
    if endurance_files:
        df = pd.read_csv(endurance_files[0], sep=';')
        df.columns = df.columns.str.strip()

        # Parse LAP_TIME (format: "1:40.123" or "100.123")
        def parse_lap_time(t):
            if pd.isna(t):
                return np.nan
            try:
                t = str(t).strip()
                if ':' in t:
                    parts = t.split(':')
                    return float(parts[0]) * 60 + float(parts[1])
                return float(t)
            except:
                return np.nan

        if 'LAP_TIME' in df.columns:
            df['lap_time'] = df['LAP_TIME'].apply(parse_lap_time)

        # Rename columns
        df = df.rename(columns={
            'NUMBER': 'vehicle_number',
            'LAP_NUMBER': 'lap'
        })

        # Keep relevant columns
        keep_cols = ['vehicle_number', 'lap', 'lap_time']
        keep_cols = [c for c in keep_cols if c in df.columns]
        return df[keep_cols]

    # Fallback to lap_time file and calculate from timestamps
    lap_files = list(race_dir.glob('*lap_time*.csv'))
    if not lap_files:
        raise FileNotFoundError(f"No lap time file found in {race_dir}")

    df = pd.read_csv(lap_files[0])
    df.columns = df.columns.str.strip()

    # Calculate lap time from consecutive timestamps
    if 'timestamp' in df.columns:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.sort_values(['vehicle_number', 'lap'])

        # Calculate time diff
        df['lap_time'] = df.groupby('vehicle_number')['timestamp'].diff().dt.total_seconds()

    # Normalize column names
    df = df.rename(columns={
        'value': 'lap_time_ms',
        'NUMBER': 'vehicle_number'
    })

    # Convert ms to seconds if needed
    if 'lap_time_ms' in df.columns and 'lap_time' not in df.columns:
        df['lap_time'] = df['lap_time_ms'] / 1000

    return df
