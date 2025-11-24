"""
Data loading utilities for motorsport telemetry data.

This module provides functions to load and process telemetry data from
CSV files in long format (one row per measurement).
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Optional, Union, List, Dict
import time


def load_telemetry(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    lap: Optional[Union[int, List[int]]] = None,
    parameters: Optional[List[str]] = None,
    wide_format: bool = True,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load telemetry data from CSV file.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file containing telemetry data
    vehicle : int, optional
        Filter by vehicle number (e.g., 55 for car #55)
    lap : int or list of int, optional
        Filter by lap number(s)
    parameters : list of str, optional
        Filter by specific telemetry parameters
        (e.g., ['speed', 'ath', 'pbrake_f'])
    wide_format : bool, default=True
        If True, pivot to wide format (one row per timestamp)
        If False, keep long format (one row per measurement)
    verbose : bool, default=False
        Print loading progress and statistics

    Returns
    -------
    pd.DataFrame
        Telemetry data in requested format

    Examples
    --------
    >>> # Load all data for vehicle #55, lap 7
    >>> df = load_telemetry('data.csv', vehicle=55, lap=7)

    >>> # Load speed and throttle for multiple laps
    >>> df = load_telemetry('data.csv', vehicle=55, lap=[5,6,7],
    ...                     parameters=['speed', 'ath'])

    >>> # Load all data in long format
    >>> df = load_telemetry('data.csv', wide_format=False)
    """
    start_time = time.time()

    if verbose:
        print(f"Loading telemetry from: {file_path}")

    # Load CSV
    df = pd.read_csv(file_path)

    if verbose:
        print(f"  Loaded {len(df):,} rows in {time.time() - start_time:.2f}s")

    # Filter by vehicle
    if vehicle is not None:
        df = df[df['vehicle_number'] == vehicle].copy()
        if verbose:
            print(f"  Filtered to vehicle #{vehicle}: {len(df):,} rows")

    # Filter by lap
    if lap is not None:
        if isinstance(lap, int):
            lap = [lap]
        df = df[df['lap'].isin(lap)].copy()
        if verbose:
            print(f"  Filtered to lap(s) {lap}: {len(df):,} rows")

    # Filter by parameters
    if parameters is not None:
        df = df[df['telemetry_name'].isin(parameters)].copy()
        if verbose:
            print(f"  Filtered to {len(parameters)} parameters: {len(df):,} rows")

    # Convert timestamp to datetime
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    if wide_format:
        # Pivot to wide format
        if verbose:
            print("  Pivoting to wide format...")

        # Pivot: rows are timestamps, columns are telemetry parameters
        df_wide = df.pivot_table(
            index=['vehicle_number', 'lap', 'timestamp'],
            columns='telemetry_name',
            values='telemetry_value',
            aggfunc='first'  # Take first value if duplicates
        ).reset_index()

        # Flatten column names
        df_wide.columns.name = None

        # Sort by timestamp
        df_wide = df_wide.sort_values(['vehicle_number', 'lap', 'timestamp'])

        if verbose:
            print(f"  Wide format: {len(df_wide):,} rows × {len(df_wide.columns)} columns")
            print(f"  Total time: {time.time() - start_time:.2f}s")

        return df_wide
    else:
        # Return long format
        df = df.sort_values(['vehicle_number', 'lap', 'timestamp', 'telemetry_name'])

        if verbose:
            print(f"  Total time: {time.time() - start_time:.2f}s")

        return df


