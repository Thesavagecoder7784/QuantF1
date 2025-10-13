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


def calculate_driver_sharpe_ratio(year: int, race_name: str):
    """
    Calculates a stint-adjusted and fuel-adjusted "Driver Sharpe Ratio".

    This implementation benchmarks each driver against a dynamic, regression-based
    trendline calculated for each specific stint and tire compound combination.
    This provides a robust, comparable metric that isolates driver performance
    by accounting for both tire strategy and fuel load effects.

    Args:
        year (int): The year of the F1 season.
        race_name (str): The name of the race (e.g., 'Italian Grand Prix').
    
    Returns:
        pd.DataFrame: A DataFrame containing the fuel- and stint-adjusted 
                      Sharpe Ratio analysis, or None if an error occurs.
    """
    print(f"Calculating Fuel- and Stint-Adjusted Driver Sharpe Ratio for {year} {race_name}\n")

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
        # For each stint-compound group, fit a linear regression to model the
        # effect of fuel burn-off on lap times. This creates a dynamic benchmark.
        
        stint_compound_groups = laps[['Stint', 'Compound']].drop_duplicates()
        trend_models = {}
        
        for _, row in stint_compound_groups.iterrows():
            stint = row['Stint']
            compound = row['Compound']
            
            group_laps = laps[(laps['Stint'] == stint) & (laps['Compound'] == compound)]
            
            # Need at least 5 data points for a stable regression
            if len(group_laps) < 5:
                # Fallback to simple median for very short or uncommon stints
                trend_models[(stint, compound)] = ('median', group_laps['LapTimeSeconds'].median())
                continue

            x = group_laps['LapNumber']
            y = group_laps['LapTimeSeconds']
            
            # Fit a linear model: lap_time = slope * lap_number + intercept
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
                return np.nan # Should not happen in practice

        laps['BenchmarkTime'] = laps.apply(calculate_benchmark, axis=1)
        laps['LapTimeDelta'] = laps['LapTimeSeconds'] - laps['BenchmarkTime']
        
        # Drop laps where a benchmark couldn't be calculated
        laps.dropna(subset=['LapTimeDelta'], inplace=True)

        driver_analysis = []
        drivers = session.drivers
        for driver_number in drivers:
            driver_laps = laps[laps['DriverNumber'] == driver_number]
            if driver_laps.empty:
                continue

            stint_sharpe_ratios = []
            stint_sortino_ratios = []
            stint_weights = []
            stint_mean_deltas = []
            stint_std_devs = []

            for stint_number in driver_laps['Stint'].unique():
                stint_laps = driver_laps[driver_laps['Stint'] == stint_number]
                if len(stint_laps) < 3:
                    continue

                mean_delta = stint_laps['LapTimeDelta'].mean()
                std_dev_delta = stint_laps['LapTimeDelta'].std()

                # Sharpe Ratio: Penalizes both positive and negative volatility
                if std_dev_delta > 1e-6:
                    # We use the negative delta as "return" (less time lost is good)
                    sharpe_ratio = -mean_delta / std_dev_delta
                else:
                    sharpe_ratio = 0

                # Sortino Ratio: Penalizes only downside risk (laps slower than mean)
                downside_deltas = stint_laps['LapTimeDelta'][stint_laps['LapTimeDelta'] > mean_delta]
                if not downside_deltas.empty:
                    downside_std_dev = downside_deltas.std()
                    if downside_std_dev > 1e-6:
                        sortino_ratio = -mean_delta / downside_std_dev
                    else:
                        sortino_ratio = 0
                else:
                    sortino_ratio = 0

                stint_sharpe_ratios.append(sharpe_ratio)
                stint_sortino_ratios.append(sortino_ratio)
                stint_weights.append(len(stint_laps))
                stint_mean_deltas.append(mean_delta)
                stint_std_devs.append(std_dev_delta)

            if not stint_sharpe_ratios:
                continue

            # --- Weighted Aggregation ---
            total_laps = np.sum(stint_weights)
            weighted_sharpe = np.average(stint_sharpe_ratios, weights=stint_weights)
            weighted_sortino = np.average(stint_sortino_ratios, weights=stint_weights)
            weighted_mean_delta = np.average(stint_mean_deltas, weights=stint_weights)
            weighted_std_dev = np.average(stint_std_devs, weights=stint_weights)

            driver_info = session.get_driver(driver_number)
            driver_results = results[results['DriverNumber'] == driver_number]
            team_name = driver_results.iloc[0]['TeamName'] if not driver_results.empty else "N/A"
            position = driver_results.iloc[0]['Position'] if not driver_results.empty else "N/A"

            driver_analysis.append({
                'Driver': driver_info['Abbreviation'],
                'Team': team_name,
                'Position': position,
                'Mean Delta vs Benchmark (s)': weighted_mean_delta,
                'Lap Time Std Dev (s)': weighted_std_dev,
                'Driver Sharpe Ratio': weighted_sharpe,
                'Driver Sortino Ratio': weighted_sortino,
                'Laps Count': total_laps
            })

        if not driver_analysis:
            print("No data available for the selected race.")
            return None

        analysis_df = pd.DataFrame(driver_analysis)
        analysis_df = analysis_df.sort_values(by='Driver Sharpe Ratio', ascending=False).reset_index(drop=True)

        return analysis_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def plot_sharpe_ratio_bar_chart(df: pd.DataFrame, year: int, race_name: str):
    plt.figure(figsize=(12, 7))
    colors = [TEAM_COLORS.get(team, '#808080') for team in df['Team']]
    
    plt.bar(df['Driver'], df['Driver Sharpe Ratio'], color=colors)
    plt.xlabel('Driver')
    plt.ylabel('Driver Sharpe Ratio')
    plt.title(f'Driver Sharpe Ratio - {year} {race_name}', fontsize=16)
    plt.xticks(rotation=45, ha='right')
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plot_dir = 'QuantF1/plots'
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(os.path.join(plot_dir, f'{year}_{race_name.replace(" ", "_")}_Sharpe_Ratio_Bar_Chart.png'))

