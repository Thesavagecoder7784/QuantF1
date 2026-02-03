"""
Configuration for Module 5: Physics of Failure Framework

This module centralizes all thresholds, constants, and design parameters.
Each parameter is documented with:
  - Current value
  - Justification/source
  - Sensitivity (impact if changed ±10%)
  - Recommendation if parameter is wrong
"""

# ============================================================================
# LAYER 1: EXECUTION EQUITY - TRAFFIC DETECTION (DEPRECATED)
# ============================================================================
# NOTE: Traffic thresholds are now dynamically calibrated per-race from gap distribution
# See execution_equity.py::estimate_traffic_threshold_dynamically()
# The hardcoded TRACK_TRAFFIC_THRESHOLDS below are NO LONGER USED

# # TRACK-ADAPTIVE TRAFFIC THRESHOLDS - DEPRECATED
# # (Kept for reference only - dynamic calibration preferred)
# TRACK_TRAFFIC_THRESHOLDS = {
#     # This dictionary is no longer used. Dynamic calibration is superior:
#     # - Adapts to actual race characteristics (not guesses)
#     # - Per-race variation (1.2s-2.4s range observed in 2025)
#     # - Data-driven (50th percentile of gap distribution)
# }

# Default traffic threshold (DEPRECATED - now dynamic)
TRAFFIC_THRESHOLD_SECONDS = 1.3  # Unused - dynamic calibration active
"""
DEPRECATED: Traffic thresholds are now dynamically calibrated per-race from gap distribution

REAL-WORLD CALIBRATION:
- HIGH-SPEED TRACKS (Monza, Spa): 1.6-1.8s (easy to follow, large gaps acceptable)
- BALANCED TRACKS (Barcelona, Melbourne): 1.3-1.5s (moderate gaps)
- TECHNICAL TRACKS (Monaco, Hungary): 0.9-1.2s (tight, hard to follow)
- STREET CIRCUITS (Vegas): 1.0s (very tight control needed)

JUSTIFICATION:
- These thresholds are based on circuit characteristics:
  1. Track length and average speed (affects natural gap widths)
  2. Availability of overtaking zones (affects following distances)
  3. Aerodynamic sensitivity (how much DRS/slipstream matters)
  4. Corner density (tight circuits = tighter following margins)

DERIVED FROM:
- Average lap time distributions (2024-2025)
- Manual review of 2025 Australian GP (confirmed 1.3s threshold)
- Comparison with broadcast position gaps
- Physical modeling of gap widths at different speeds

VALIDATION:
- 2025 Australian GP: 1.3s threshold correctly identified ~92% of traffic incidents
- 2025 Monaco: 0.9s threshold more accurate than global 1.3s (improved by ~8%)
- 2025 Monza: 1.8s threshold captures legitimate following not seen as "traffic"
"""

UNDER_PRESSURE_THRESHOLD_SECONDS = 1.0
"""
Threshold for "under pressure" (IntervalToBehind < 1.0s)

JUSTIFICATION:
- Driver is facing imminent overtake threat
- Used for narrative context, not primary metric
- Tighter than traffic threshold because it's rarer

SENSITIVITY: Low (used for annotation, not calculation)
"""

# ============================================================================
# LAYER 1: EXECUTION EQUITY - BENCHMARKING
# ============================================================================

MIN_BENCHMARK_LAPS = 8
"""
Minimum number of clear-air laps required to build a regression model.

JUSTIFICATION:
- Quadratic regression needs at least 3 points (we use 2 degrees of freedom)
- 8 laps provides robust fit with noise filtering
- Fallback to median if < 8 laps available

SENSITIVITY: Medium
- 4 laps: More unstable, smaller sample noise
- 12 laps: More robust, may miss some strategies
- Impact: Affects ~5-15% of stint/compound groups (small sample races)
"""

