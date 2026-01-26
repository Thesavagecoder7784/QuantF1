

import fastf1
import pandas as pd
import numpy as np
import warnings
import os

# Suppress warnings for cleaner output
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)

class RegimeClassifier:
    """
    Classifies a race track into a regime vector based on four axes:
    1. Degradation
    2. Overtaking Difficulty
    3. Power vs Downforce Sensitivity
    4. Race Volatility
    """
    FUEL_CORRECTION_FACTOR = 0.04  # Seconds per lap fuel effect

    def __init__(self, year: int, race_name: str):
        self.year = year
        self.race_name = race_name
        
        # Construct cache path relative to the script's location
        cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'cache'))
        fastf1.Cache.enable_cache(cache_path)
        
        self.session = fastf1.get_session(self.year, self.race_name, 'R')
        self.session.load(laps=True, weather=True, messages=True, telemetry=True) # Re-enable telemetry
        
        # Filter for quick laps under green flag conditions for performance metrics
        self.laps = self.session.laps.pick_quicklaps()
        if 'TrackStatus' in self.laps.columns:
            self.laps = self.laps[self.laps['TrackStatus'] == '1'].copy()
        
        if not self.laps.empty:
            self.laps['LapTimeSeconds'] = self.laps['LapTime'].dt.total_seconds()

    def _calculate_degradation_score(self) -> float:
        """Calculates fuel-corrected degradation score."""
        # Exclude SOFT compound as it's not representative for long-run degradation
        common_compound = self.laps[self.laps['Compound'] != 'SOFT']['Compound'].mode()
        if common_compound.empty:
            common_compound = self.laps['Compound'].mode() # Fallback if no non-soft laps
        if common_compound.empty:
            return 0.0
        
        target_compound = common_compound.iloc[0]
        stint_slopes = []
        stints = self.laps[(self.laps['Compound'] == target_compound) & (self.laps['Stint'] > 0)]
        
        for driver in stints['Driver'].unique():
            driver_stints = stints[stints['Driver'] == driver]
            for stint_num in driver_stints['Stint'].unique():
                stint_laps = driver_stints[driver_stints['Stint'] == stint_num].copy()
                if len(stint_laps) >= 5:
                    # Fuel correction
                    lap_num_in_stint = stint_laps['LapNumber'] - stint_laps['LapNumber'].min()
                    stint_laps['CorrectedLapTime'] = stint_laps['LapTimeSeconds'] + (lap_num_in_stint * self.FUEL_CORRECTION_FACTOR)
                    
                    x = stint_laps['LapNumber']
                    y = stint_laps['CorrectedLapTime']
                    
                    slope, _ = np.polyfit(x, y, 1)
                    
                    # Clip negative degradation to 0, as it's likely noise or track evolution
                    stint_slopes.append(max(0, slope))
                    
        return np.mean(stint_slopes) if stint_slopes else 0.0

    def _calculate_overtaking_score(self) -> int:
        """Counts the number of on-track overtakes, excluding pit stop effects."""
        laps = self.session.laps.copy()
        if laps.empty:
            return 0
            
        laps = laps.sort_values(by=['Driver', 'LapNumber'])
        
        # Get previous lap's position for each driver
        laps['PrevPosition'] = laps.groupby('Driver')['Position'].shift(1)
        
        # Identify laps where a driver was not in the pits
        laps['NotPitting'] = laps['PitInTime'].isna() & laps['PitOutTime'].isna()
        
        # Identify lap numbers where at least one driver was pitting
        pitting_lap_numbers = laps[~laps['NotPitting']]['LapNumber'].unique()
        
        # An overtake is a position gain (lower number) vs the previous lap
        # Must happen on track (driver not pitting on this lap or previous)
        # Must happen on a lap where NO driver was pitting
        overtakes = laps[
            (laps['Position'] < laps['PrevPosition']) &
            (laps['NotPitting']) &
            (laps.groupby('Driver')['NotPitting'].shift(1) == True) &
            (laps['LapNumber'] > 1) &
            (~laps['LapNumber'].isin(pitting_lap_numbers)) # Exclude laps with any pit stops
        ]
        
        return len(overtakes)

    def _calculate_full_throttle_percentage(self) -> float | None:
        """Calculates the percentage of a lap spent at full throttle."""
        try:
            # Use a representative fast lap instead of all laps for efficiency
            lap = self.laps.pick_fastest()
            if lap is None: return None
            
            tel = lap.get_telemetry()
            if tel.empty: return None

            return (tel['Throttle'] > 95).sum() / len(tel)
        except Exception as e:
            print(f"Warning: Could not calculate full throttle percentage due to: {e}.")
            return None

    def _calculate_disruption_percentage(self) -> float:
        """Calculates disruption using the full session data."""
        all_laps = self.session.laps
        if all_laps.empty:
            return 0.0
            
        # TrackStatus '4' is Safety Car, '5' is VSC
        sc_laps = len(all_laps[all_laps['TrackStatus'] == '4']['LapNumber'].unique())
        vsc_laps = len(all_laps[all_laps['TrackStatus'] == '5']['LapNumber'].unique())
        
        # Red flags are message-based, not per lap
        red_flags = 0
        if hasattr(self.session, 'race_control_messages') and not self.session.race_control_messages.empty:
            red_flags = len(self.session.race_control_messages[self.session.race_control_messages['Category'] == 'RedFlag'])
        
        # Consider rain as a disruption factor
        weather = self.session.weather_data
        rainy_laps = 0
        if not weather.empty and 'Rainfall' in weather.columns and weather['Rainfall'].any():
            rainy_intervals = weather[weather['Rainfall'] == True]
            if not rainy_intervals.empty:
                rain_start_time = rainy_intervals['Time'].min()
                rain_end_time = rainy_intervals['Time'].max()
                rainy_laps = len(all_laps[
                    (all_laps['Time'] >= rain_start_time) &
                    (all_laps['Time'] <= rain_end_time)
                ]['LapNumber'].unique())

        # Each red flag is weighted as 5 laps of disruption
        total_disruption_laps = sc_laps + vsc_laps + rainy_laps + (red_flags * 5)
        
        return total_disruption_laps / all_laps['LapNumber'].max()

    def get_raw_metrics(self) -> dict:
        """Returns the raw calculated metrics for the track."""
        if self.laps.empty:
            print("No valid green-flag laps found.")
            return None
            
        degradation_score = self._calculate_degradation_score()
        overtaking_score = self._calculate_overtaking_score()
        full_throttle_percentage = self._calculate_full_throttle_percentage()
        disruption_percentage = self._calculate_disruption_percentage()

        return {
            'Race': self.race_name,
            'Degradation Score': degradation_score,
            'Overtaking Score': overtaking_score,
            'Full Throttle %': full_throttle_percentage,
            'Disruption %': disruption_percentage
        }

