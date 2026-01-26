import pandas as pd
import sys
import os
import warnings
import importlib.util

# Suppress warnings for cleaner output
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

def import_from_path(module_name, file_path):
    """Dynamically imports a module from a given file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module

def run_conditional_analysis(year: int):
    """
    Performs a conditional analysis of driver performance based on track regimes.
    """
    # --- 1. Load Master Data ---
    # This assumes a master CSV file has been generated containing per-race, per-driver metrics.
    # For this example, we'll generate it on the fly.
    
    # Define absolute paths to the scripts we need
    base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    sharpe_script_path = os.path.join(base_path, '1_Sharpe_Ratio', 'driver_sharpe_ratio.py')
    
    # Import the necessary functions from these modules
    sharpe_module = import_from_path('driver_sharpe_ratio', sharpe_script_path)
    calculate_driver_sharpe_ratio = sharpe_module.calculate_driver_sharpe_ratio

    RACE_SCHEDULE = [
        'Bahrain Grand Prix', 'Saudi Arabian Grand Prix', 'Australian Grand Prix', 'Azerbaijan Grand Prix',
        'Miami Grand Prix', 'Monaco Grand Prix', 'Spanish Grand Prix', 'Canadian Grand Prix',
        'Austrian Grand Prix', 'British Grand Prix', 'Hungarian Grand Prix', 'Belgian Grand Prix',
        'Dutch Grand Prix', 'Italian Grand Prix', 'Singapore Grand Prix', 'Japanese Grand Prix',
        'Qatar Grand Prix', 'United States Grand Prix', 'Mexico City Grand Prix', 'Brazilian Grand Prix',
        'Las Vegas Grand Prix', 'Abu Dhabi Grand Prix'
    ]
    
    all_race_data = []
    for race_name in RACE_SCHEDULE:
        print(f"Processing {year} {race_name}...")
        driver_ratios = calculate_driver_sharpe_ratio(year, race_name)
        if driver_ratios is not None:
            driver_ratios['Race'] = race_name
            all_race_data.append(driver_ratios)
            
    if not all_race_data:
        print("No data to analyze.")
        return
        
    master_df = pd.concat(all_race_data, ignore_index=True)

    # --- 2. Load Regime Vectors from File ---
    regime_df = pd.read_csv(os.path.join('results', f'{year}_regime_vectors.csv'))
    
    # Merge regime information into the master dataframe
    master_df = pd.merge(master_df, regime_df, on='Race')

    # --- 2.5 Calculate Teammate Delta ---
    # Calculate average Sharpe Ratio per Team per Race
    team_race_means = master_df.groupby(['Race', 'Team'])['Driver Sharpe Ratio'].mean().reset_index()
    team_race_means = team_race_means.rename(columns={'Driver Sharpe Ratio': 'Team Mean Sharpe'})
    
    master_df = pd.merge(master_df, team_race_means, on=['Race', 'Team'])
    master_df['Teammate Delta Sharpe Ratio'] = master_df['Driver Sharpe Ratio'] - master_df['Team Mean Sharpe']

    # --- 3. Compute Conditional Metrics ---
    # We are interested in how Sharpe Ratio changes across different regimes
    
    conditional_metrics = master_df.groupby(['Driver', 'Degradation', 'Overtaking', 'Power vs Downforce Sensitivity', 'Volatility'])[['Driver Sharpe Ratio', 'Teammate Delta Sharpe Ratio']].mean().reset_index()
    
    # --- 4. Measure Sensitivity ---
    sensitivity_data = []
    
    for driver in conditional_metrics['Driver'].unique():
        driver_data = conditional_metrics[conditional_metrics['Driver'] == driver]
        
        # Regime Spread (using raw performance for now, could switch to delta)
        spread = driver_data['Driver Sharpe Ratio'].max() - driver_data['Driver Sharpe Ratio'].min()
        
        # Regime Stability (Variance)
        stability = driver_data['Driver Sharpe Ratio'].var()
        
        sensitivity_data.append({
            'Driver': driver,
            'Regime Spread': spread,
            'Regime Stability': stability
        })
        
    sensitivity_df = pd.DataFrame(sensitivity_data)
    
    # --- 5. Save Results ---
    output_dir = os.path.join(os.path.dirname(__file__), 'results')
    os.makedirs(output_dir, exist_ok=True)
    
    conditional_metrics.to_csv(os.path.join(output_dir, f'{year}_conditional_metrics.csv'), index=False)
    sensitivity_df.to_csv(os.path.join(output_dir, f'{year}_sensitivity_analysis.csv'), index=False)
    
    print("\n--- Conditional Analysis Complete ---")
    print("Conditional metrics and sensitivity analysis saved to 'results' directory.")

if __name__ == '__main__':
    run_conditional_analysis(2025)