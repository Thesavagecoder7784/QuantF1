import fastf1
import pandas as pd
import numpy as np
import warnings
import matplotlib.pyplot as plt
import fastf1.plotting
import os

# Suppress pandas warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

# Hardcoded team colors for common F1 teams (2023 season as example)
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6',
    'Mercedes': '#27F4D2',
    'Ferrari': '#E80020',
    'McLaren': '#FF8000',
    'Aston Martin': '#229971',
    'Alpine': '#0093CC',
    'Williams': '#64C4FF',
    'AlphaTauri': '#5E8CA8', # Renamed to RB for 2024, but using 2023 name for consistency with example data
    'Haas F1 Team': '#B6BABD',
    'Alfa Romeo': '#C92D4B', # Renamed to Kick Sauber for 2024, but using 2023 name for consistency with example data
    'RB': '#5E8CA8', # For 2024 AlphaTauri
    'Kick Sauber': '#52e252', # For 2024 Alfa Romeo
    # Add more teams if necessary, or a default color
    'N/A': '#808080' # Default color for unknown teams
}


def calculate_driver_sortino_ratio(year: int, race_name: str):
    """
    Calculates a stint-adjusted and fuel-adjusted "Driver Sortino Ratio".

    This implementation benchmarks each driver against a dynamic, regression-based
    trendline calculated for each specific stint and tire compound combination.
    This provides a robust, comparable metric that isolates driver performance
    by accounting for both tire strategy and fuel load effects. The Sortino Ratio
    specifically penalizes for downside volatility (slower laps).

    Args:
        year (int): The year of the F1 season.
        race_name (str): The name of the race (e.g., 'Italian Grand Prix').
    
    Returns:
        pd.DataFrame: A DataFrame containing the fuel- and stint-adjusted 
                      Sortino Ratio analysis, or None if an error occurs.
    """
    print(f"Calculating Fuel- and Stint-Adjusted Driver Sortino Ratio for {year} {race_name}\n")

    try:
        fastf1.Cache.enable_cache('cache')
        session = fastf1.get_session(year, race_name, 'R')
        session.load(laps=True, telemetry=False, weather=False, messages=True)

        results = session.results
        all_laps = session.laps.pick_quicklaps()

        # Robustly filter out any laps affected by SC, VSC, or Yellow Flags.
        if 'TrackStatus' in all_laps.columns:
            laps = all_laps[all_laps['TrackStatus'] == '1'].copy()
        else:
            laps = all_laps.copy()

        if laps.empty:
            print("No valid green-flag laps found for analysis.")
            return None

        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

        # --- Fuel-Adjusted Stint-Compound Benchmark Calculation ---
        
        stint_compound_groups = laps[['Stint', 'Compound']].drop_duplicates()
        trend_models = {}
        
        for _, row in stint_compound_groups.iterrows():
            stint = row['Stint']
            compound = row['Compound']
            
            group_laps = laps[(laps['Stint'] == stint) & (laps['Compound'] == compound)]
            
            if len(group_laps) < 5:
                trend_models[(stint, compound)] = ('median', group_laps['LapTimeSeconds'].median())
                continue

            x = group_laps['LapNumber']
            y = group_laps['LapTimeSeconds']
            
            slope, intercept = np.polyfit(x, y, 1)
            trend_models[(stint, compound)] = ('regression', (slope, intercept))

        def calculate_benchmark(row):
            model_type, model_params = trend_models.get((row['Stint'], row['Compound']), (None, None))
            
            if model_type == 'median':
                return model_params
            elif model_type == 'regression':
                slope, intercept = model_params
                return slope * row['LapNumber'] + intercept
            else:
                return np.nan

        laps['BenchmarkTime'] = laps.apply(calculate_benchmark, axis=1)
        laps['LapTimeDelta'] = laps['LapTimeSeconds'] - laps['BenchmarkTime']
        
        laps.dropna(subset=['LapTimeDelta'], inplace=True)

        driver_analysis = []
        drivers = session.drivers
        for driver_number in drivers:
            driver_laps = laps[laps['DriverNumber'] == driver_number]
            if driver_laps.empty:
                continue

            stint_sortino_ratios = []
            stint_weights = []
            stint_mean_deltas = []
            stint_downside_devs = []

            for stint_number in driver_laps['Stint'].unique():
                stint_laps = driver_laps[driver_laps['Stint'] == stint_number]
                if len(stint_laps) < 3:
                    continue

                mean_delta = stint_laps['LapTimeDelta'].mean()
                
                # Sortino Ratio: Penalizes only downside risk (laps slower than mean)
                downside_deltas = stint_laps['LapTimeDelta'][stint_laps['LapTimeDelta'] > mean_delta]
                downside_std_dev = 0
                if not downside_deltas.empty:
                    downside_std_dev = downside_deltas.std()
                    if downside_std_dev > 1e-6:
                        sortino_ratio = -mean_delta / downside_std_dev
                    else:
                        sortino_ratio = 0
                else:
                    sortino_ratio = 0

                stint_sortino_ratios.append(sortino_ratio)
                stint_weights.append(len(stint_laps))
                stint_mean_deltas.append(mean_delta)
                stint_downside_devs.append(downside_std_dev)

            if not stint_sortino_ratios:
                continue

            total_laps = np.sum(stint_weights)
            weighted_sortino = np.average(stint_sortino_ratios, weights=stint_weights)
            weighted_mean_delta = np.average(stint_mean_deltas, weights=stint_weights)
            weighted_downside_dev = np.average(stint_downside_devs, weights=stint_weights)

            driver_info = session.get_driver(driver_number)
            driver_results = results[results['DriverNumber'] == driver_number]
            team_name = driver_results.iloc[0]['TeamName'] if not driver_results.empty else "N/A"
            position = driver_results.iloc[0]['Position'] if not driver_results.empty else "N/A"

            driver_analysis.append({
                'Driver': driver_info['Abbreviation'],
                'Team': team_name,
                'Position': position,
                'Mean Delta vs Benchmark (s)': weighted_mean_delta,
                'Downside Deviation (s)': weighted_downside_dev,
                'Driver Sortino Ratio': weighted_sortino,
                'Laps Count': total_laps
            })

        if not driver_analysis:
            print("No data available for the selected race.")
            return None

        analysis_df = pd.DataFrame(driver_analysis)
        analysis_df = analysis_df.sort_values(by='Driver Sortino Ratio', ascending=False).reset_index(drop=True)

        return analysis_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def plot_sortino_ratio_bar_chart(df: pd.DataFrame, year: int, race_name: str):
    plt.figure(figsize=(12, 7))
    colors = [TEAM_COLORS.get(team, '#808080') for team in df['Team']]
    
    plt.bar(df['Driver'], df['Driver Sortino Ratio'], color=colors)
    plt.xlabel('Driver')
    plt.ylabel('Driver Sortino Ratio')
    plt.title(f'Driver Sortino Ratio - {year} {race_name}', fontsize=16)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plot_dir = 'QuantF1/plots'
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(os.path.join(plot_dir, f'{year}_{race_name.replace(" ", "_")}_Sortino_Ratio_Bar_Chart.png'))