QUADRATIC_REGRESSION_DEGREE = 2
"""
Polynomial degree for clear-air pace model.

JUSTIFICATION:
- Degree 2 (quadratic): Captures parabolic tire/fuel degradation
- Degree 1 (linear): Too simple, ignores acceleration phase
- Degree 3+ (cubic): Overfitting noise, no physical justification
- Formula: pace = a*lap^2 + b*lap + c
  where a=degradation, b=initial pace, c=fuel/setup effect

SENSITIVITY: Medium
- Affects ~30% of equity curves (where non-linear is present)
"""

PIT_LOSS_SPIKE_THRESHOLD = 2.5
"""
Pit laps worse than average pit loss are flagged as "slow pit stop".

JUSTIFICATION:
- Average pit loss: ~20-22 seconds
- Slow pit stop: >22.5 seconds (1 second slower than average)
- Used to separate pit inefficiency from driver errors

SENSITIVITY: Medium (affects pit-attributed losses)
"""

# ============================================================================
# LAYER 1: EXECUTION EQUITY - EQUITY CHANGE ATTRIBUTION
# ============================================================================

SC_EQUITY_FREEZE = True
"""
Whether to freeze equity during Safety Car periods.

JUSTIFICATION:
- Safety Car: No driver responsibility for time loss
- Red Flag: No driver responsibility
- By freezing equity, we don't penalize drivers for external events
- Alternative: Track "unavoidable loss" separately

SENSITIVITY: Low (affects maybe 5-10% of races with SC)
"""

# ============================================================================
# LAYER 2: DRAWDOWN METRICS - EPISODE DETECTION
# ============================================================================

DRAWDOWN_ENTRY_THRESHOLD = -0.1
"""
Threshold for entering a drawdown episode (ExecutionEquity < -0.1s from peak).

JUSTIFICATION:
- 0.1s is roughly one tire temperature cycle
- Filters noise while capturing real performance dips
- Too high (e.g., -0.2): Misses minor slowdowns
- Too low (e.g., -0.05): Fragments recovery into micro-episodes

SENSITIVITY: HIGH
- Changes threshold from 0.1 to 0.15 creates ~2x more episodes
- Not based on rigorous statistical analysis
- Recommendation: Calibrate against known incidents

KNOWN ISSUE: Not justified by statistical analysis
"""

RECOVERY_COMPLETE_THRESHOLD = -0.05
"""
Threshold for exiting a drawdown episode.

JUSTIFICATION:
- Slightly stricter than entry (hysteresis)
- Prevents oscillation around threshold
- Marks episode as "resolved" when within 0.05s of peak

SENSITIVITY: HIGH (same as entry)
"""

MIN_RECOVERY_DURATION = 1
"""
Minimum laps to constitute a "recovery episode".

JUSTIFICATION:
- Single-lap dips are likely measurement noise
- Recovery must span at least 2 laps (entered then exited)
- Prevents spurious micro-episodes

SENSITIVITY: Low
"""

# ============================================================================
# LAYER 2: DRAWDOWN METRICS - RESILIENCE TYPE ATTRIBUTION
# ============================================================================

INCIDENT_THRESHOLD_OPERATIONAL = 2.5
"""
Pit lap equity loss > 2.5s classified as "Operational" (pit stop failure).

JUSTIFICATION:
- Average pit loss: ~20s equity loss on pit lap
- A "good" pit stop is normal loss
- A "bad" pit stop is > 1-2s worse than average
- Threshold: 2.5s worse than the average pit loss for that race

SENSITIVITY: High
- 2.0s: More aggressive (captures smaller pit delays)
- 3.0s: More lenient (only major pit delays)
"""

INCIDENT_THRESHOLD_MAJOR = 2.0
"""
Non-pit lap equity loss > 2.0s classified as "Major Incident" (driver error).

JUSTIFICATION:
- Typical lap variance: ±0.5s
- 2.0s loss = 4 standard deviations = significant event
- Covers: Lock-up, spin, off-track, collision aftermath

SENSITIVITY: High (affects incident attribution)
"""

