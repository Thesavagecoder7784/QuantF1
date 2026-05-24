"""Multi-race preprocessing orchestrator.

Walks the FastF1 schedule for the given years and runs the single-race pipeline
on each. Skips already-processed races (idempotent), logs failures so a single
bad race doesn't kill the whole run.

Usage:
    python preprocess_all.py                  # 2024 + 2025
    python preprocess_all.py 2024             # just 2024
    python preprocess_all.py 2024 2025 --force  # force-rebuild every parquet
"""

import argparse
import sys
import traceback
from pathlib import Path

import fastf1

from preprocess_race import preprocess_race


HERE = Path(__file__).resolve().parent
DEFAULT_OUTPUT = HERE / 'data' / 'processed'
DEFAULT_CACHE = HERE / 'cache'


def _race_entries(year: int):
    """Yield (location, event_name) for each non-testing round in the year."""
    schedule = fastf1.get_event_schedule(year)
    for _, event in schedule.iterrows():
        if event['RoundNumber'] == 0:
            continue
        yield event['Location'], event['EventName']


def preprocess_all(years, output_dir: Path, force: bool = False):
    output_dir.mkdir(parents=True, exist_ok=True)
    successes, skipped, failures = [], [], []

    for year in years:
        for location, event_name in _race_entries(year):
            out_path = output_dir / f'{year}_{location}.parquet'
            tag = f'{year} {location} ({event_name})'

            if out_path.exists() and not force:
                print(f'SKIP    {tag}  -> {out_path.name} (exists)')
                skipped.append((year, location))
                continue

            try:
                print(f'PROCESS {tag}')
                preprocess_race(year, location, output_dir)
                successes.append((year, location))
            except Exception as e:
                print(f'FAIL    {tag}: {e}', flush=True)
                traceback.print_exc()
                failures.append((year, location, str(e)))

    print()
    print('=' * 70)
    print('SUMMARY')
    print('=' * 70)
    print(f'  Succeeded: {len(successes)}')
    print(f'  Skipped:   {len(skipped)}')
    print(f'  Failed:    {len(failures)}')
    if failures:
        print('\nFailures:')
        for year, loc, msg in failures:
            print(f'  {year} {loc}: {msg}')

    return {'successes': successes, 'skipped': skipped, 'failures': failures}


def main(argv=None):
    parser = argparse.ArgumentParser(description='Run preprocessing across multiple races.')
    parser.add_argument('years', nargs='*', type=int, default=[2024, 2025],
                        help='Seasons to process (default: 2024 2025).')
    parser.add_argument('--force', action='store_true',
                        help='Re-run even if the parquet already exists.')
    parser.add_argument('--output-dir', type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument('--cache-dir', type=Path, default=DEFAULT_CACHE)
    args = parser.parse_args(argv)

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(args.cache_dir))

    result = preprocess_all(args.years, args.output_dir, force=args.force)
    return 0 if not result['failures'] else 1


if __name__ == '__main__':
    sys.exit(main())