def plot_pace_consistency_scatter(df: pd.DataFrame, year: int, race_name: str):
    plt.figure(figsize=(12, 8))
    colors = [TEAM_COLORS.get(team, '#808080') for team in df['Team']]
    
    min_size = 50
    scale_factor = 200
    sizes = min_size + abs(df['Driver Sortino Ratio']) * scale_factor

    plt.scatter(df['Downside Deviation (s)'], df['Mean Delta vs Benchmark (s)'], 
                c=colors, s=sizes, alpha=0.7, edgecolors='w', linewidth=0.5)
    
    for i, row in df.iterrows():
        plt.annotate(row['Driver'], (row['Downside Deviation (s)'], row['Mean Delta vs Benchmark (s)']),
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)

    plt.xlabel('Downside Deviation (s) - (Inconsistency on Slow Laps)')
    plt.ylabel('Mean Delta vs Benchmark (s) - (Pace)')
    plt.title(f'Pace vs. Downside Consistency - {year} {race_name}', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plot_dir = 'QuantF1/plots'
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(os.path.join(plot_dir, f'{year}_{race_name.replace(" ", "_")}_Pace_Downside_Consistency_Scatter.png'))

def main():
    """
    Main function to run the analysis.
    """
    year = 2025
    race_name = 'Hungarian Grand Prix'
    
    sortino_df = calculate_driver_sortino_ratio(year, race_name)

    if sortino_df is not None:
        print("--- Fuel- and Stint-Adjusted Driver Sortino Ratio Analysis ---")
        print_df = sortino_df.rename(columns={'Mean Delta vs Benchmark (s)': 'Mean Delta (s)'})
        print(print_df.to_string(index=False))

        results_dir = 'QuantF1/results'
        os.makedirs(results_dir, exist_ok=True)
        csv_filename = os.path.join(results_dir, f'{year}_{race_name.replace(" ", "_")}_Driver_Sortino_Ratios.csv')
        sortino_df.to_csv(csv_filename, index=False)
        print(f"\nResults saved to {csv_filename}")

        plot_sortino_ratio_bar_chart(sortino_df, year, race_name)
        plot_pace_consistency_scatter(sortino_df, year, race_name)

        print("\n--- Interpretation ---")
        print("This 'Driver Sortino Ratio' evaluates risk-adjusted pace, focusing only on downside risk (slower laps).")
        print("It compares driver performance to a dynamic, fuel-adjusted benchmark for their specific stint and tire compound.")
        print("\nKey Components:")
        print(" - Pace (Return): Measured by the driver's 'Mean Delta' to the stint's expected pace trendline. A negative delta means the driver was consistently faster than expected.")
        print(" - Downside Inconsistency (Risk): Measured by the 'Downside Deviation', the standard deviation of only the laps that were slower than the driver's own mean delta for that stint.")
        print(" - Sortino Ratio Formula: Calculated as (-Mean_Delta / Downside_Deviation). It rewards drivers who are both faster than the benchmark and highly consistent on their slower laps.")
        print("\nHow to Read the Results:")
        print(" - High Positive Sortino Ratio: The ideal result. Indicates the driver was significantly faster than their expected pace and managed their slower laps with high consistency (i.e., no major mistakes).")
        print(" - Sortino Ratio Near Zero: Indicates the driver performed close to the expected pace or had high downside inconsistency.")
        print(" - Negative Sortino Ratio: Indicates the driver was slower than the expected pace.")

if __name__ == '__main__':
    main()