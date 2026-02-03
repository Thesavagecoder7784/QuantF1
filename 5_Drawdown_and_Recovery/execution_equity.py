import fastf1
import pandas as pd
import numpy as np
import warnings
import os
import sys
from scipy import stats

# Add parent directory to path for config import
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    UNDER_PRESSURE_THRESHOLD_SECONDS,
    MIN_BENCHMARK_LAPS,
    QUADRATIC_REGRESSION_DEGREE,
    PIT_LOSS_SPIKE_THRESHOLD,
    SC_EQUITY_FREEZE,
    INCIDENT_THRESHOLD_OPERATIONAL,
    INCIDENT_THRESHOLD_MAJOR,
    INCIDENT_THRESHOLD_TRAFFIC,
    LOG_LEVEL
)

warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

def estimate_traffic_threshold_dynamically(all_laps):
    """
    Dynamically calibrate traffic threshold from actual race data.
    
    MECHANISM: Traffic gaps have natural bimodal distribution:
    - Tight followers: 0.2-1.2s (constrained by following rules/DRS)
    - Regular following: 1.2-2.0s (deliberate gap maintenance)
    - Clear air: 2.0-9.0s (natural expansion)
    
    We find the natural boundary between following behavior and clear air.
    """
    valid_gaps = all_laps[(~all_laps['IsPit']) & (~all_laps['IsSC']) & 
                          (all_laps['IntervalToAhead'] > 0.1) & 
                          (all_laps['IntervalToAhead'] < 9.0)]['IntervalToAhead'].values
    
    if len(valid_gaps) < 50:
        return 1.3
    
    try:
        # Find the gap where distribution changes behavior
        # Use the gap at 50th percentile as separation between "following" and "clear"
        # Drivers maintaining tighter gaps (≤50th) are "in traffic"
        # Drivers with larger gaps (>50th) are "clear air"
        threshold = np.percentile(valid_gaps, 50)
        
        # Constrain to realistic range (0.8s-3.0s) - higher cap allows natural variation
        return np.clip(threshold, 0.8, 3.0)
    except:
        return 1.3


