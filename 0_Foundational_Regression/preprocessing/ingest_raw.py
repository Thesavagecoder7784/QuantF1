import fastf1
from pathlib import Path
import pandas as pd

CACHE_DIR = Path('./cache')
CACHE_DIR.mkdir(exist_ok=True)
fastf1.Cache.enable_cache(str(CACHE_DIR))


def ingest_race(year: int, race: str) -> pd.DataFrame:
    """Pull lap data for a single race from FastF1."""
    session = fastf1.get_session(year, race, 'R')
    session.load(laps=True, telemetry=False, weather=True, messages=True)

    laps = session.laps.copy()
    laps['year'] = year
    laps['race'] = race
    laps['circuit'] = session.event['EventName']

    return laps