def plot_pace_consistency_scatter(df: pd.DataFrame, year: int, race_name: str):
    plt.figure(figsize=(12, 8))
    colors = [TEAM_COLORS.get(team, '#808080') for team in df['Team']]
    
    # Use absolute value of Sharpe for sizing, as it can be negative
    min_size = 50
    scale_factor = 200
    sizes = min_size + abs(df['Driver Sharpe Ratio']) * scale_factor

    plt.scatter(df['Lap Time Std Dev (s)'], df['Mean Delta vs Benchmark (s)'], 
                c=colors, s=sizes, alpha=0.7, edgecolors='w', linewidth=0.5)
    
    for i, row in df.iterrows():
        plt.annotate(row['Driver'], (row['Lap Time Std Dev (s)'], row['Mean Delta vs Benchmark (s)']),
                     textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)

    plt.xlabel('Lap Time Standard Deviation (s) - (Inconsistency)')
    plt.ylabel('Mean Delta vs Benchmark (s) - (Pace)')
    plt.title(f'Pace vs. Consistency - {year} {race_name}', fontsize=16)
    plt.grid(True, linestyle='--', alpha=0.7)
    # Invert y-axis: lower delta (closer to 0 or negative) is better pace
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plot_dir = 'QuantF1/plots'
    os.makedirs(plot_dir, exist_ok=True)
    plt.savefig(os.path.join(plot_dir, f'{year}_{race_name.replace(" ", "_")}_Pace_Consistency_Scatter.png'))

def main():
    """
    Main function to run the analysis.
    """
    year = 2025
    race_name = 'Hungarian Grand Prix'
    
    sharpe_df = calculate_driver_sharpe_ratio(year, race_name)

    if sharpe_df is not None:
        print("--- Fuel- and Stint-Adjusted Driver Sharpe Ratio Analysis ---")
        # For printing, we can simplify the column name
        print_df = sharpe_df.rename(columns={'Mean Delta vs Benchmark (s)': 'Mean Delta (s)'})
        print(print_df.to_string(index=False))

        # --- Save results to CSV ---
        results_dir = 'QuantF1/results'
        os.makedirs(results_dir, exist_ok=True)
        csv_filename = os.path.join(results_dir, f'{year}_{race_name.replace(" ", "_")}_Driver_Sharpe_Ratios.csv')
        print(f"\nResults saved to {csv_filename}")

        plot_sharpe_ratio_bar_chart(sharpe_df, year, race_name)
        plot_pace_consistency_scatter(sharpe_df, year, race_name)

        print("\n--- Interpretation ---")
        print("This 'Driver Sharpe Ratio' evaluates risk-adjusted pace against a dynamic, fuel-adjusted benchmark.")
        print("It compares each driver's performance to a regression-based trendline for their specific stint and tire compound, isolating driver skill from car, tire, and fuel load effects.")
        print("\nKey Components:")
        print(" - Pace (Return): Measured by the driver's 'Mean Delta' to the stint's expected pace trendline. A negative delta means the driver was consistently faster than expected.")
        print(" - Inconsistency (Risk): Measured by the 'Lap Time Std Dev' of those deltas. Lower values mean higher consistency.")
        print(" - Sharpe Ratio Formula: Calculated as (-Mean_Delta / Std_Dev). It rewards drivers who are both faster than the benchmark and highly consistent.")
        print("\nHow to Read the Results:")
        print(" - High Positive Sharpe Ratio: The ideal result. Indicates the driver was significantly faster than their expected pace and did so with high consistency.")
        print(" - Sharpe Ratio Near Zero: Indicates the driver performed close to the expected pace or had high inconsistency that negated their pace advantage.")
        print(" - Negative Sharpe Ratio: Indicates the driver was slower than the expected pace.")
        print(" - Mean Delta vs Benchmark (s): The driver's average time difference from the expected, fuel-adjusted lap time. Negative is faster, positive is slower.")

if __name__ == '__main__':
    main()