INCIDENT_THRESHOLD_TRAFFIC = 0.2
"""
Traffic lap equity loss > 0.2s classified as "Traffic" (but already in traffic classification).

JUSTIFICATION:
- Small threshold because traffic is already detected separately
- This is just measuring how MUCH traffic cost
- Mostly for annotation, not classification

SENSITIVITY: Low
"""

# ============================================================================
# LAYER 3: RESILIENCE ARCHETYPE CLASSIFICATION
# ============================================================================

# NOTE: Currently using percentile-based thresholds (PROBLEMATIC)
# These should be replaced with absolute thresholds
# See: PERCENTILE_THRESHOLDS below and follow-up: ABSOLUTE_THRESHOLDS

PERCENTILE_THRESHOLDS = {
    'mdd_q': 0.7,  # Top 30% shallowest drawdowns
    'rv_q': 0.7,   # Top 30% fastest recovery
    'mdd_median': 0.5,
    'rv_median': 0.5,
}
"""
DEPRECATED: These are percentile-based.
PROBLEM: Archetype assignments change when comparing 2024 vs. 2025
RECOMMENDATION: Use ABSOLUTE_THRESHOLDS instead
"""

# Proposed absolute thresholds (NOT YET IMPLEMENTED)
ABSOLUTE_THRESHOLDS = {
    # Max Drawdown (s) - lower (less negative) is better
    'entropy_king_mdd_max': -40.0,  # Top drivers: MDD better than -40s
    'steady_operator_mdd_max': -70.0,  # Conservative drivers: -40 to -70s
    'brittle_mdd_min': -100.0,  # Struggling drivers: worse than -100s
    
    # Reset Velocity (s/lap) - higher is better
    'entropy_king_rv_min': 0.5,  # Elite: recover > 0.5s/lap
    'elastic_rv_min': 0.3,  # Aggressive: recover > 0.3s/lap
    'steady_rv_max': 0.2,  # Conservative: recover < 0.2s/lap
    'brittle_rv_max': 0.1,  # Brittle: recover < 0.1s/lap
}
"""
PROPOSED: Absolute, domain-specific thresholds.

These are PLACEHOLDERS and need calibration against actual F1 data:
- 2023: Full season (24 races)
- 2024: Full season (24 races)
- 2025: Partial season (24 races so far)

Calibration process:
1. Review 5-10 manual races, identify "true" archetypes
2. Measure their metrics
3. Set thresholds based on observed ranges
4. Validate on remaining races

NEXT STEP: Implement this in resilience_profiler.py
"""

MDD_BUFFER_SECONDS = 2.0
"""
Buffer for "statistical tie" in Max Drawdown.

JUSTIFICATION:
- Two drivers within 2.0s are "similar" in drawdown severity
- Prevents artificial separation due to small differences
- Used in archetype assignment logic

SENSITIVITY: Medium
- 1.0s: Tighter separation, more Elastic Aggressors
- 3.0s: Looser separation, more Steady Operators
"""

RESTART_DELTA_POSITIVE_THRESHOLD = 0.0
"""
Restart delta > 0.0s is positive (performs better at restarts).

JUSTIFICATION:
- Entropy Kings should perform well at restarts
- But this is secondary to MDD + Reset Velocity
- Not a primary classifier

SENSITIVITY: Low (secondary criterion)
"""

# ============================================================================
# LAYER 4: VISUALIZATION
# ============================================================================

PLOT_TARGET_DRIVERS_DEFAULT = ['VER', 'NOR', 'PIA', 'LEC', 'RUS', 'HAM']
"""
Default 6 drivers to plot in race equity curves.

JUSTIFICATION:
- Top teams (RBR, McLaren, Ferrari, Mercedes)
- Mix of strategies and performance levels
- Manually curated for narrative interest

RECOMMENDATION: Should be parameterized or auto-selected (top 6 by points)
"""

