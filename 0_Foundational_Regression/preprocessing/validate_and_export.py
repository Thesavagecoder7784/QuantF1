from pathlib import Path

import pandas as pd


REQUIRED_COLUMNS = [
    'Driver', 'Team', 'Compound', 'LapNumber', 'Stint',
    'lap_in_stint', 'fuel_kg', 'lap_time_seconds',
    'lap_time_fuel_corrected', 'anomaly_flag',
]


def validate_and_export(laps: pd.DataFrame, output_path: Path) -> None:
    """Run sanity checks and export to Parquet."""
    missing = [c for c in REQUIRED_COLUMNS if c not in laps.columns]
    assert not missing, f"Missing required columns: {missing}"

    clean = laps[laps['anomaly_flag'] == 'normal']
    assert clean['lap_time_seconds'].min() > 50, "Lap times suspiciously fast"
    assert clean['lap_time_seconds'].max() < 200, "Lap times suspiciously slow"

    assert clean['fuel_kg'].min() > 0, "Negative fuel weight"
    assert clean['fuel_kg'].max() <= 110, "Fuel exceeds regulation max"

    assert laps['lap_in_stint'].min() == 1, "Stint should start at lap 1"

    print(f"Total laps: {len(laps)}")
    print(f"Clean laps: {len(clean)}")
    print("Anomaly breakdown:")
    print(laps['anomaly_flag'].value_counts())
    print(f"Drivers: {laps['Driver'].nunique()}")
    print(f"Constructors: {laps['Team'].nunique()}")
    print(f"Compounds in clean data: {clean['Compound'].unique()}")

    laps.to_parquet(output_path, index=False)
    print(f"Exported to {output_path}")
