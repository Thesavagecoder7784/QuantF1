import fastf1
import pandas as pd
import numpy as np
import warnings
import matplotlib.pyplot as plt
import os
from scipy.stats import linregress

# Suppress warnings for cleaner output
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

# Reusing the team color mapping for consistent visualizations
TEAM_COLORS = {
    'Red Bull Racing': '#3671C6', 'Mercedes': '#27F4D2', 'Ferrari': '#E80020',
    'McLaren': '#FF8000', 'Aston Martin': '#229971', 'Alpine': '#0093CC',
    'Williams': '#64C4FF', 'AlphaTauri': '#5E8CA8', 'Haas F1 Team': '#B6BABD',
    'Alfa Romeo': '#C92D4B', 'RB': '#5E8CA8', 'Kick Sauber': '#52e252',
    'N/A': '#808080'
}

def calculate_adaptability_index(year: int, race_name: str, num_segments: int = 3):
    """
    Calculates the Driver Adaptability Index based on the stability and evolution of lap times.

    This analysis captures a driver's execution style by measuring two key dimensions:
    1.  **Adaptability (Stability):** How consistent are their lap times relative to a dynamic
        benchmark? This is measured by the standard deviation of their lap time deltas.
        A lower standard deviation results in a higher (better) Adaptability Index.
    2.  **Pace Evolution:** How does their average pace change over the course of the race?
        This is measured by the slope of their average pace across race segments.

    Args:
        year (int): The year of the F1 season.
        race_name (str): The name of the race (e.g., 'Hungarian Grand Prix').
        num_segments (int): The number of segments to split the race into for evolution analysis.

    Returns:
        pd.DataFrame: A DataFrame with adaptability metrics for each driver, or None if an error occurs.
    """
    print(f"Calculating Driver Adaptability for {year} {race_name}\n")

    try:
        fastf1.Cache.enable_cache('/Users/prabhatm/Documents/GitHub/Formula1/QuantF1/cache')
        session = fastf1.get_session(year, race_name, 'R')
        session.load(laps=True, telemetry=False, weather=False, messages=False)

        results = session.results
        all_laps = session.laps.pick_quicklaps()
        if 'TrackStatus' in all_laps.columns:
            laps = all_laps[all_laps['TrackStatus'] == '1'].copy()
        else:
            laps = all_laps.copy()

        if laps.empty:
            print("No valid green-flag laps found for analysis.")
            return None

        laps['LapTimeSeconds'] = laps['LapTime'].dt.total_seconds()

        # --- Fuel-Adjusted Stint-Compound Benchmark Calculation (Consistent with Sharpe/Sortino) ---
        stint_compound_groups = laps[['Stint', 'Compound']].drop_duplicates()
        trend_models = {}
        for _, row in stint_compound_groups.iterrows():
            stint, compound = row['Stint'], row['Compound']
            group_laps = laps[(laps['Stint'] == stint) & (laps['Compound'] == compound)]
            
            if len(group_laps) < 5:
                trend_models[(stint, compound)] = ('median', group_laps['LapTimeSeconds'].median())
                continue

            x, y = group_laps['LapNumber'], group_laps['LapTimeSeconds']
            slope, intercept = np.polyfit(x, y, 1)
            trend_models[(stint, compound)] = ('regression', (slope, intercept))

        def calculate_benchmark(row):
            model_type, params = trend_models.get((row['Stint'], row['Compound']), (None, None))
            if model_type == 'median': return params
            if model_type == 'regression': return params[0] * row['LapNumber'] + params[1]
            return np.nan

        laps['BenchmarkTime'] = laps.apply(calculate_benchmark, axis=1)
        laps['LapTimeDelta'] = laps['LapTimeSeconds'] - laps['BenchmarkTime']
        laps.dropna(subset=['LapTimeDelta'], inplace=True)

        driver_analysis = []
        driver_numbers = session.drivers
        
        for driver_number in driver_numbers:
            driver_laps = laps[laps['DriverNumber'] == driver_number].sort_values(by='LapNumber')
            if len(driver_laps) < num_segments * 2:  # Ensure enough laps for meaningful segmentation
                continue

            # --- 1. Overall Stability (Adaptability Index) ---
            # The core metric: negative standard deviation of lap time deltas.
            # Lower variability -> higher adaptability (less negative index).
            overall_std_dev = driver_laps['LapTimeDelta'].std()
            adaptability_index = -overall_std_dev

            # --- 2. Temporal Evolution Analysis ---
            lap_segments = np.array_split(driver_laps, num_segments)
            segment_metrics = []
            for i, segment in enumerate(lap_segments):
                if not segment.empty:
                    segment_metrics.append({
                        'segment': i + 1,
                        'mean_delta': segment['LapTimeDelta'].mean(),
                        'std_delta': segment['LapTimeDelta'].std()
                    })
            
            if len(segment_metrics) < 2:
                continue

            segment_df = pd.DataFrame(segment_metrics)
            
            # --- Pace Evolution (Trend of mean lap time delta) ---
            # A negative slope is good (deltas are decreasing, so pace is improving vs benchmark)
            pace_slope, _, _, _, _ = linregress(segment_df['segment'], segment_df['mean_delta'])
            
            # --- Consistency Evolution (Trend of lap time stability) ---
            consistency_slope, _, _, _, _ = linregress(segment_df['segment'], segment_df['std_delta'].fillna(0))

            driver_info = session.get_driver(driver_number)
            driver_result = results[results['DriverNumber'] == driver_number]
            team_name = driver_result.iloc[0]['TeamName'] if not driver_result.empty else "N/A"
            
            driver_analysis.append({
                'Driver': driver_info['Abbreviation'],
                'Team': team_name,
                'AdaptabilityIndex': adaptability_index,
                'PaceEvolution': pace_slope,
                'ConsistencyEvolution': consistency_slope,
                'AnalyzedLaps': len(driver_laps)
            })

        if not driver_analysis:
            print("Could not generate Adaptability analysis for any driver.")
            return None

        analysis_df = pd.DataFrame(driver_analysis)
        analysis_df = analysis_df.sort_values(by='AdaptabilityIndex', ascending=False).reset_index(drop=True)

        return analysis_df

    except Exception as e:
        print(f"An error occurred: {e}")
        return None

