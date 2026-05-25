"""Sanity-check every Parquet in data/processed/.

Reports per-race compound-regime breakdown (DRY / WET / UNKNOWN) and aggregate
totals. Flags races with concerning patterns. Distinguishes:

  - 'wet'         : majority WET clean laps; expected, not an error.
  - 'data_quality': >5% UNKNOWN-compound laps (FastF1 2025 issue where entire
                    stints sometimes lose their compound label as 'nan'/'None').
                    Worth knowing - those laps drop out of the dry-pace model.
  - 'low_dry'     : fewer than 100 DRY clean laps (typically pure-wet races; the
                    race contributes no dry-pace data to the model).
  - 'no_total_laps': legacy parquet predating the multi-race attach_metadata
                    refactor (no `total_laps` column). Currently only
                    2025_Hungary.parquet, which is dedup'd out anyway.

Usage:
    python verify_processed.py
"""

import sys
from pathlib import Path

import pandas as pd


HERE = Path(__file__).resolve().parent
DEFAULT_DIR = HERE / 'data' / 'processed'

UNKNOWN_RATIO_THRESHOLD = 0.05   # >5% UNKNOWN -> data quality flag
LOW_DRY_THRESHOLD       = 100    # <100 DRY -> race contributes ~nothing to dry model
WET_MAJORITY_THRESHOLD  = 0.5    # >50% WET clean -> wet race (expected, not error)


def verify_one(path: Path) -> dict:
    df = pd.read_parquet(path)
    clean = df[df['anomaly_flag'] == 'normal']
    regime = clean['compound_condition'].value_counts() if 'compound_condition' in clean.columns else pd.Series()

    return {
        'file':         path.name,
        'total_laps':   len(df),
        'clean_laps':   len(clean),
        'dry':          int(regime.get('DRY', 0)),
        'wet':          int(regime.get('WET', 0)),
        'unknown':      int(regime.get('UNKNOWN', 0)),
        'drivers':      df['Driver'].nunique(),
        'compounds_raw': sorted({str(c) for c in clean['Compound'].dropna().unique()}),
        'total_race_laps': int(df['total_laps'].iloc[0]) if 'total_laps' in df.columns else None,
        'has_compound_condition': 'compound_condition' in df.columns,
    }


def flag(r: dict) -> list[tuple[str, str]]:
    flags = []
    if not r['has_compound_condition']:
        flags.append(('no_compound_condition',
                      'missing compound_condition column - re-run preprocessing'))
        return flags
    if r['total_race_laps'] is None:
        flags.append(('no_total_laps',
                      'legacy parquet, missing total_laps column'))

    clean = r['clean_laps']
    if clean == 0:
        return flags  # nothing else to evaluate

    wet_ratio = r['wet'] / clean
    unk_ratio = r['unknown'] / clean

    if wet_ratio >= WET_MAJORITY_THRESHOLD:
        flags.append(('wet',
                      f'wet race: {r["wet"]}/{clean} ({100*wet_ratio:.0f}%) clean laps on wet tyres'))
    if unk_ratio > UNKNOWN_RATIO_THRESHOLD:
        flags.append(('data_quality',
                      f'{r["unknown"]} ({100*unk_ratio:.1f}%) clean laps have UNKNOWN compound '
                      '(FastF1 may have lost the compound label for whole stints)'))
    if r['dry'] < LOW_DRY_THRESHOLD and wet_ratio < WET_MAJORITY_THRESHOLD:
        flags.append(('low_dry',
                      f'only {r["dry"]} DRY clean laps - race contributes minimally to dry-pace model'))
    return flags


def main(argv=None):
    target_dir = DEFAULT_DIR if not argv else Path(argv[0])
    parquets = sorted(target_dir.glob('*.parquet'))
    if not parquets:
        print(f'No parquet files in {target_dir}')
        return 1

    print(f'Found {len(parquets)} parquet files in {target_dir}\n')

    totals = {'total_laps': 0, 'clean_laps': 0, 'dry': 0, 'wet': 0, 'unknown': 0}
    rows = []
    flag_buckets = {'wet': [], 'data_quality': [], 'low_dry': [], 'no_total_laps': [], 'no_compound_condition': []}

    for p in parquets:
        try:
            r = verify_one(p)
        except Exception as e:
            print(f'  ERROR reading {p.name}: {e}')
            continue
        fs = flag(r)
        for f_kind, _ in fs:
            flag_buckets.setdefault(f_kind, []).append(p.name)

        for k in totals:
            totals[k] += r.get(k, 0)
        rows.append((r, fs))

        kind_tag = ','.join(sorted({k for k, _ in fs})) or 'OK'
        print(f'  [{kind_tag:>12s}]  {p.name:35s}  '
              f'DRY={r["dry"]:>4d}  WET={r["wet"]:>3d}  UNK={r["unknown"]:>3d}  '
              f'drivers={r["drivers"]:>2d}  race_laps={r["total_race_laps"]}')
        for _, msg in fs:
            print(f'                 - {msg}')

    print()
    print('=' * 78)
    print('AGGREGATE')
    print('=' * 78)
    print(f'  Files processed:    {len(parquets)}')
    print(f'  Total laps:         {totals["total_laps"]:,}')
    print(f'  Clean laps:         {totals["clean_laps"]:,}')
    print(f'    DRY:              {totals["dry"]:,}')
    print(f'    WET:              {totals["wet"]:,}')
    print(f'    UNKNOWN:          {totals["unknown"]:,}')

    print('\nFlag summary:')
    for kind, files in flag_buckets.items():
        if files:
            print(f'  {kind} ({len(files)}):')
            for fn in files:
                print(f'    - {fn}')

    # Exit code: only non-zero if there's a real data-quality issue, not for
    # benign wet/low_dry flags (those are expected race characteristics).
    serious = flag_buckets.get('data_quality', []) + flag_buckets.get('no_compound_condition', [])
    return 0 if not serious else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
