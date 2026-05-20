from pathlib import Path

from preprocessing.ingest_raw import ingest_race
from preprocessing.attach_metadata import attach_metadata
from preprocessing.compute_derived_features import compute_derived_features
from preprocessing.classify_anomalies import classify_anomalies
from preprocessing.validate_and_export import validate_and_export


def preprocess_race(year: int, race: str, output_dir: Path) -> Path:
    output_path = output_dir / f"{year}_{race}.parquet"

    laps = ingest_race(year, race)
    laps = attach_metadata(laps, year, race)
    laps = compute_derived_features(laps)
    laps = classify_anomalies(laps)
    validate_and_export(laps, output_path)

    return output_path


if __name__ == '__main__':
    output_dir = Path('./data/processed')
    output_dir.mkdir(parents=True, exist_ok=True)
    preprocess_race(2025, 'Hungary', output_dir)
