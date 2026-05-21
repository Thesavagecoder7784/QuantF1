# 0_Foundational_Regression

Hierarchical Bayesian baseline for Formula 1 lap times. From a single race it estimates driver effects, constructor effects, and compound-specific tyre degradation — the foundation downstream modules (StartPerformance, regime-sensitivity, latent-fuel) build on.

## Model

For each clean lap *i*:

```
lap_time_fuel_corrected_i ~ Normal(μ_i, σ)

μ_i = μ_0
    + α_driver[i]
    + β_constructor[i]
    + τ_compound[i]
    + linear_wear[compound]  * lap_in_stint_c
    + quad_wear[compound]    * lap_in_stint_c²
```

- `α_driver`, `β_constructor`, `τ_compound` are `ZeroSumNormal` random effects (sum-to-zero across levels) so each block is identified against `μ_0`.
- `lap_in_stint` is centered to decorrelate the linear and quadratic wear terms.
- Sampled with PyMC NUTS, 4 chains × 2000 draws (1500 tune), `target_accept=0.95`.

## Pipeline

```
FastF1 ──► ingest_raw ──► attach_metadata ──► compute_derived_features
       ──► classify_anomalies ──► validate_and_export ──► Parquet
       ──► notebook (PyMC) ──► trace.nc + CSVs + summary.md + figures
```

### Preprocessing (`preprocessing/`)

| Module | Purpose |
|---|---|
| `ingest_raw.py` | Pull the Race session from FastF1 (laps + weather + messages). Caches HTTP requests to `cache/`. |
| `attach_metadata.py` | Attach race-level constants: weather, circuit type, starting fuel, fuel burn per lap, fuel cost. Constants for now — latent-fuel telemetry estimation is scheduled June 2026. |
| `compute_derived_features.py` | `lap_time_seconds`, `lap_in_stint`, `fuel_kg`, `lap_time_fuel_corrected`. |
| `classify_anomalies.py` | Flag laps to exclude from pace analysis. Precedence (first match wins): `race_start` (lap 1, standing-start dominated) → `out_lap` → `in_lap` → `track_status` (non-green) → `missing` → `outlier` (>5σ from driver median on clean laps). |
| `validate_and_export.py` | Sanity-check column presence, lap-time ranges, fuel weight, stint indexing — then write Parquet. |

Run the full pipeline:

```bash
python preprocess_race.py
```

Currently hard-coded to Hungary 2025; add new races by extending `METADATA` in `attach_metadata.py` and editing the call site.

### Modelling (`notebooks/01_Hungary_2025_baseline.ipynb`)

Six cells:

1. Imports, paths, env check
2. Load Parquet, filter to `anomaly_flag == 'normal'`, build categorical indices, center `lap_in_stint`
3. Specify the model (above)
4. Sample with NUTS; save trace
5. Convergence diagnostics, driver/constructor rankings, variance decomposition, tyre coefficients; write CSVs and `summary.md`
6. Forest plots, trace plots, posterior predictive check

## Outputs

| Path | Contents |
|---|---|
| `data/processed/2025_Hungary.parquet` | Canonical model input — all laps with derived features and anomaly flags |
| `results/hungary_2025_baseline_trace.nc` | Full InferenceData (NetCDF via h5netcdf) |
| `results/hungary_2025_driver_effects.csv` | Posterior mean + 95% HDI per driver |
| `results/hungary_2025_constructor_effects.csv` | Posterior mean + 95% HDI per constructor |
| `results/hungary_2025_summary.md` | Provenance, convergence, variance decomposition, tyre coefficients, top-5 drivers and constructors |
| `figures/00_data_distribution.png` | Response distribution + by-driver boxplot |
| `figures/01_hungary_driver_effects.png` | Driver forest plot (95% HDI) |
| `figures/02_hungary_constructor_effects.png` | Constructor forest plot (95% HDI) |
| `figures/03_hungary_hyperparameter_traces.png` | Trace plots for σ_driver, σ_constructor, σ, μ_0 |
| `figures/04_hungary_posterior_predictive.png` | PPC density overlay |

## Environment

- Python 3.14
- PyMC ≥ 6
- ArviZ ≥ 1.1 (1.x renamed `hdi_prob` → `ci_prob` in `az.summary`, `hdi_prob` → `prob` in `az.hdi`, replaced `plot_ppc` with `plot_ppc_dist`)
- `h5netcdf` + `h5py` for NetCDF trace I/O
- `fastf1` for data ingestion
- pandas, numpy, matplotlib, seaborn

```bash
pip install pymc arviz h5netcdf h5py fastf1 pandas numpy matplotlib seaborn
```

## Known limitations

Carried-forward items, deferred not buggy:

- **Fuel correction is a fixed linear detrend.** `fuel_burn_per_lap` is a constant in `attach_metadata.py`. Telemetry-based per-car estimation lands June 2026.
- **Driver-constructor confounding** is intrinsic to single-race analysis: each constructor has exactly two drivers, so the priors do most of the work splitting the two blocks. Resolved by cross-race pooling.
- **IID Gaussian residuals.** Within-stint laps are autocorrelated (track evolution, fuel temperature, traffic). The posterior is slightly overconfident as a result.
- **No explicit track-evolution term.** Rubber-in is currently absorbed by the residual; for permanent circuits this is ~1–3 s/race.
- **`tyre_intercept`** is the baseline pace at the *mean* clean-stint position (since `lap_in_stint` is centered), not fresh-tyre pace. Interpret accordingly.
- Lap 1 is excluded from the pace model (`race_start` flag). Lap-1 performance — positions gained, racecraft — is the StartPerformance module's job (see paper Section X).

## Layout

```
0_Foundational_Regression/
├── preprocess_race.py              # pipeline orchestrator
├── preprocessing/                  # ingest + clean + validate
├── data/processed/                 # canonical Parquet outputs
├── notebooks/                      # Hungary 2025 baseline
├── results/                        # trace, CSVs, summary
├── figures/                        # PNGs
├── cache/                          # FastF1 HTTP cache (not committed)
└── models/                         # reserved
```