def calculate_execution_equity(year: int, race_name: str):
    """
    Calculates the 'Execution Equity' curve for each driver with Physics of Failure attribution.
    
    DYNAMIC CALIBRATION (Data-Driven, Not Hardcoded):
    - Analyzes actual gap distribution from race
    - Finds natural separation between "traffic" and "clear air" regimes
    - No config file thresholds needed - learns from the data itself
    """
    print(f"Calculating Execution Equity for {year} {race_name} (Physics of Failure Model)\n")
    print(f"  → Calibrating traffic threshold from actual race data...")
    
    try:
        cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
        fastf1.Cache.enable_cache(cache_path)
        session = fastf1.get_session(year, race_name, 'R')
        session.load(laps=True, telemetry=True, weather=False, messages=True)

        all_laps = session.laps.copy()
        
        # 1. Identify Contextual Laps
        all_laps['IsPit'] = (all_laps['PitInTime'].notna()) | (all_laps['PitOutTime'].notna())
        if 'TrackStatus' in all_laps.columns:
            all_laps['IsSC'] = all_laps['TrackStatus'].apply(lambda x: x != '1')
        else:
            all_laps['IsSC'] = False
            
        # 2. Interval Recognition (Ahead/Behind)
        # Calculate intervals by comparing 'Time' (end of lap) between cars on the same lap.
        all_laps['TimeSec'] = all_laps['Time'].dt.total_seconds()
        
        all_laps['IntervalToAhead'] = 10.0 # Default clear air
        all_laps['IntervalToBehind'] = 10.0
        
        for lap_num in all_laps['LapNumber'].unique():
            lap_data = all_laps[all_laps['LapNumber'] == lap_num].sort_values('TimeSec')
            if len(lap_data) < 2: continue
            
            intervals = lap_data['TimeSec'].diff()
            all_laps.loc[lap_data.index, 'IntervalToAhead'] = intervals.fillna(10.0)
            
            shifted_intervals = intervals.shift(-1)
            all_laps.loc[lap_data.index, 'IntervalToBehind'] = shifted_intervals.fillna(10.0)

        # DYNAMIC CALIBRATION: Learn threshold from this race's data
        traffic_threshold = estimate_traffic_threshold_dynamically(all_laps)
        print(f"  ✓ Dynamically calibrated threshold: {traffic_threshold:.2f}s (from gap distribution analysis)")
        
        all_laps['InTraffic'] = all_laps['IntervalToAhead'] < traffic_threshold
        all_laps['UnderPressure'] = all_laps['IntervalToBehind'] < UNDER_PRESSURE_THRESHOLD_SECONDS

        # 3. Quadratic Clear-Air Benchmarking
        # ONLY use Green Flag, Non-Pit, Clear Air laps for the benchmark
        benchmark_laps = all_laps[ (~all_laps['IsPit']) & (~all_laps['IsSC']) & (~all_laps['InTraffic']) ].copy()
        benchmark_laps['LapTimeSeconds'] = benchmark_laps['LapTime'].dt.total_seconds()
        
        stint_compound_groups = all_laps[['Stint', 'Compound']].drop_duplicates()
        trend_models = {}
        
        for _, row in stint_compound_groups.iterrows():
            stint = row['Stint']
            compound = row['Compound']
            group_laps = benchmark_laps[(benchmark_laps['Stint'] == stint) & (benchmark_laps['Compound'] == compound)]
            
            if len(group_laps) < MIN_BENCHMARK_LAPS:
                trend_models[(stint, compound)] = ('median', group_laps['LapTimeSeconds'].median() if not group_laps.empty else 90.0)
                continue

            x = group_laps['LapNumber']
            y = group_laps['LapTimeSeconds']
            coeffs = np.polyfit(x, y, QUADRATIC_REGRESSION_DEGREE)
            trend_models[(stint, compound)] = ('quadratic', coeffs)

        # 4. Expected Pace Application
        def get_expected_pace(row):
            model = trend_models.get((row['Stint'], row['Compound']))
            if model:
                if model[0] == 'quadratic':
                    a, b, c = model[1]
                    return a * (row['LapNumber']**2) + b * row['LapNumber'] + c
                else:
                    return model[1]
            return np.nan

        all_laps['LapTimeSeconds'] = all_laps['LapTime'].dt.total_seconds()
        all_laps['ExpectedPace'] = all_laps.apply(get_expected_pace, axis=1)
        all_laps['RawDelta'] = all_laps['LapTimeSeconds'] - all_laps['ExpectedPace']
        
        # 5. Pit Analysis
        pit_laps = all_laps[all_laps['IsPit'] & (~all_laps['IsSC'])]
        avg_pit_loss = pit_laps['RawDelta'].median() if not pit_laps.empty else 20.0
        
        # 6. Equity Change
        def calculate_equity_change(row):
            if row['IsSC']: return 0.0
            base_equity = 0.0
            if row['IsPit']:
                loss = row['RawDelta'] - avg_pit_loss
                base_equity = -loss
            elif not pd.isna(row['RawDelta']):
                base_equity = -row['RawDelta']
            return base_equity

        all_laps['EquityChange'] = all_laps.apply(calculate_equity_change, axis=1)
        
        # 7. Refined Failure Attribution with Priority
        conditions = [
            (all_laps['IsPit']) & (all_laps['EquityChange'] < -INCIDENT_THRESHOLD_OPERATIONAL),
            (~all_laps['IsPit']) & (all_laps['EquityChange'] < -INCIDENT_THRESHOLD_MAJOR),
            (all_laps['InTraffic']) & (all_laps['EquityChange'] < -INCIDENT_THRESHOLD_TRAFFIC)
        ]
        choices = [
            'Operational',
            'Major Incident',
            'Traffic'
        ]
        all_laps['FailureType'] = np.select(conditions, choices, default='None')

        # 8. Aggregation per Driver
        equity_curves = []
        for driver in session.drivers:
            d_laps = all_laps[all_laps['DriverNumber'] == driver].sort_values('LapNumber')
            if d_laps.empty: continue
            
            d_laps['ExecutionEquity'] = d_laps['EquityChange'].cumsum()
            d_laps['Driver'] = session.get_driver(driver)['Abbreviation']
            
            # Restart Analysis
            d_laps['WasSC'] = d_laps['IsSC'].shift(1, fill_value=False)
            d_laps['RestartLap'] = (d_laps['WasSC']) & (~d_laps['IsSC'])
            
            equity_curves.append(d_laps[['Driver', 'LapNumber', 'EquityChange', 'ExecutionEquity', 
                                         'FailureType', 'InTraffic', 'UnderPressure', 'IsSC', 'RestartLap']])
            
        return pd.concat(equity_curves)

    except Exception as e:
        print(f"Error calculating equity: {e}")
        import traceback
        traceback.print_exc()
        return None

if __name__ == '__main__':
    df = calculate_execution_equity(2025, 'Australian Grand Prix')
    if df is not None:
        curr_dir = os.path.dirname(__file__)
        df.to_csv(os.path.join(curr_dir, 'test_equity.csv'), index=False)
        print("Success! Equity data with attribution saved.")