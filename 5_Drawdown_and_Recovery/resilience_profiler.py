import pandas as pd
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import os
import sys

# Import configuration
sys.path.insert(0, os.path.dirname(__file__))
from config import (
    MDD_BUFFER_SECONDS,
    PERCENTILE_THRESHOLDS,
    ABSOLUTE_THRESHOLDS,
    LOG_LEVEL
)

class ResilienceProfiler:
    def __init__(self, year: int):
        self.year = year
        self.results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'results'))
        os.makedirs(self.results_path, exist_ok=True)

    def profile_drivers(self, aggregated_metrics_df):
        """
        Classifies drivers into resilience archetypes based on Physics of Failure metrics.
        
        CURRENT: Percentile-based classification (NOTE: Not reproducible across seasons)
        RECOMMENDED: Switch to absolute thresholds (see config.ABSOLUTE_THRESHOLDS)
        
        Archetypes:
        - Entropy King: Shallow MDD + Fast Reset = Few mistakes, recovers instantly
        - Elastic Aggressor: Deep MDD + Fast Reset = Aggressive, but recovers quickly
        - Steady Operator: Shallow MDD + Slow Reset = Conservative, avoids errors
        - Brittle Performer: Deep MDD + Slow Reset = Struggling, slow recovery
        - Volatile Performer: Undefined = Residual category (should be eliminated)
        """
        if aggregated_metrics_df.empty:
            return None

        # Select features for classification
        # Fill NaN values with 0 (drivers with no incidents of a type)
        features = ['Max Drawdown (s)', 'Reset Velocity (s/Lap)', 'Restart Delta (s)', 
                    'Major Incident Resilience', 'Traffic Resilience']
        X = aggregated_metrics_df[features].fillna(0)
        
        # Scale for KMeans
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)
        
        # KMeans clustering (used for supplementary validation, not primary classification)
        kmeans = KMeans(n_clusters=8, random_state=42, n_init=10)
        aggregated_metrics_df['Cluster'] = kmeans.fit_predict(X_scaled)
        
        # =====================================================================
        # PRIMARY CLASSIFICATION: Percentile-Based Thresholds
        # WARNING: This approach is not reproducible across seasons
        # A driver classified as "Entropy King" in 2025 might be
        # "Elastic Aggressor" in 2024 if the field is different
        # =====================================================================
        
        mdd_q70 = aggregated_metrics_df['Max Drawdown (s)'].quantile(0.7)
        rv_q70 = aggregated_metrics_df['Reset Velocity (s/Lap)'].quantile(0.7)
        
        mdd_median = aggregated_metrics_df['Max Drawdown (s)'].median()
        rv_median = aggregated_metrics_df['Reset Velocity (s/Lap)'].median()
        
        if LOG_LEVEL == 'DEBUG':
            print(f"Classification Thresholds (Percentile-Based):")
            print(f"  MDD Q70: {mdd_q70:.2f}s (top 30% shallowest)")
            print(f"  RV Q70:  {rv_q70:.3f} s/lap (top 30% fastest)")
            print(f"  MDD Median: {mdd_median:.2f}s")
            print(f"  RV Median:  {rv_median:.3f} s/lap")
        
        def assign_archetype(row):
            """
            Assign archetype using decision tree logic.
            NOTE: Order matters! Check conditions in order.
            """
            # 1. Entropy King: Top 30% in both metrics + positive restart
            if (row['Max Drawdown (s)'] >= mdd_q70 and 
                row['Reset Velocity (s/Lap)'] >= rv_q70):
                if row['Restart Delta (s)'] >= 0.0:
                    return "Entropy King"
            
            # 2. Steady Operator: Shallow MDD (better than median - buffer)
            if row['Max Drawdown (s)'] >= (mdd_median - MDD_BUFFER_SECONDS):
                return "Steady Operator"
            
            # 3. Elastic Aggressor: Fast reset despite deep MDD
            if row['Reset Velocity (s/Lap)'] >= (rv_median + 0.05):
                return "Elastic Aggressor"
            
            # 4. Brittle Performer: Very deep MDD + slow recovery
            if (row['Max Drawdown (s)'] < (mdd_median - MDD_BUFFER_SECONDS) and
                row['Reset Velocity (s/Lap)'] < rv_median):
                return "Brittle Performer"
            
            # 5. Outlier / Critical Fail: Extreme case
            if row['Max Drawdown (s)'] <= aggregated_metrics_df['Max Drawdown (s)'].quantile(0.1):
                return "Outlier / Critical Fail"
            
            # 6. Volatile Performer: Residual (SHOULD BE ELIMINATED)
            # This is a catch-all for drivers not fitting other categories
            # Better approach: Define explicit criteria for each category
            return "Volatile Performer"

        aggregated_metrics_df['Resilience Profile'] = aggregated_metrics_df.apply(assign_archetype, axis=1)

        # =====================================================================
        # POST-HOC CORRECTION (BAD PRACTICE - but required with percentile approach)
        # =====================================================================
        # Ensure at least one "Entropy King" exists
        if "Entropy King" not in aggregated_metrics_df['Resilience Profile'].values:
            best_idx = aggregated_metrics_df['Restart Delta (s)'].idxmax()
            old_profile = aggregated_metrics_df.loc[best_idx, 'Resilience Profile']
            aggregated_metrics_df.loc[best_idx, 'Resilience Profile'] = "Entropy King"
            if LOG_LEVEL in ['DEBUG', 'INFO']:
                print(f"Note: Reassigned {aggregated_metrics_df.loc[best_idx, 'Driver']} "
                      f"from {old_profile} → Entropy King (no natural kings found)")
        
        # Add archetype confidence scores
        def calculate_archetype_confidence(row):
            """
            Score 0-1 indicating how well the driver fits their assigned archetype.
            Based on distance from archetype's expected center.
            """
            profile = row['Resilience Profile']
            
            if profile == "Entropy King":
                # Expected: MDD near q70, RV near q70
                mdd_score = (row['Max Drawdown (s)'] - mdd_q70) / (mdd_q70 - mdd_median + 0.001)
                rv_score = (row['Reset Velocity (s/Lap)'] - rv_q70) / (rv_q70 - rv_median + 0.001)
                return min(1.0, max(0, (mdd_score + rv_score) / 2))
            
            elif profile == "Steady Operator":
                # Expected: Shallow MDD, low RV
                mdd_score = (row['Max Drawdown (s)'] - mdd_median) / (mdd_q70 - mdd_median + 0.001)
                rv_score = (rv_median - row['Reset Velocity (s/Lap)']) / (rv_median + 0.001)
                return min(1.0, max(0, (mdd_score + rv_score) / 2))
            
            elif profile == "Elastic Aggressor":
                # Expected: Deep MDD, high RV
                mdd_score = (mdd_median - row['Max Drawdown (s)']) / (mdd_median + 0.001)
                rv_score = (row['Reset Velocity (s/Lap)'] - rv_median) / (rv_median + 0.001)
                return min(1.0, max(0, (mdd_score + rv_score) / 2))
            
            else:
                # Other profiles: default confidence
                return 0.5

        aggregated_metrics_df['Archetype Confidence'] = aggregated_metrics_df.apply(
            calculate_archetype_confidence, axis=1
        )
        
        output_file = os.path.join(self.results_path, f'{self.year}_resilience_profiles.csv')
        aggregated_metrics_df.to_csv(output_file, index=False)
        
        if LOG_LEVEL in ['DEBUG', 'INFO']:
            print(f"Saved resilience profiles to {output_file}")
            print(f"\nArchetype Distribution:")
            for profile, count in aggregated_metrics_df['Resilience Profile'].value_counts().items():
                print(f"  {profile}: {count} drivers")
        
        return aggregated_metrics_df

if __name__ == '__main__':
    # Placeholder test
    pass
