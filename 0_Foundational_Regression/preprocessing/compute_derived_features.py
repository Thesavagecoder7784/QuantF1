import pandas as pd


def compute_derived_features(laps: pd.DataFrame) -> pd.DataFrame:
    """Compute lap_in_stint, fuel_kg, lap_time_seconds, lap_time_fuel_corrected."""
    laps['lap_time_seconds'] = laps['LapTime'].dt.total_seconds()

    laps['lap_in_stint'] = (
        laps.groupby(['Driver', 'Stint']).cumcount() + 1
    )

    # LapNumber is 1-indexed, so lap 1 carries full starting fuel.
    laps['fuel_kg'] = (
        laps['starting_fuel_kg']
        - laps['fuel_burn_per_lap'] * (laps['LapNumber'] - 1)
    )

    laps['lap_time_fuel_corrected'] = (
        laps['lap_time_seconds']
        - laps['fuel_cost_per_kg'] * laps['fuel_kg']
    )

    return laps
