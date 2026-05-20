import pandas as pd

# Fuel burn rates are placeholder assumptions for the Session 1 model: a constant
# kg/lap derived from starting_fuel_kg / race_distance. Hungary 2025 is 70 laps,
# so 1.55 kg/lap consumes ~108.5 kg and leaves a small end-of-race reserve. This
# stand-in is good enough for the foundational regression; the latent-fuel
# upgrade (estimating burn per car from telemetry) is scheduled for June 2026.
METADATA = {
    (2025, 'Hungary'): {
        'weather': 'dry',
        'circuit_type': 'permanent',
        'starting_fuel_kg': 110.0,
        'fuel_burn_per_lap': 1.55,
        'fuel_cost_per_kg': 0.03,
    },
}


def attach_metadata(laps: pd.DataFrame, year: int, race: str) -> pd.DataFrame:
    """Attach race-level context."""
    key = (year, race)
    if key not in METADATA:
        raise ValueError(f"No metadata for {key}")

    for k, v in METADATA[key].items():
        laps[k] = v

    return laps
