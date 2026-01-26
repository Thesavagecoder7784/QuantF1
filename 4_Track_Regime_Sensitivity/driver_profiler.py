import pandas as pd
import os

class DriverProfiler:
    """
    Classifies drivers into context profiles based on their performance 
    in different track regimes.
    """
    def __init__(self, year: int):
        self.year = year
        
        results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'results'))
        
        self.conditional_metrics_path = os.path.join(results_path, f'{self.year}_conditional_metrics.csv')
        self.sensitivity_analysis_path = os.path.join(results_path, f'{self.year}_sensitivity_analysis.csv')
        
        self.conditional_metrics = None
        self.sensitivity_analysis = None
        
        self.load_data()

    def load_data(self):
        """Loads the required analysis files."""
        try:
            self.conditional_metrics = pd.read_csv(self.conditional_metrics_path)
            self.sensitivity_analysis = pd.read_csv(self.sensitivity_analysis_path)
        except FileNotFoundError as e:
            print(f"Error loading data: {e}")
            print("Please run conditional_analysis.py first to generate the required files.")
            raise

    def profile_drivers(self, metric: str = 'Driver Sharpe Ratio', output_suffix: str = 'driver_profiles') -> pd.DataFrame:
        """
        Assigns a context profile to each driver based on their regime performance
        using K-Means clustering.
        
        Args:
            metric (str): The column name in conditional_metrics to use for clustering.
            output_suffix (str): Suffix for the output CSV file.
            
        Returns:
            pd.DataFrame: A DataFrame with drivers and their assigned profiles.
        """
        if self.conditional_metrics is None or self.sensitivity_analysis is None:
            print("Data not loaded. Cannot profile drivers.")
            return None
            
        # --- Feature Engineering ---
        # We need to pivot the conditional metrics to get a wide format: 
        # One row per driver, columns for performance in each regime.
        
        # 1. Expand Conditional Metrics
        feature_dfs = []
        
        # Degradation Features
        deg_pivot = self.conditional_metrics.groupby(['Driver', 'Degradation'])[metric].mean().unstack()
        deg_pivot.columns = [f'Degradation_{c}' for c in deg_pivot.columns]
        feature_dfs.append(deg_pivot)
        
        # Volatility Features
        vol_pivot = self.conditional_metrics.groupby(['Driver', 'Volatility'])[metric].mean().unstack()
        vol_pivot.columns = [f'Volatility_{c}' for c in vol_pivot.columns]
        feature_dfs.append(vol_pivot)
        
        # Sensitivity Features
        sens_pivot = self.conditional_metrics.groupby(['Driver', 'Power vs Downforce Sensitivity'])[metric].mean().unstack()
        sens_pivot.columns = [f'Sensitivity_{c}' for c in sens_pivot.columns]
        feature_dfs.append(sens_pivot)
        
        # Combine Features
        features = pd.concat(feature_dfs, axis=1)
        
        # Add Stability Metrics (Currently these are based on raw Sharpe, but might still be relevant context)
        sensis = self.sensitivity_analysis.set_index('Driver')
        features = features.join(sensis[['Regime Stability', 'Regime Spread']])
        
        # Fill missing values
        features = features.apply(lambda x: x.fillna(x.mean()), axis=1)
        features = features.fillna(0)
        
        # Determine mode for labeling context
        mode = 'relative' if 'Delta' in metric else 'absolute'
        
        profile_labels = self._cluster_drivers(features, mode=mode)
        
        result_df = pd.DataFrame({
            'Driver': features.index,
            'Profile': profile_labels
        }).reset_index(drop=True)
        
        # Save internally or return
        output_dir = os.path.join(os.path.dirname(__file__), 'results')
        os.makedirs(output_dir, exist_ok=True)
        result_df.to_csv(os.path.join(output_dir, f'{self.year}_{output_suffix}.csv'), index=False)
        print(f"Profiles based on {metric} saved to 'results/{self.year}_{output_suffix}.csv'")
        
        return result_df

    def profile_drivers_skill_isolated(self) -> pd.DataFrame:
        """
        Profiles drivers based on Teammate Delta Sharpe Ratio to isolate driver skill.
        """
        print("\n--- Running Skill Isolation Profiling ---")
        return self.profile_drivers(metric='Teammate Delta Sharpe Ratio', output_suffix='driver_skill_profiles')

    def _cluster_drivers(self, features: pd.DataFrame, mode: str = 'absolute') -> list:
        """
        Applies K-Means clustering to driver features and generates descriptive labels.
        Args:
            features: DataFrame of features
            mode: 'absolute' (Performance) or 'relative' (Skill/Delta)
        """
        from sklearn.preprocessing import StandardScaler
        from sklearn.cluster import KMeans
        import numpy as np

        # Normalize features
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        # Clustering
        n_clusters = 5
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_ids = kmeans.fit_predict(scaled_features)
        
        # Generate Descriptive Labels
        centers = kmeans.cluster_centers_
        feature_names = features.columns
        
        cluster_labels_map = {}
        
        for i in range(n_clusters):
            center = centers[i]
            # Get indices of top 2 features
            top_indices = center.argsort()[-2:][::-1]
            top_features = [feature_names[j] for j in top_indices]
            
            # Label definitions based on context
            if mode == 'absolute':
                # Absolute Performance Context (Car + Driver)
                if np.mean(center) > 0.5:
                    label = "Front Runner"    # Fast Car/Driver
                elif np.mean(center) < -0.5:
                    label = "Backmarker"      # Slow Car/Driver
                elif np.std(center) < 0.5:
                    label = "Midfield Runner" # Average
                elif 'Regime Stability' in top_features:
                    label = "High Variance"
                else:
                    # Specific specialist fallback
                    clean_names = [f.split('_')[-1] for f in top_features]
                    label = f"{clean_names[0]} Specialist"
                    
            else:
                # Relative Skill Context (Driver vs Teammate)
                if np.mean(center) > 0.5:
                    label = "Team Leader"     # Beats Teammate (Alpha +)
                elif np.mean(center) < -0.5:
                    label = "Team Trailer"    # Loses to Teammate (Alpha -)
                elif np.std(center) < 0.5:
                    label = "Team Matcher"    # Matches Teammate (Alpha 0)
                elif 'Regime Stability' in top_features:
                    label = "Inconsistent"    # High delta variance
                else:
                    # Specific specialist fallback
                    clean_names = [f.split('_')[-1] for f in top_features]
                    label = f"{clean_names[0]} Specialist"

            cluster_labels_map[i] = label
            
        full_labels = [cluster_labels_map[c_id] for c_id in cluster_ids]
        return full_labels

if __name__ == '__main__':
    try:
        profiler = DriverProfiler(2025)
        
        print(f"--- Driver Performance Profiles for {profiler.year} ---")
        perf_profiles = profiler.profile_drivers()
        print(perf_profiles)
        
        print(f"\n--- Driver Skill Profiles (Teammate Delta) for 2024 ---")
        skill_profiles = profiler.profile_drivers_skill_isolated()
        print(skill_profiles)

    except FileNotFoundError:
        pass
