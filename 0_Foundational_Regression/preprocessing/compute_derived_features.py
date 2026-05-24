import pandas as pd


DRY_COMPOUNDS = {'HARD', 'MEDIUM', 'SOFT'}
WET_COMPOUNDS = {'INTERMEDIATE', 'WET'}


def _classify_compound(c) -> str:
    """Bucket a compound label into DRY / WET / UNKNOWN.

    UNKNOWN catches missing values and the occasional 'nan'/'None' string the
    FastF1 API emits for 2025 races where the compound field couldn't be parsed.
    """
    if pd.isna(c):
        return 'UNKNOWN'
    c = str(c).strip().upper()
    if c in DRY_COMPOUNDS:
        return 'DRY'
    if c in WET_COMPOUNDS:
        return 'WET'
    return 'UNKNOWN'


def compute_derived_features(laps: pd.DataFrame) -> pd.DataFrame:
    """Compute lap_in_stint, fuel_kg, lap_time_seconds, lap_time_fuel_corrected,
    and tag each lap with a DRY/WET/UNKNOWN compound regime.
    """
    laps['lap_time_seconds'] = laps['LapTime'].dt.total_seconds()

    laps['lap_in_stint'] = (
        laps.groupby(['Driver', 'Stint']).cumcount() + 1
    )

    # Globally-unique stint identifier. Within a single race file the (Driver, Stint)
    # pair is enough; including year+race lets concatenated multi-race datasets index
    # stint-level random effects (Pass 2 of the foundational regression) without
    # collisions between e.g. Norris's Monaco stint 1 and Spa stint 1.
    year = laps['year'].iloc[0] if 'year' in laps.columns else 'NA'
    race = laps['race'].iloc[0] if 'race' in laps.columns else 'NA'
    # Stint can be NaN on a handful of edge laps (race_start, missing); use 'NA'
    # so those rows still get a valid (but unique-per-driver) stint_id.
    stint_str = laps['Stint'].apply(lambda s: str(int(s)) if pd.notna(s) else 'NA')
    laps['stint_id'] = (
        f'{year}_{race}_'
        + laps['Driver'].astype(str)
        + '_S' + stint_str
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

    # Wet/dry regime — preserved on disk so the wet-conditions module
    # (Section 12 in the paper) can filter on the same canonical parquet files.
    laps['compound_condition'] = laps['Compound'].apply(_classify_compound)

    return laps