def plot_adaptability_summary(df: pd.DataFrame, year: int, race_name: str):
    """Plots and saves a scatter plot of Adaptability vs. Pace Evolution."""
    plt.style.use('dark_background')
    fig, ax = plt.subplots(figsize=(14, 10))
    
    # Define quadrant boundaries at the median
    x_mid = df['PaceEvolution'].median()
    y_mid = df['AdaptabilityIndex'].median()

    ax.axhline(y_mid, color='gray', linestyle='--', alpha=0.5)
    ax.axvline(x_mid, color='gray', linestyle='--', alpha=0.5)

    # Quadrant labels
    ax.text(ax.get_xlim()[1], y_mid, 'More Stable →', va='bottom', ha='right', fontsize=10, color='gray', alpha=0.8)
    ax.text(ax.get_xlim()[0], y_mid, '← More Turbulent', va='bottom', ha='left', fontsize=10, color='gray', alpha=0.8)
    ax.text(x_mid, ax.get_ylim()[1], 'Improving Pace →', va='top', ha='center', fontsize=10, color='gray', alpha=0.8)
    ax.text(x_mid, ax.get_ylim()[0], '← Fading Pace', va='bottom', ha='center', fontsize=10, color='gray', alpha=0.8)

    # Scatter plot
    for i, row in df.iterrows():
        ax.scatter(row['PaceEvolution'], row['AdaptabilityIndex'], 
                   color=TEAM_COLORS.get(row['Team'], '#808080'), 
                   s=150, alpha=0.9, edgecolors='white', linewidth=0.5)
        ax.text(row['PaceEvolution'] + 0.005, row['AdaptabilityIndex'], ' ' + row['Driver'], 
                va='center', ha='left', fontsize=9, color='white')

    ax.set_title(f'Driver Execution Style - {year} {race_name}', fontsize=18, pad=20)
    ax.set_xlabel('Pace Evolution (Lower is Better)', fontsize=12)
    ax.set_ylabel('Adaptability Index (Higher is More Stable)', fontsize=12)
    
    # Invert X-axis so that improving pace (more negative slope) is to the right
    ax.invert_xaxis()
    
    ax.grid(False)
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    
    plt.tight_layout()

    plot_dir = f'QuantF1/3_Adaptibility_Index/plots'
    os.makedirs(plot_dir, exist_ok=True)
    plot_path = os.path.join(plot_dir, f'{year}_{race_name.replace(" ", "_")}_Adaptability_Summary.png')
    plt.savefig(plot_path, dpi=300)
    print(f"Adaptability summary plot saved to {plot_path}")

def main():
    """Main function to run the analysis and save results."""
    year = 2025
    race_name = 'Hungarian Grand Prix'
    
    adaptability_df = calculate_adaptability_index(year, race_name)

    if adaptability_df is not None:
        print("\n--- Driver Adaptability Analysis ---")
        # Make evolution columns more readable for printing
        print_df = adaptability_df.copy()
        print_df['PaceEvolution'] = print_df['PaceEvolution'].map('{:.4f}'.format)
        print_df['ConsistencyEvolution'] = print_df['ConsistencyEvolution'].map('{:.4f}'.format)
        print(print_df.to_string(index=False))

        results_dir = f'QuantF1/3_Adaptibility_Index/results'
        os.makedirs(results_dir, exist_ok=True)
        csv_path = os.path.join(results_dir, f'{year}_{race_name.replace(" ", "_")}_Driver_Adaptability.csv')
        adaptability_df.to_csv(csv_path, index=False)
        print(f"\nResults saved to {csv_path}")

        plot_adaptability_summary(adaptability_df, year, race_name)

        print("\n--- Interpretation ---")
        print("This analysis adds a temporal dimension to performance, classifying execution style rather than skill.")
        print("It answers: As race conditions evolve, does a driver’s efficiency remain stable or swing violently?")
        
        print("\n--- How to Read the Metrics ---")
        print(" - Adaptability Index: Measures overall lap time stability (smooth vs. turbulent). Higher (closer to 0) is more stable.")
        print(" - Pace Evolution: Measures the trend of pace throughout the race. A negative slope means pace is improving relative to the benchmark (getting faster).")

        print("\n--- How to Read the Plot ---")
        print("The plot classifies drivers into four execution styles (X-axis is inverted: right is better):")
        print(" - Top-Right (Smooth Improver): Stable and getting faster. The ideal quadrant.")
        print(" - Top-Left (Smooth Fader): Stable but losing pace. Might indicate a conservative strategy or tire management.")
        print(" - Bottom-Right (Turbulent Improver): Erratic but getting faster. An aggressive, 'on the edge' style.")
        print(" - Bottom-Left (Turbulent Fader): Erratic and losing pace. The most challenging quadrant, often indicating struggles.")

if __name__ == '__main__':
    main()