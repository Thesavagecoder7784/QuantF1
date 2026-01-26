import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

class RegimeVisualizer:
    """
    Creates visualizations for the Track & Regime Sensitivity analysis.
    """
    def __init__(self, year: int):
        self.year = year
        self.results_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'results'))
        self.plots_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'plots'))
        os.makedirs(self.plots_path, exist_ok=True)
        
        self.load_data()

    def load_data(self):
        """Loads the analysis results."""
        try:
            self.sensitivity_df = pd.read_csv(os.path.join(self.results_path, f'{self.year}_sensitivity_analysis.csv'))
            self.conditional_metrics_df = pd.read_csv(os.path.join(self.results_path, f'{self.year}_conditional_metrics.csv'))
            self.profiles_df = pd.read_csv(os.path.join(self.results_path, f'{self.year}_driver_profiles.csv'))
            
            # Load skill profiles if available
            skill_path = os.path.join(self.results_path, f'{self.year}_driver_skill_profiles.csv')
            if os.path.exists(skill_path):
                self.skill_profiles_df = pd.read_csv(skill_path)
            else:
                self.skill_profiles_df = None
                
        except FileNotFoundError as e:
            print(f"Error: {e}. Please run conditional_analysis.py and driver_profiler.py first.")
            raise

    def plot_sensitivity_summary(self):
        """
        Plots Regime Spread and Stability for each driver.
        """
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, axes = plt.subplots(2, 1, figsize=(16, 14), sharex=True)
        
        # Plot Regime Spread
        sns.barplot(data=self.sensitivity_df.sort_values('Regime Spread', ascending=False), 
                    x='Driver', y='Regime Spread', ax=axes[0], palette='viridis')
        axes[0].set_title(f'{self.year} Driver Regime Spread (Performance Delta Across Regimes)', fontsize=16)
        axes[0].set_ylabel('Sharpe Ratio Spread')
        
        # Plot Regime Stability
        sns.barplot(data=self.sensitivity_df.sort_values('Regime Stability', ascending=True), 
                    x='Driver', y='Regime Stability', ax=axes[1], palette='plasma')
        axes[1].set_title(f'{self.year} Driver Regime Stability (Performance Variance Across Regimes)', fontsize=16)
        axes[1].set_ylabel('Sharpe Ratio Variance')
        
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_sensitivity_summary.png'))
        plt.close()

    def plot_conditional_performance(self, regime_type='Degradation'):
        """
        Plots conditional Sharpe Ratio for a given regime type.
        """
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(16, 10))
        
        sns.barplot(data=self.conditional_metrics_df, x='Driver', y='Driver Sharpe Ratio', hue=regime_type, ax=ax, palette='coolwarm')
        
        ax.set_title(f'{self.year} Driver Performance by {regime_type} Regime', fontsize=18)
        ax.set_ylabel('Average Sharpe Ratio')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_performance_vs_{regime_type.lower()}.png'))
        plt.close()

    def plot_profile_distribution(self):
        """
        Plots the distribution of driver profiles.
        """
        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(12, 12))
        
        profile_counts = self.profiles_df['Profile'].value_counts()
        
        ax.pie(profile_counts, labels=profile_counts.index, autopct='%1.1f%%', startangle=90,
               colors=sns.color_palette('pastel'))
        ax.set_title(f'{self.year} Distribution of Driver Profiles (Clustered)', fontsize=18)
        
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_profile_distribution.png'))
        plt.close()

    def plot_cluster_insights(self):
        """
        Visualizes the characteristics of each profile using a parallel coordinates plot or heatmap
        to show which features define each cluster.
        Note: This requires re-calculating the feature vectors for the drivers to map them to profiles,
        or we can merge the source data if available. 
        For simplicity, we will assume we can join profile labels back to metrics.
        """
        # Re-aggregate features similar to driver_profiler.py to visualize what makes each profile unique
        # We need the original features.
        
        # 1. Reconstruct minimal feature set
        feature_dfs = []
        deg_pivot = self.conditional_metrics_df.groupby(['Driver', 'Degradation'])['Driver Sharpe Ratio'].mean().unstack()
        deg_pivot.columns = [f'Deg_{c}' for c in deg_pivot.columns]
        feature_dfs.append(deg_pivot)
        
        vol_pivot = self.conditional_metrics_df.groupby(['Driver', 'Volatility'])['Driver Sharpe Ratio'].mean().unstack()
        vol_pivot.columns = [f'Vol_{c}' for c in vol_pivot.columns]
        feature_dfs.append(vol_pivot)
        
        features = pd.concat(feature_dfs, axis=1)
        features = features.apply(lambda x: x.fillna(x.mean()), axis=1).fillna(0)
        
        # Join Profile
        merged = features.merge(self.profiles_df, on='Driver')
        
        if merged.empty:
            print("Could not merge profiles for insight plot.")
            return

        # Calculate mean feature values per Profile
        profile_means = merged.drop(columns=['Driver']).groupby('Profile').mean()
        
        # Plot Heatmap
        plt.figure(figsize=(14, 10))
        sns.heatmap(profile_means, annot=True, cmap='RdYlGn', center=0, fmt='.2f')
        plt.title(f'{self.year} Driver Profile Characteristics (Mean Sharpe Ratio)', fontsize=16)
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_profile_characteristics_heatmap.png'))
        plt.close()

    def plot_skill_distribution(self):
        """
        Plots the distribution of driver skill profiles.
        """
        if self.skill_profiles_df is None:
            return

        plt.style.use('seaborn-v0_8-darkgrid')
        fig, ax = plt.subplots(figsize=(12, 12))
        
        profile_counts = self.skill_profiles_df['Profile'].value_counts()
        
        ax.pie(profile_counts, labels=profile_counts.index, autopct='%1.1f%%', startangle=90,
               colors=sns.color_palette('pastel'))
        ax.set_title(f'{self.year} Distribution of Driver Skill Profiles (Teammate Delta)', fontsize=18)
        
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_skill_profile_distribution.png'))
        plt.close()

    def plot_skill_insights(self):
        """
        Visualizes the characteristics of each SKILL profile.
        """
        if self.skill_profiles_df is None:
            return

        # 1. Reconstruct minimal feature set using Teammate Delta
        feature_dfs = []
        deg_pivot = self.conditional_metrics_df.groupby(['Driver', 'Degradation'])['Teammate Delta Sharpe Ratio'].mean().unstack()
        deg_pivot.columns = [f'Deg_{c}' for c in deg_pivot.columns]
        feature_dfs.append(deg_pivot)
        
        vol_pivot = self.conditional_metrics_df.groupby(['Driver', 'Volatility'])['Teammate Delta Sharpe Ratio'].mean().unstack()
        vol_pivot.columns = [f'Vol_{c}' for c in vol_pivot.columns]
        feature_dfs.append(vol_pivot)
        
        features = pd.concat(feature_dfs, axis=1)
        features = features.apply(lambda x: x.fillna(x.mean()), axis=1).fillna(0)
        
        # Join Profile
        merged = features.merge(self.skill_profiles_df, on='Driver')
        
        # Calculate mean feature values per Profile
        profile_means = merged.drop(columns=['Driver']).groupby('Profile').mean()
        
        # Plot Heatmap
        plt.figure(figsize=(14, 10))
        sns.heatmap(profile_means, annot=True, cmap='RdYlGn', center=0, fmt='.2f')
        plt.title(f'{self.year} Driver Skill Characteristics (Mean Teammate Delta)', fontsize=16)
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_skill_profile_characteristics_heatmap.png'))
        plt.close()

    def plot_skill_vs_machine_quadrant(self):
        """
        Plots Team Mean Sharpe (Machine) vs Teammate Delta Sharpe (Skill).
        Publication-ready with dark mode, shaded quadrants, and team colors.
        """
        import numpy as np
        
        if self.skill_profiles_df is None:
            return

        # Team color mapping
        TEAM_COLORS = {
            'Red Bull Racing': '#3671C6', 'Mercedes': '#27F4D2', 'Ferrari': '#E80020',
            'McLaren': '#FF8000', 'Aston Martin': '#229971', 'Alpine': '#0093CC',
            'Williams': '#64C4FF', 'RB': '#6692FF', 'Haas F1 Team': '#B6BABD',
            'Kick Sauber': '#52e252', 'N/A': '#808080'
        }
        
        # We need team info - get it from conditional_metrics if available
        # For now, use skill profiles only
        agg_df = self.conditional_metrics_df.groupby('Driver')[['Driver Sharpe Ratio', 'Teammate Delta Sharpe Ratio']].mean().reset_index()
        merged = agg_df.merge(self.skill_profiles_df, on='Driver')
        merged['Team Performance'] = merged['Driver Sharpe Ratio'] - merged['Teammate Delta Sharpe Ratio']
        
        # Dark Mode Style
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(16, 12))
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')
        
        # Define quadrant boundaries
        x_mid = merged['Team Performance'].median()
        y_mid = 0
        
        x_min, x_max = merged['Team Performance'].min() - 0.3, merged['Team Performance'].max() + 0.3
        y_min, y_max = merged['Teammate Delta Sharpe Ratio'].min() - 0.2, merged['Teammate Delta Sharpe Ratio'].max() + 0.2
        
        # Add shaded quadrants with labels
        # Top Right - Elite in Elite Car (Green tint)
        ax.fill_between([x_mid, x_max], y_mid, y_max, alpha=0.15, color='#00FF00')
        ax.text((x_mid + x_max)/2, (y_mid + y_max)/2, 'ELITE DRIVER\nFAST CAR', 
                ha='center', va='center', fontsize=14, color='#00FF00', alpha=0.6, weight='bold')
        
        # Top Left - Elite in Slow Car (Cyan tint)  
        ax.fill_between([x_min, x_mid], y_mid, y_max, alpha=0.15, color='#00FFFF')
        ax.text((x_min + x_mid)/2, (y_mid + y_max)/2, 'OVERACHIEVER\nSLOW CAR', 
                ha='center', va='center', fontsize=14, color='#00FFFF', alpha=0.6, weight='bold')
        
        # Bottom Right - Passenger in Fast Car (Orange tint)
        ax.fill_between([x_mid, x_max], y_min, y_mid, alpha=0.15, color='#FF4500')
        ax.text((x_mid + x_max)/2, (y_min + y_mid)/2, 'UNDERPERFORMER\nFAST CAR', 
                ha='center', va='center', fontsize=14, color='#FF4500', alpha=0.6, weight='bold')
        
        # Bottom Left - Struggling in Slow Car (Red tint)
        ax.fill_between([x_min, x_mid], y_min, y_mid, alpha=0.15, color='#FF0000')
        ax.text((x_min + x_mid)/2, (y_min + y_mid)/2, 'STRUGGLING\nSLOW CAR', 
                ha='center', va='center', fontsize=14, color='#FF0000', alpha=0.4, weight='bold')
        
        # Draw quadrant lines
        ax.axhline(y_mid, color='white', linestyle='-', alpha=0.5, linewidth=2)
        ax.axvline(x_mid, color='white', linestyle='-', alpha=0.5, linewidth=2)
        
        # Profile to color mapping for scatter
        profile_colors = {
            'Team Leader': '#00FF00',
            'Team Matcher': '#FFFF00', 
            'Team Trailer': '#FF4500',
            'Inconsistent': '#FF00FF',
            'High Variance': '#00FFFF'
        }
        
        # Plot each driver
        texts = []
        for i, row in merged.iterrows():
            color = profile_colors.get(row['Profile'], '#FFFFFF')
            ax.scatter(row['Team Performance'], row['Teammate Delta Sharpe Ratio'], 
                      s=300, c=color, edgecolors='white', linewidth=2, alpha=0.9, zorder=5)
            
            # Collect text annotations for adjustText
            txt = ax.text(row['Team Performance'], row['Teammate Delta Sharpe Ratio'], 
                         row['Driver'], fontsize=11, color='white', weight='bold',
                         bbox=dict(boxstyle='round,pad=0.3', facecolor='#333333', edgecolor='none', alpha=0.8))
            texts.append(txt)
        
        # Use adjustText to spread out overlapping labels
        try:
            from adjustText import adjust_text
            adjust_text(texts, ax=ax, arrowprops=dict(arrowstyle='-', color='white', alpha=0.5),
                       expand_points=(2, 2), force_text=(0.5, 0.5))
        except ImportError:
            # Fallback: manual offset if adjustText not installed
            pass
        
        # Set limits
        ax.set_xlim(x_min, x_max)
        ax.set_ylim(y_min, y_max)
        
        # Labels and Title
        ax.set_title(f'{self.year} MAN vs MACHINE\nDriver Skill vs Car Performance', 
                    fontsize=24, color='white', weight='bold', pad=20)
        ax.set_xlabel('← SLOW CAR              Machine Performance (Team Mean Sharpe)              FAST CAR →', 
                     fontsize=14, color='white', weight='bold')
        ax.set_ylabel('← LOSING TO TEAMMATE              Driver Skill (Teammate Delta)              BEATING TEAMMATE →', 
                     fontsize=14, color='white', weight='bold')
        
        # Add legend
        from matplotlib.lines import Line2D
        legend_elements = [Line2D([0], [0], marker='o', color='w', markerfacecolor=c, markersize=12, label=p, linestyle='None')
                          for p, c in profile_colors.items() if p in merged['Profile'].values]
        ax.legend(handles=legend_elements, loc='upper left', fontsize=11, 
                 facecolor='#1a1a1a', edgecolor='#444444', labelcolor='white')
        
        # Grid
        ax.grid(True, alpha=0.2, color='white')
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_skill_vs_machine_quadrant.png'), 
                   facecolor='#0a0a0a', dpi=150, bbox_inches='tight')
        plt.close()

    def plot_driver_dna_radar(self, target_drivers=None):
        """
        Plots individual radar charts for each driver showing their regime sensitivity profile.
        Redesigned for publication clarity with separate panels per driver.
        """
        import numpy as np
        
        # Team color mapping
        DRIVER_COLORS = {
            'VER': '#3671C6', 'NOR': '#FF8000', 'PIA': '#FF8000', 'LEC': '#E80020',
            'SAI': '#E80020', 'HAM': '#E80020', 'RUS': '#27F4D2', 'ANT': '#27F4D2',
            'ALO': '#229971', 'STR': '#229971', 'GAS': '#0093CC', 'COL': '#0093CC',
            'TSU': '#6692FF', 'HAD': '#6692FF', 'LAW': '#6692FF', 'ALB': '#64C4FF',
            'BOR': '#52e252', 'HUL': '#B6BABD', 'BEA': '#B6BABD', 'OCO': '#0093CC',
            'BOT': '#52e252', 'ZHO': '#52e252', 'DOO': '#0093CC'
        }
        
        if target_drivers is None:
            # Default to top 6 interesting drivers for 2x3 grid
            target_drivers = ['VER', 'NOR', 'LEC', 'RUS', 'HAM', 'PIA']
            
        # Build radar data
        radar_data = []
        
        for driver in target_drivers:
            d_metrics = self.conditional_metrics_df[self.conditional_metrics_df['Driver'] == driver]
            if d_metrics.empty:
                continue
                
            try:
                # Use raw Driver Sharpe Ratio for better differentiation
                high_deg = d_metrics[d_metrics['Degradation'] == 'High']['Driver Sharpe Ratio'].mean()
                very_high_deg = d_metrics[d_metrics['Degradation'] == 'Very High']['Driver Sharpe Ratio'].mean()
                chaotic = d_metrics[d_metrics['Volatility'] == 'Chaotic']['Driver Sharpe Ratio'].mean()
                power = d_metrics[d_metrics['Power vs Downforce Sensitivity'] == 'Power-Dominant']['Driver Sharpe Ratio'].mean()
                technical = d_metrics[d_metrics['Power vs Downforce Sensitivity'] == 'Downforce-Dominant']['Driver Sharpe Ratio'].mean()
                
                radar_data.append({
                    'Driver': driver,
                    'Tire Killer\n(High Deg)': high_deg if not np.isnan(high_deg) else 0,
                    'Chaos Master\n(Volatile)': chaotic if not np.isnan(chaotic) else 0,
                    'Power Track\nSpecialist': power if not np.isnan(power) else 0,
                    'Technical\nWizard': technical if not np.isnan(technical) else 0,
                    'Extreme Deg\nExpert': very_high_deg if not np.isnan(very_high_deg) else 0
                })
            except Exception as e:
                print(f"Skipping {driver} for radar: {e}")
                continue
                
        if not radar_data:
            return

        radar_df = pd.DataFrame(radar_data).set_index('Driver')
        radar_df = radar_df.fillna(0)
        
        # Min-Max Normalization (0.1 to 1.0)
        normalized_df = (radar_df - radar_df.min()) / (radar_df.max() - radar_df.min() + 1e-6)
        normalized_df = normalized_df * 0.8 + 0.2
        normalized_df = normalized_df.fillna(0.5)
        
        categories = list(normalized_df.columns)
        N = len(categories)
        angles = [n / float(N) * 2 * np.pi for n in range(N)]
        angles += angles[:1]
        
        # Create subplot grid
        n_drivers = len(radar_df.index)
        cols = 3
        rows = (n_drivers + cols - 1) // cols
        
        plt.style.use('dark_background')
        fig, axes = plt.subplots(rows, cols, figsize=(18, 6*rows), subplot_kw=dict(polar=True))
        fig.patch.set_facecolor('#0a0a0a')
        
        if n_drivers == 1:
            axes = [axes]
        else:
            axes = axes.flatten()
        
        for idx, driver in enumerate(radar_df.index):
            ax = axes[idx]
            ax.set_facecolor('#0a0a0a')
            
            values = normalized_df.loc[driver].values.flatten().tolist()
            values += values[:1]
            
            color = DRIVER_COLORS.get(driver, '#FFFFFF')
            
            # Plot the radar
            ax.plot(angles, values, linewidth=3, linestyle='solid', color=color, alpha=0.9)
            ax.fill(angles, values, color=color, alpha=0.3)
            
            # Add data points
            ax.scatter(angles[:-1], values[:-1], s=80, c=color, edgecolors='white', linewidth=1.5, zorder=5)
            
            # Styling
            ax.set_theta_offset(np.pi / 2)
            ax.set_theta_direction(-1)
            ax.set_xticks(angles[:-1])
            ax.set_xticklabels(categories, size=9, color='white', weight='bold')
            
            # Remove radial labels
            ax.set_yticklabels([])
            ax.set_ylim(0, 1.1)
            
            # Grid
            for y in [0.25, 0.5, 0.75, 1.0]:
                ax.plot(np.linspace(0, 2*np.pi, 100), [y]*100, color='#333333', lw=0.5, linestyle='--', zorder=0)
            
            # Title with driver name
            ax.set_title(driver, size=24, color=color, weight='bold', pad=20)
        
        # Hide unused subplots
        for idx in range(len(radar_df.index), len(axes)):
            axes[idx].set_visible(False)
        
        fig.suptitle(f'{self.year} DRIVER DNA\nContext Sensitivity Profiles', 
                    size=28, color='white', weight='bold', y=1.02)
        
        plt.tight_layout()
        plt.savefig(os.path.join(self.plots_path, f'{self.year}_driver_dna_radar.png'), 
                   facecolor='#0a0a0a', dpi=150, bbox_inches='tight')
        plt.close()

if __name__ == '__main__':
    try:
        visualizer = RegimeVisualizer(2025)
        
        print("Generating sensitivity summary plot...")
        visualizer.plot_sensitivity_summary()
        
        print("Generating conditional performance plots...")
        visualizer.plot_conditional_performance(regime_type='Degradation')
        visualizer.plot_conditional_performance(regime_type='Volatility')
        visualizer.plot_conditional_performance(regime_type='Power vs Downforce Sensitivity')

        print("Generating profile distribution plot...")
        visualizer.plot_profile_distribution()

        print("Generating cluster insights heatmap...")
        visualizer.plot_cluster_insights()
        
        if visualizer.skill_profiles_df is not None:
             print("Generating skill profile plots...")
             visualizer.plot_skill_distribution()
             visualizer.plot_skill_insights()
             
             print("Generating publication plots...")
             visualizer.plot_skill_vs_machine_quadrant()
             visualizer.plot_driver_dna_radar()

        print("\nVisualizations saved to 'plots' directory.")
        
    except FileNotFoundError:
        pass