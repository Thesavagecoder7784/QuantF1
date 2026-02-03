import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import os

class DrawdownVisualizer:
    def __init__(self, year: int):
        self.year = year
        self.plots_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 'plots'))
        os.makedirs(self.plots_path, exist_ok=True)
        
        # Color mapping for 2025 Teams (Unique shades for teammates)
        self.colors = {
            # McLaren
            'NOR': '#FF8000', 'PIA': '#FFB366', 
            # Ferrari
            'LEC': '#E80020', 'HAM': '#990000', # Red tones
            # Red Bull
            'VER': '#3671C6', 'LAW': '#1A3F7A', # Lawson in RBR
            # Mercedes
            'RUS': '#27F4D2', 'ANT': '#00A19B', # Antonelli
            # Aston Martin
            'ALO': '#229971', 'STR': '#166147',
            # Alpine
            'GAS': '#0093CC', 'DOO': '#005F82',
            # Williams
            'ALB': '#64C4FF', 'SAI': '#004A77', # Sainz in Williams
            # VCARB
            'TSU': '#6692FF', 'HAD': '#33497F', # Hadjar
            # Haas
            'HUL': '#B6BABD', 'BEA': '#5C5D5F', # Bearman
            # Stake / Audi
            'BOR': '#52FF00', 'COL': '#2E8C00'  # Colapinto in Audi/Stake?
        }
        self.default_color = '#FFFFFF'

        # Failure Marker Config
        self.markers = {
            'Major Incident': {'marker': 'X', 'label': 'Major Incident', 'color': '#FF3131'},
            'Traffic': {'marker': 'o', 'label': 'Traffic Erosion', 'color': '#FFD700'},
            'Operational': {'marker': 'D', 'label': 'Operational (Pit)', 'color': '#00D7FF'}
        }

    def plot_race_equity(self, equity_df, race_name, target_drivers=None):
        """
        Plots the Execution Equity curve and an Underwater Drawdown plot with symbol-based markers.
        """
        if target_drivers is None:
            target_drivers = equity_df['Driver'].unique()[:6]

        plt.style.use('dark_background')
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 12), sharex=True, gridspec_kw={'height_ratios': [2, 1]})
        fig.patch.set_facecolor('#0a0a0a')
        
        # Track which failure types are used for the legend
        seen_failures = set()

        for driver in target_drivers:
            d_df = equity_df[equity_df['Driver'] == driver].sort_values('LapNumber')
            if d_df.empty: continue
            
            color = self.colors.get(driver, self.default_color)
            
            # 1. Equity Curve
            ax1.plot(d_df['LapNumber'], d_df['ExecutionEquity'], label=driver, linewidth=3, color=color, alpha=0.9)
            
            # 2. Drawdown (Underwater)
            peak = d_df['ExecutionEquity'].cummax()
            drawdown = d_df['ExecutionEquity'] - peak
            ax2.fill_between(d_df['LapNumber'], drawdown, 0, alpha=0.2, color=color)
            ax2.plot(d_df['LapNumber'], drawdown, linewidth=1.5, color=color, alpha=0.6)

            # 3. Symbol-Based Annotations (Markers on the Equity Curve)
            failure_points = d_df[d_df['FailureType'] != 'None']
            for _, row in failure_points.iterrows():
                # Only mark significant equity shifts
                if abs(row['EquityChange']) > 0.5:
                    f_type = row['FailureType']
                    m_cfg = self.markers.get(f_type)
                    if m_cfg:
                        ax1.scatter(row['LapNumber'], row['ExecutionEquity'], 
                                   marker=m_cfg['marker'], color=m_cfg['color'], 
                                   edgecolors='white', s=80, zorder=5, alpha=0.9)
                        seen_failures.add(f_type)

        # Highlight Chaos Zones (SC/Restarts)
        sc_laps = equity_df[equity_df['IsSC'] == True]['LapNumber'].unique()
        for lap in sc_laps:
            ax1.axvspan(lap-0.5, lap+0.5, color='yellow', alpha=0.02)
            ax2.axvspan(lap-0.5, lap+0.5, color='yellow', alpha=0.02)

        # Custom Legends
        # Main Driver Legend
        driver_legend = ax1.legend(loc='upper left', frameon=True, facecolor='#1a1a1a', 
                                  edgecolor='#333333', fontsize=12, title="Execution Equity")
        plt.setp(driver_legend.get_title(), color='white', weight='bold')

        # Failure Type Legend (Manual proxies)
        from matplotlib.lines import Line2D
        failure_handles = [
            Line2D([0], [0], marker=self.markers[f]['marker'], color='w', label=self.markers[f]['label'],
                   markerfacecolor=self.markers[f]['color'], markersize=10, linestyle='None')
            for f in sorted(list(seen_failures))
        ]
        if failure_handles:
            from matplotlib.legend import Legend
            failure_legend = Legend(ax1, failure_handles, [h.get_label() for h in failure_handles],
                                   loc='lower left', frameon=True, facecolor='#1a1a1a', 
                                   edgecolor='#333333', fontsize=10, title="Failure Taxonomy")
            ax1.add_artist(failure_legend)
            plt.setp(failure_legend.get_title(), color='white', weight='bold')

        # Styling
        ax1.set_title(f'Physics of Failure: {race_name} {self.year}', 
                     fontsize=24, color='#f1f1f1', weight='bold', pad=20)
        ax1.set_ylabel('Execution Equity (s)', fontsize=16, color='#cccccc')
        ax1.grid(True, alpha=0.05, color='#ffffff', linestyle='--')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)

        ax2.set_title('Performance Drawdowns (Underwater)', fontsize=18, color='#ff4444', weight='bold', pad=15)
        ax2.set_ylabel('Depth (s)', fontsize=16, color='#cccccc')
        ax2.set_xlabel('Lap Number', fontsize=16, color='#cccccc')
        ax2.grid(True, alpha=0.05, color='#ffffff', linestyle='--')
        ax2.spines['right'].set_visible(False)
        
        plt.tight_layout()
        filename = f"{self.year}_{race_name.replace(' ', '_')}_equity_analysis.png"
        save_path = os.path.join(self.plots_path, filename)
        plt.savefig(save_path, facecolor='#0a0a0a', dpi=200)
        plt.close()
        print(f"Saved refined Physics of Failure plot to {filename}")

    def plot_resilience_scatter(self, profiles_df):
        """
        Generates the "Seasonal Resilience Map" using Physics of Failure archetypes.
        """
        from adjustText import adjust_text
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 10))
        fig.patch.set_facecolor('#0a0a0a')
        ax.set_facecolor('#0a0a0a')

        # X = Max Drawdown, Y = Reset Velocity
        x = profiles_df['Max Drawdown (s)']
        y = profiles_df['Reset Velocity (s/Lap)']
        drivers = profiles_df['Driver']
        
        # Color by Refined Profile
        profile_colors = {
            'Entropy King': '#00D7FF',      # Cyan (Elite Chaos)
            'Steady Operator': '#00FF41',   # Matrix Green (Consistency)
            'Elastic Aggressor': '#FFD700', # Gold (Fast but risky)
            'Brittle Performer': '#FF3131', # Red (Failure Prone)
            'Outlier / Critical Fail': '#888888' # Gray
        }
        
        texts = []
        for i, driver in enumerate(drivers):
            profile = profiles_df.loc[i, 'Resilience Profile']
            color = profile_colors.get(profile, '#888888')
            ax.scatter(x[i], y[i], s=180, color=color, alpha=0.9, edgecolors='white', linewidth=1.5)
            texts.append(ax.text(x[i], y[i], driver, fontsize=11, weight='bold', color='white'))

        adjust_text(texts, arrowprops=dict(arrowstyle='->', color='gray', lw=0.5))

        # Styling
        ax.set_title(f'The Physics of Failure: Resilience Map - {self.year}', fontsize=24, color='white', weight='bold', pad=25)
        ax.set_xlabel('Max Drawdown Depth (s) - Failure Severity', fontsize=16, color='#cccccc')
        ax.set_ylabel('Reset Velocity (s/Lap) - V-Shape Recovery Speed', fontsize=16, color='#cccccc')
        
        # QUADRANT LABELS (Corrected for X=Shallow is Right, Y=Fast is Top)
        xlim = ax.get_xlim()
        ylim = ax.get_ylim()
        
        # Entropy King Zone: Shallow MDD + Fast Reset
        ax.text(xlim[1]*0.9, ylim[1]*0.9, "Entropy Kings\n(Hardened Elite)", 
                color='#00D7FF', fontsize=16, alpha=0.6, ha='right', weight='bold')
        
        # Elastic Aggressor Zone: Deep MDD + Fast Reset
        ax.text(xlim[0]*0.9, ylim[1]*0.9, "Elastic\nAggressors", 
                color='#FFD700', fontsize=16, alpha=0.6, ha='left', weight='bold')
        
        # Brittle Performer Zone: Deep MDD + Slow Reset
        ax.text(xlim[0]*0.9, ylim[0]*0.9, "Brittle\nPerformers", 
                color='#FF3131', fontsize=16, alpha=0.6, ha='left', weight='bold')
        
        # Steady Operator Zone: Shallow MDD + Slow Reset
        ax.text(xlim[1]*0.9, ylim[0]*0.9, "Steady\nOperators", 
                color='#00FF41', fontsize=16, alpha=0.6, ha='right', weight='bold')

        ax.grid(True, alpha=0.05, color='white')
        
        plt.tight_layout()
        filename = f"{self.year}_seasonal_resilience_map.png"
        plt.savefig(os.path.join(self.plots_path, filename), facecolor='#0a0a0a', dpi=200)
        plt.close()
        print(f"Saved refined resilience scatter map to {filename}")

    def plot_recovery_comparison(self, equity_df, d1, d2, race_name):
        """
        Zooms in on a recovery battle between two drivers.
        """
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(14, 8))
        fig.patch.set_facecolor('#0a0a0a')
        
        # Custom colors for comparison if they are in the same team
        comp_colors = {d1: self.colors.get(d1, self.default_color), d2: '#FFB366' if d1 == 'NOR' and d2 == 'PIA' else self.default_color}
        if d1 == 'NOR' and d2 == 'PIA':
            comp_colors['NOR'] = '#FF8000' # McLaren Papaya
            comp_colors['PIA'] = '#555555' # Slate/Dark for contrast
        
        for driver in [d1, d2]:
            d_df = equity_df[equity_df['Driver'] == driver].sort_values('LapNumber')
            color = comp_colors.get(driver, self.default_color)
            ax.plot(d_df['LapNumber'], d_df['ExecutionEquity'], label=driver, linewidth=4, color=color)
            
            # Highlight recovery zones
            peak = d_df['ExecutionEquity'].cummax()
            is_recovering = (d_df['ExecutionEquity'] < peak)
            ax.fill_between(d_df['LapNumber'], d_df['ExecutionEquity'], peak, where=is_recovering, alpha=0.15, color=color)

        ax.set_title(f'The Recovery Battle: {d1} vs {d2} ({race_name})', fontsize=22, color='white', weight='bold')
        ax.set_ylabel('Execution Equity (s)', fontsize=16)
        ax.set_xlabel('Lap Number', fontsize=16)
        ax.legend(fontsize=14)
        ax.grid(True, alpha=0.1)
        
        plt.tight_layout()
        filename = f"{self.year}_recovery_battle_{d1}_{d2}.png"
        plt.savefig(os.path.join(self.plots_path, filename), facecolor='#0a0a0a', dpi=200)
        plt.close()
        print(f"Saved recovery comparison to {filename}")

if __name__ == '__main__':
    # Test loading profiles
    try:
        profiles_df = pd.read_csv('QuantF1/5_Drawdown_and_Recovery/results/2025_resilience_profiles.csv')
        viz = DrawdownVisualizer(2025)
        viz.plot_resilience_scatter(profiles_df)
    except FileNotFoundError:
        print("Profiles not found. Run run_drawdown_analysis.py first.")