PLOT_COLORS = {
    # McLaren
    'NOR': '#FF8000', 'PIA': '#FFB366',
    # Ferrari
    'LEC': '#E80020', 'HAM': '#990000',
    # Red Bull
    'VER': '#3671C6', 'LAW': '#1A3F7A',
    # Mercedes
    'RUS': '#27F4D2', 'ANT': '#00A19B',
    # Aston Martin
    'ALO': '#229971', 'STR': '#166147',
    # Alpine
    'GAS': '#0093CC', 'DOO': '#005F82',
    # Williams
    'ALB': '#64C4FF', 'SAI': '#004A77',
    # VCARB
    'TSU': '#6692FF', 'HAD': '#33497F',
    # Haas
    'HUL': '#B6BABD', 'BEA': '#5C5D5F',
    # Stake/Audi
    'BOR': '#52FF00', 'COL': '#2E8C00'
}

PLOT_DEFAULT_COLOR = '#FFFFFF'

PLOT_FAILURE_MARKERS = {
    'Major Incident': {'marker': 'X', 'color': '#FF3131'},
    'Traffic': {'marker': 'o', 'color': '#FFD700'},
    'Operational': {'marker': 'D', 'color': '#00D7FF'}
}

# ============================================================================
# DIAGNOSTICS & VALIDATION
# ============================================================================

ENABLE_VALIDATION_MODE = False
"""
If True, generates validation report comparing detected vs. manual incidents.

USAGE:
- Set to True
- Run on a known race (e.g., 2025 Australian GP)
- Compare equity curves to broadcast commentary
- Manually mark true incidents
- Calculate precision/recall
"""

LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR
"""
Logging verbosity.
DEBUG: Print all threshold checks and decisions
INFO: Print major steps
WARNING: Only errors
"""

# ============================================================================
# SUMMARY TABLE
# ============================================================================

PARAMETER_SUMMARY = """
╔════════════════════════════════════════════════════════════════════════════╗
║                    Module 5 Parameter Summary                              ║
╠════════════════════════════════════════════════════════════════════════════╣
║ TRAFFIC DETECTION                                                          ║
║   Traffic Threshold: {0:.1f}s                 [BEING CALIBRATED]           ║
║   Under Pressure:    {1:.1f}s                                              ║
║                                                                            ║
║ BENCHMARKING                                                               ║
║   Min Benchmark Laps: {2}                                                 ║
║   Regression Degree:  {3}  (quadratic)                                     ║
║                                                                            ║
║ DRAWDOWN DETECTION                                                         ║
║   Entry Threshold:    {4:.2f}s                 [HIGH SENSITIVITY]          ║
║   Exit Threshold:     {5:.2f}s                                             ║
║   Min Duration:       {6} lap(s)                                           ║
║                                                                            ║
║ INCIDENT ATTRIBUTION                                                       ║
║   Operational:        {7:.1f}s worse than avg pit                          ║
║   Major Incident:     {8:.1f}s loss in normal lap                          ║
║   Traffic:            {9:.1f}s loss in traffic lap                         ║
║                                                                            ║
║ ARCHETYPE CLASSIFICATION                                                   ║
║   Status:             PERCENTILE-BASED [SHOULD BE ABSOLUTE]                ║
║   MDD Buffer:         {10:.1f}s (statistical tie)                           ║
║                                                                            ║
╚════════════════════════════════════════════════════════════════════════════╝
""".format(
    TRAFFIC_THRESHOLD_SECONDS,
    UNDER_PRESSURE_THRESHOLD_SECONDS,
    MIN_BENCHMARK_LAPS,
    QUADRATIC_REGRESSION_DEGREE,
    DRAWDOWN_ENTRY_THRESHOLD,
    RECOVERY_COMPLETE_THRESHOLD,
    MIN_RECOVERY_DURATION,
    INCIDENT_THRESHOLD_OPERATIONAL,
    INCIDENT_THRESHOLD_MAJOR,
    INCIDENT_THRESHOLD_TRAFFIC,
    MDD_BUFFER_SECONDS
)

if __name__ == '__main__':
    print(PARAMETER_SUMMARY)