def load_gps_data(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    lap: Optional[Union[int, List[int]]] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load GPS telemetry data (latitude, longitude, lap distance).

    This is a convenience function that loads only GPS-related parameters.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file containing telemetry data
    vehicle : int, optional
        Filter by vehicle number
    lap : int or list of int, optional
        Filter by lap number(s)
    verbose : bool, default=False
        Print loading progress

    Returns
    -------
    pd.DataFrame
        GPS data with columns: vehicle_number, lap, timestamp,
        VBOX_Lat_Min, VBOX_Long_Minutes, Laptrigger_lapdist_dls

    Examples
    --------
    >>> gps = load_gps_data('data.csv', vehicle=55, lap=7)
    >>> plt.plot(gps['VBOX_Long_Minutes'], gps['VBOX_Lat_Min'])
    """
    gps_params = ['VBOX_Lat_Min', 'VBOX_Long_Minutes', 'Laptrigger_lapdist_dls']

    df = load_telemetry(
        file_path,
        vehicle=vehicle,
        lap=lap,
        parameters=gps_params,
        wide_format=True,
        verbose=verbose
    )

    # Check if GPS data is present
    if 'VBOX_Lat_Min' not in df.columns or 'VBOX_Long_Minutes' not in df.columns:
        raise ValueError(
            "GPS data not found in telemetry. "
            "This dataset may not include GPS parameters."
        )

    # Rename for convenience
    df = df.rename(columns={
        'VBOX_Lat_Min': 'latitude',
        'VBOX_Long_Minutes': 'longitude',
        'Laptrigger_lapdist_dls': 'lap_distance'
    })

    # Remove rows with missing GPS
    df = df.dropna(subset=['latitude', 'longitude'])

    if verbose:
        print(f"GPS data: {len(df):,} points")

    return df


def load_lap_times(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    max_lap: Optional[int] = None,
    min_lap_time: float = 60.0,
    max_lap_time: float = 300.0,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load lap time data from CSV file with data quality fixes.

    Handles common data quality issues:
    - Duplicate timestamps (keeps latest per lap)
    - Invalid lap numbers (e.g., 32768 sentinel values)
    - Cool-down laps (filtered via max_lap)
    - Invalid lap times (filtered via min/max thresholds)

    Parameters
    ----------
    file_path : str or Path
        Path to lap time CSV file
    vehicle : int, optional
        Filter by vehicle number
    max_lap : int, optional
        Maximum lap number to include (filters out cool-down laps)
    min_lap_time : float, default=60.0
        Minimum valid lap time in seconds
    max_lap_time : float, default=300.0
        Maximum valid lap time in seconds
    verbose : bool, default=False
        Print loading progress and statistics

    Returns
    -------
    pd.DataFrame
        Lap time data with columns:
        - vehicle_number: int
        - lap: int
        - timestamp: datetime
        - lap_time: float (seconds)

    Notes
    -----
    Lap times are calculated as the difference between consecutive lap
    timestamps for each vehicle. Lap 1 is excluded since there's no
    prior timestamp to compute a difference from.

    Examples
    --------
    >>> # Load all lap times for Race 1 (26 laps)
    >>> df = load_lap_times('R1_lap_time.csv', max_lap=26)

    >>> # Load lap times for specific vehicle
    >>> df = load_lap_times('R1_lap_time.csv', vehicle=55, max_lap=26)
    """
    if verbose:
        print(f"Loading lap times from: {file_path}")

    df = pd.read_csv(file_path)

    if verbose:
        print(f"  Loaded {len(df):,} rows")

    # Handle different column naming schemes
    # Some files have 'vehicle_number', others only have 'vehicle_id'
    if 'vehicle_number' not in df.columns and 'vehicle_id' in df.columns:
        # vehicle_id can be string like "GR86-002-2" - extract number from middle
        if df['vehicle_id'].dtype == 'object':
            # Extract number from pattern "GR86-XXX-Y"
            df['vehicle_number'] = df['vehicle_id'].str.extract(r'-(\d+)-', expand=False)
            df['vehicle_number'] = pd.to_numeric(df['vehicle_number'], errors='coerce')
            if verbose:
                print(f"  Extracted vehicle_number from vehicle_id string")
        else:
            df['vehicle_number'] = df['vehicle_id']
            if verbose:
                print(f"  Using vehicle_id as vehicle_number")

    # Parse timestamps
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Filter out invalid lap numbers (32768 is a sentinel value)
    df = df[df['lap'] < 1000].copy()

    # Filter by vehicle if specified
    if vehicle is not None:
        df = df[df['vehicle_number'] == vehicle].copy()
        if verbose:
            print(f"  Filtered to vehicle #{vehicle}: {len(df):,} rows")

    # Filter to max lap if specified
    if max_lap is not None:
        df = df[df['lap'] <= max_lap].copy()
        if verbose:
            print(f"  Filtered to laps <= {max_lap}")

    # Remove duplicates (keep last occurrence per lap per vehicle)
    # Using 'last' because erroneous early timestamps appear first in duplicates
    df = df.sort_values(['vehicle_number', 'lap', 'timestamp'])
    df = df.drop_duplicates(subset=['vehicle_number', 'lap'], keep='last')

    # Calculate lap times as diff between consecutive lap timestamps
    lap_times = []

    for veh in df['vehicle_number'].unique():
        vehicle_data = df[df['vehicle_number'] == veh].sort_values('lap').copy()

        # Lap time = timestamp of this lap - timestamp of previous lap
        vehicle_data['lap_time'] = vehicle_data['timestamp'].diff().dt.total_seconds()

        lap_times.append(vehicle_data)

    result = pd.concat(lap_times, ignore_index=True)

    # Remove lap 1 (no prior timestamp to diff from) and invalid times
    result = result[result['lap'] > 1].copy()
    result = result[result['lap_time'] > min_lap_time].copy()
    result = result[result['lap_time'] < max_lap_time].copy()

    if verbose:
        print(f"  Computed lap times: {len(result):,} valid laps")
        print(f"  Vehicles: {result['vehicle_number'].nunique()}")
        print(f"  Lap range: {result['lap'].min()} - {result['lap'].max()}")
        print(f"  Lap time range: {result['lap_time'].min():.2f}s - {result['lap_time'].max():.2f}s")

    return result[['vehicle_number', 'lap', 'timestamp', 'lap_time']]


def load_weather(
    file_path: Union[str, Path],
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load weather data for a race.

    Parameters
    ----------
    file_path : str or Path
        Path to weather CSV file (e.g., '26_Weather_Race 1.CSV')
    verbose : bool, default=False
        Print loading progress

    Returns
    -------
    pd.DataFrame
        Weather data with columns:
        - timestamp: datetime
        - air_temp: float (°C)
        - track_temp: float (°C)
        - humidity: float (%)
        - pressure: float (hPa)
        - wind_speed: float (m/s)
        - wind_direction: float (degrees)
        - rain: int (0 or 1)
    """
    if verbose:
        print(f"Loading weather from: {file_path}")

    df = pd.read_csv(file_path, sep=';')

    # Rename columns for consistency
    df = df.rename(columns={
        'TIME_UTC_STR': 'timestamp',
        'AIR_TEMP': 'air_temp',
        'TRACK_TEMP': 'track_temp',
        'HUMIDITY': 'humidity',
        'PRESSURE': 'pressure',
        'WIND_SPEED': 'wind_speed',
        'WIND_DIRECTION': 'wind_direction',
        'RAIN': 'rain'
    })

    # Parse timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Select relevant columns
    cols = ['timestamp', 'air_temp', 'track_temp', 'humidity',
            'pressure', 'wind_speed', 'wind_direction', 'rain']
    df = df[cols]

    if verbose:
        print(f"  Loaded {len(df)} weather readings")
        print(f"  Air temp: {df['air_temp'].mean():.1f}°C (mean)")
        print(f"  Track temp: {df['track_temp'].mean():.1f}°C (mean)")

    return df


def get_race_weather_summary(
    file_path: Union[str, Path],
    verbose: bool = False
) -> Dict:
    """
    Get summary weather statistics for a race.

    Parameters
    ----------
    file_path : str or Path
        Path to weather CSV file
    verbose : bool
        Print summary

    Returns
    -------
    dict
        Dictionary with mean weather values:
        - air_temp, track_temp, humidity, pressure, wind_speed
    """
    df = load_weather(file_path, verbose=False)

    summary = {
        'air_temp': df['air_temp'].mean(),
        'track_temp': df['track_temp'].mean(),
        'humidity': df['humidity'].mean(),
        'pressure': df['pressure'].mean(),
        'wind_speed': df['wind_speed'].mean()
    }

    if verbose:
        print(f"Weather summary:")
        print(f"  Air temp: {summary['air_temp']:.1f}°C")
        print(f"  Track temp: {summary['track_temp']:.1f}°C")
        print(f"  Humidity: {summary['humidity']:.1f}%")

    return summary


def load_endurance_analysis(
    file_path: Union[str, Path],
    vehicle: Optional[int] = None,
    verbose: bool = False
) -> pd.DataFrame:
    """
    Load endurance analysis data with sector times and flag status.

    Parameters
    ----------
    file_path : str or Path
        Path to endurance analysis CSV (e.g., '23_AnalysisEnduranceWithSections_Race 1.CSV')
    vehicle : int, optional
        Filter by vehicle number
    verbose : bool
        Print loading progress

    Returns
    -------
    pd.DataFrame
        Endurance data with columns:
        - vehicle_number, lap, lap_time
        - s1, s2, s3 (sector times in seconds)
        - kph (average speed)
        - flag_status (GF=green, FCY=full course yellow, FF=finish)
        - top_speed
        - pit_time (if pitted)
    """
    if verbose:
        print(f"Loading endurance analysis from: {file_path}")

    df = pd.read_csv(file_path, sep=';')

    # Strip whitespace from column names (CSV has leading spaces)
    df.columns = df.columns.str.strip()

    # Rename columns
    df = df.rename(columns={
        'NUMBER': 'vehicle_number',
        'LAP_NUMBER': 'lap',
        'LAP_TIME': 'lap_time_str',
        'S1_SECONDS': 's1',
        'S2_SECONDS': 's2',
        'S3_SECONDS': 's3',
        'KPH': 'kph',
        'FLAG_AT_FL': 'flag_status',
        'TOP_SPEED': 'top_speed',
        'PIT_TIME': 'pit_time'
    })

    # Convert vehicle number to int (handle leading zeros like '03')
    df['vehicle_number'] = pd.to_numeric(df['vehicle_number'], errors='coerce')

    # Filter by vehicle if specified
    if vehicle is not None:
        df = df[df['vehicle_number'] == vehicle].copy()

    # Select relevant columns
    cols = ['vehicle_number', 'lap', 's1', 's2', 's3', 'kph',
            'flag_status', 'top_speed', 'pit_time']
    df = df[[c for c in cols if c in df.columns]]

    # Create is_under_yellow flag
    if 'flag_status' in df.columns:
        df['is_under_yellow'] = df['flag_status'].isin(['FCY', 'SC']).astype(int)

    if verbose:
        print(f"  Loaded {len(df)} lap records")
        if 'is_under_yellow' in df.columns:
            yellow_pct = 100 * df['is_under_yellow'].sum() / len(df)
            print(f"  Under yellow: {yellow_pct:.1f}% of laps")

    return df


def get_available_vehicles(file_path: Union[str, Path]) -> List[int]:
    """
    Get list of vehicle numbers present in the dataset.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file

    Returns
    -------
    list of int
        Sorted list of vehicle numbers

    Examples
    --------
    >>> vehicles = get_available_vehicles('data.csv')
    >>> print(f"Found {len(vehicles)} vehicles: {vehicles}")
    """
    df = pd.read_csv(file_path, usecols=['vehicle_number'])
    vehicles = sorted(df['vehicle_number'].dropna().unique())
    return [int(v) for v in vehicles]


def get_available_parameters(file_path: Union[str, Path]) -> List[str]:
    """
    Get list of telemetry parameters present in the dataset.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file

    Returns
    -------
    list of str
        Sorted list of parameter names

    Examples
    --------
    >>> params = get_available_parameters('data.csv')
    >>> print(f"Found {len(params)} parameters: {params}")
    """
    df = pd.read_csv(file_path, usecols=['telemetry_name'])
    parameters = sorted(df['telemetry_name'].dropna().unique())
    return parameters


def validate_data_completeness(
    file_path: Union[str, Path],
    expected_vehicles: Optional[int] = None,
    expected_parameters: Optional[List[str]] = None,
    verbose: bool = True
) -> dict:
    """
    Validate data completeness and quality.

    Parameters
    ----------
    file_path : str or Path
        Path to CSV file
    expected_vehicles : int, optional
        Expected number of vehicles (e.g., 19 for full race)
    expected_parameters : list of str, optional
        Expected parameter names
    verbose : bool, default=True
        Print validation results

    Returns
    -------
    dict
        Validation results with keys:
        - vehicles_found: list of int
        - parameters_found: list of str
        - has_gps: bool
        - total_rows: int
        - validation_passed: bool

    Examples
    --------
    >>> result = validate_data_completeness('data.csv', expected_vehicles=19)
    >>> if not result['validation_passed']:
    ...     print("Data validation failed!")
    """
    if verbose:
        print("=" * 60)
        print("DATA VALIDATION")
        print("=" * 60)

    # Get vehicles and parameters
    vehicles = get_available_vehicles(file_path)
    parameters = get_available_parameters(file_path)

    # Check for GPS
    has_gps = ('VBOX_Lat_Min' in parameters and
               'VBOX_Long_Minutes' in parameters)

    # Count total rows
    df = pd.read_csv(file_path, usecols=['vehicle_number'])
    total_rows = len(df)

    # Validation checks
    validation_passed = True

    if verbose:
        print(f"\nVehicles found: {len(vehicles)}")
        print(f"  {vehicles}")

        if expected_vehicles is not None:
            if len(vehicles) == expected_vehicles:
                print(f"  ✅ Expected {expected_vehicles} vehicles - PASS")
            else:
                print(f"  ❌ Expected {expected_vehicles} vehicles - FAIL")
                validation_passed = False

        print(f"\nParameters found: {len(parameters)}")
        for param in parameters:
            print(f"  - {param}")

        if expected_parameters is not None:
            missing = set(expected_parameters) - set(parameters)
            if not missing:
                print(f"  ✅ All expected parameters present - PASS")
            else:
                print(f"  ❌ Missing parameters: {missing} - FAIL")
                validation_passed = False

        print(f"\nGPS data: {'✅ PRESENT' if has_gps else '❌ NOT FOUND'}")
        print(f"Total rows: {total_rows:,}")

        print("\n" + "=" * 60)
        if validation_passed:
            print("✅ VALIDATION PASSED")
        else:
            print("❌ VALIDATION FAILED")
        print("=" * 60)

    return {
        'vehicles_found': vehicles,
        'parameters_found': parameters,
        'has_gps': has_gps,
        'total_rows': total_rows,
        'validation_passed': validation_passed
    }