def apply_clustering_labels(df: pd.DataFrame) -> pd.DataFrame:
    """
    Applies K-Means clustering to raw metrics to generate dynamic, data-driven labels.
    """
    from sklearn.cluster import KMeans
    import numpy as np

    def cluster_1d(series, n_clusters, labels_sorted_by_center):
        """
        Clusters a 1D series and assigns labels based on the sorted cluster centers.
        """
        # Reshape for sklearn
        X = series.values.reshape(-1, 1)
        
        # Handle NaN
        if np.isnan(X).any():
            # Fill NaNs with mean for clustering, though ideally we shouldn't have them
            X = np.nan_to_num(X, nan=np.nanmean(X))

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels_idx = kmeans.fit_predict(X)
        
        # Determine order of clusters
        centers = kmeans.cluster_centers_.flatten()
        sorted_indices = np.argsort(centers)
        
        # Create a mapping from cluster_idx -> label
        # If labels_sorted_by_center is ['Low', 'Med', 'High'], 
        # and sorted_indices is [2, 0, 1] (meaning cluster 2 is lowest, 0 is med, 1 is highest)
        # then cluster 2 -> 'Low', cluster 0 -> 'Med', cluster 1 -> 'High'
        
        cluster_map = {original_idx: labels_sorted_by_center[rank] 
                       for rank, original_idx in enumerate(sorted_indices)}
        
        return [cluster_map[idx] for idx in labels_idx]

    # 1. Degradation (Low -> Very High)
    # We use 4 clusters to capture the nuance
    df['Degradation'] = cluster_1d(df['Degradation Score'], 4, 
                                   ['Low', 'Moderate', 'High', 'Very High'])

    # 2. Overtaking (Processional -> Overtake-Heavy)
    df['Overtaking'] = cluster_1d(df['Overtaking Score'], 3, 
                                  ['Processional', 'Raceable', 'Overtake-Heavy'])

    # 3. Volatility (Stable -> Chaotic)
    # 2 clusters often split clearly between normal races and crazy ones
    df['Volatility'] = cluster_1d(df['Disruption %'], 2, 
                                  ['Stable', 'Chaotic'])

    # 4. Power Sensitivity (Downforce -> Power)
    # Full Throttle %: Low = Downforce, High = Power
    df['Power vs Downforce Sensitivity'] = cluster_1d(df['Full Throttle %'].fillna(0.5), 3,
                                                      ['Downforce-Dominant', 'Balanced', 'Power-Dominant'])
                                                      
    return df

if __name__ == '__main__':
    year = 2025
    schedule = fastf1.get_event_schedule(year, include_testing=False)
    races = schedule['EventName']
    
    raw_data = []

    for race_name in races:
        print(f"--- Processing {year} {race_name} ---")
        try:
            classifier = RegimeClassifier(year, race_name)
            metrics = classifier.get_raw_metrics()
            
            if metrics:
                raw_data.append(metrics)
                print(metrics)
        except Exception as e:
            print(f"Could not process {race_name}: {e}")

    if raw_data:
        df = pd.DataFrame(raw_data)
        
        print("\n--- Applying Unsupervised Clustering for Regime Labels ---")
        df = apply_clustering_labels(df)
        
        # Reorder columns for readability
        cols = ['Race', 
                'Degradation', 'Degradation Score',
                'Overtaking', 'Overtaking Score',
                'Power vs Downforce Sensitivity', 'Full Throttle %',
                'Volatility', 'Disruption %']
                
        df = df[cols]
        print(df)

        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'{year}_regime_vectors.csv')
        df.to_csv(output_path, index=False)
        print(f"\nSaved all regime vectors to '{output_path}'")
