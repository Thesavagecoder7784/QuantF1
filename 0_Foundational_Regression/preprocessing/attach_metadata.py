"""Attach race-level context to a laps DataFrame.

Config lives in config/circuits.yaml. Fuel burn is derived per-race from total laps
(starting_fuel_kg minus reserve, divided by race length) since lap count varies
across the calendar. The constant placeholder will be replaced by per-car latent
estimates from telemetry in the June 2026 latent-fuel upgrade.
"""

from functools import lru_cache
from pathlib import Path

import pandas as pd
import yaml


_CONFIG_PATH = Path(__file__).resolve().parent.parent / 'config' / 'circuits.yaml'


@lru_cache(maxsize=1)
def _load_config():
    with open(_CONFIG_PATH) as f:
        return yaml.safe_load(f)


def _resolve_circuit(race: str, cfg: dict) -> dict:
    """Resolve a race identifier (Location or alias) to its circuit config."""
    aliases = cfg.get('aliases', {}) or {}
    circuits = cfg.get('circuits', {}) or {}
    canonical = aliases.get(race, race)
    return circuits.get(canonical, {})


def attach_metadata(laps: pd.DataFrame, year: int, race: str) -> pd.DataFrame:
    """Attach race-level context columns.

    `fuel_burn_per_lap` is derived from the actual race length so the
    same constants work for 50-lap Bahrain and 78-lap Monaco.
    """
    cfg = _load_config()
    defaults = cfg['defaults']
    circuit = _resolve_circuit(race, cfg)

    total_laps = int(laps['LapNumber'].max())
    if total_laps <= 0:
        raise ValueError(f"Cannot derive fuel burn: LapNumber.max()={total_laps} for {year} {race}")

    starting = defaults['starting_fuel_kg']
    reserve = defaults['fuel_reserve_kg']
    fuel_burn_per_lap = (starting - reserve) / total_laps

    laps['starting_fuel_kg'] = starting
    laps['fuel_burn_per_lap'] = fuel_burn_per_lap
    laps['fuel_cost_per_kg'] = defaults['fuel_cost_per_kg']
    laps['weather'] = circuit.get('weather', defaults['weather'])
    laps['circuit_type'] = circuit.get('circuit_type', defaults['circuit_type'])
    laps['total_laps'] = total_laps

    return laps
