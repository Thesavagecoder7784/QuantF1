import pandas as pd
import os
import sys

# Add parent directory to path to import from other modules if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from execution_equity import calculate_execution_equity
from drawdown_metrics import calculate_drawdown_metrics
from resilience_profiler import ResilienceProfiler
from visualize_drawdown import DrawdownVisualizer

def run_seasonal_drawdown(year: int):
    # Reduced list for speed in testing, or full schedule
    RACE_SCHEDULE = [
        'Australian Grand Prix', 'Chinese Grand Prix', 'Japanese Grand Prix', 
        'Bahrain Grand Prix', 'Saudi Arabian Grand Prix', 'Miami Grand Prix', 
        'Emilia Romagna Grand Prix', 'Monaco Grand Prix', 'Spanish Grand Prix', 
        'Canadian Grand Prix', 'Austrian Grand Prix', 'British Grand Prix', 
        'Belgian Grand Prix', 'Hungarian Grand Prix', 'Dutch Grand Prix', 
        'Italian Grand Prix', 'Azerbaijan Grand Prix', 'Singapore Grand Prix', 
        'United States Grand Prix', 'Mexico City Grand Prix', 'São Paulo Grand Prix', 
        'Las Vegas Grand Prix', 'Qatar Grand Prix', 'Abu Dhabi Grand Prix'
    ]
    
    all_metrics = []
    viz = DrawdownVisualizer(year)
    profiler = ResilienceProfiler(year)
    
    for race in RACE_SCHEDULE:
        try:
            print(f"\n--- Processing {race} ---")
            equity_df = calculate_execution_equity(year, race)
            if equity_df is not None:
                # 1. Calculate Metrics
                race_metrics = calculate_drawdown_metrics(equity_df)
                race_metrics['Race'] = race
                all_metrics.append(race_metrics)
                
                # 2. Visualize key drivers for this race
                viz.plot_race_equity(equity_df, race, target_drivers=['VER', 'NOR', 'PIA', 'LEC', 'RUS', 'HAM'])
        except Exception as e:
            print(f"Skipping {race} due to error: {e}")

    if not all_metrics:
        print("No data processed.")
        return

    # Aggregate Season Metrics
    master_metrics = pd.concat(all_metrics)
    
    # Calculate participation count
    participation = master_metrics.groupby('Driver')['Race'].count()
    full_season_drivers = participation[participation >= 10].index
    
    seasonal_summary = master_metrics[master_metrics['Driver'].isin(full_season_drivers)].groupby('Driver').agg({
        'Max Drawdown (s)': 'min',
        'Reset Velocity (s/Lap)': 'mean',
        'Restart Delta (s)': 'mean',
        'Major Incident Resilience': 'mean',
        'Traffic Resilience': 'mean',
        'Operational Resilience': 'mean',
        'Recovery Curvature': 'mean',
        'Recovery Shape': lambda x: x.mode()[0] if len(x.mode()) > 0 else 'Unknown'
    }).reset_index()
    
    # 3. Profile Drivers
    profiles = profiler.profile_drivers(seasonal_summary)
    print("\n--- Seasonal Resilience Profiles ---")
    print(profiles[['Driver', 'Resilience Profile']])
    
    # 4. Generate Seasonal Visuals
    viz.plot_resilience_scatter(profiles)
    
    # Generate specific Comparisons for the article
    try:
        print("\n--- Generating Recovery Battle: NOR vs PIA ---")
        aus_equity = calculate_execution_equity(year, 'Australian Grand Prix')
        if aus_equity is not None:
            viz.plot_recovery_comparison(aus_equity, 'NOR', 'PIA', 'Australian Grand Prix')
            
            print("\n--- Generating Recovery Battle: LEC vs HAM (Ferrari 2025) ---")
            viz.plot_recovery_comparison(aus_equity, 'LEC', 'HAM', 'Australian Grand Prix')
    except Exception as e:
        print(f"Failed to generate recovery battle plots: {e}")

if __name__ == '__main__':
    run_seasonal_drawdown(2025)
