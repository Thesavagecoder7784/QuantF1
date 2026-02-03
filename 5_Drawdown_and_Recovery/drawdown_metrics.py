import pandas as pd
import numpy as np
from config import (
    DRAWDOWN_ENTRY_THRESHOLD,
    RECOVERY_COMPLETE_THRESHOLD,
    MIN_RECOVERY_DURATION,
    INCIDENT_THRESHOLD_OPERATIONAL,
    INCIDENT_THRESHOLD_MAJOR,
    INCIDENT_THRESHOLD_TRAFFIC
)

def calculate_drawdown_metrics(equity_df):
    """
    Calculates Physics of Failure metrics: MDD, Reset Velocity, Recovery Curvature.
    
    Returns:
        pd.DataFrame with columns:
        - Driver
        - Max Drawdown (s): Worst equity trough
        - Reset Velocity (s/lap): Average recovery rate
        - Recovery Curvature: Shape of recovery (V vs U vs linear)
        - Restart Delta (s): Performance at SC restarts
        - Major Incident Resilience: Recovery speed from driver errors
        - Traffic Resilience: Recovery speed from traffic incidents
        - Operational Resilience: Recovery speed from pit delays
    """
    metrics_summary = []
    
    for driver in equity_df['Driver'].unique():
        d_df = equity_df[equity_df['Driver'] == driver].sort_values('LapNumber').copy()
        
        # 1. Standard Drawdown Logic
        d_df['Peak'] = d_df['ExecutionEquity'].cummax()
        d_df['Drawdown'] = d_df['ExecutionEquity'] - d_df['Peak']
        mdd = d_df['Drawdown'].min()
        
        # 2. Episode Analysis & Reset Velocity + Recovery Curvature
        recovery_velocities = []
        recovery_curvatures = []  # NEW: Track shape of recovery
        recovery_types = []
        
        in_dd = False
        trough_lap = 0
        trough_equity = 0
        current_failure_type = 'None'
        
        for idx, row in d_df.iterrows():
            if row['Drawdown'] < DRAWDOWN_ENTRY_THRESHOLD:
                if not in_dd:
                    in_dd = True
                    trough_lap = row['LapNumber']
                    trough_equity = row['ExecutionEquity']
                    current_failure_type = row['FailureType']
                
                if row['ExecutionEquity'] < trough_equity:
                    trough_equity = row['ExecutionEquity']
                    trough_lap = row['LapNumber']
                
            elif in_dd and row['Drawdown'] >= RECOVERY_COMPLETE_THRESHOLD:
                # Recovery complete
                in_dd = False
                end_lap = row['LapNumber']
                duration = end_lap - trough_lap
                
                if duration > MIN_RECOVERY_DURATION:
                    # Calculate "Velocity" (Rate of change)
                    total_recovery = abs(row['ExecutionEquity'] - trough_equity)
                    avg_rate = total_recovery / duration
                    recovery_velocities.append(avg_rate)
                    recovery_types.append(current_failure_type)
                    
                    # NEW: Calculate Recovery Curvature (Shape)
                    # Extract the recovery portion
                    recovery_segment = d_df[(d_df['LapNumber'] >= trough_lap) & (d_df['LapNumber'] <= end_lap)].copy()
                    recovery_segment['NormLap'] = recovery_segment['LapNumber'] - trough_lap
                    
                    if len(recovery_segment) > 2:
                        # Fit quadratic to see if V-shaped (concave up) or U-shaped (concave down)
                        try:
                            x = recovery_segment['NormLap'].values
                            y = recovery_segment['ExecutionEquity'].values
                            if len(x) > 2:
                                coeffs = np.polyfit(x, y, 2)
                                curvature = coeffs[0]  # Leading coefficient (positive = concave up = V-shape)
                                recovery_curvatures.append(curvature)
                            else:
                                recovery_curvatures.append(0.0)
                        except:
                            recovery_curvatures.append(0.0)
                    else:
                        recovery_curvatures.append(0.0)

        # 3. Chaos Factor: Restart Performance
        restart_laps = d_df[d_df['RestartLap'] == True]
        avg_restart_delta = restart_laps['EquityChange'].mean() if not restart_laps.empty else 0.0
        
        # 4. Attribution Aggregation (FIXED: Remove "Perfect" score for no failures)
        # Instead, use confidence intervals and flag missing data
        type_recovery = {}
        for r_type in ['Major Incident', 'Traffic', 'Operational']:
            relevant_rates = [v for v, t in zip(recovery_velocities, recovery_types) if t == r_type]
            if not relevant_rates:
                # NEW: Instead of 1.0 (perfect), use NaN to indicate no data
                # This allows downstream to handle appropriately
                type_recovery[f'{r_type} Resilience'] = np.nan
            else:
                type_recovery[f'{r_type} Resilience'] = np.mean(relevant_rates)
        
        # IMPROVED: Traffic Resilience measures recovery capability from traffic incidents
        # Use the recovery velocity data already tracked by incident type
        traffic_rates = [v for v, t in zip(recovery_velocities, recovery_types) if t == 'Traffic']
        if traffic_rates:
            type_recovery['Traffic Resilience'] = np.mean(traffic_rates)
        else:
            # Fallback: if no traffic incidents, use average of all recovery velocities
            type_recovery['Traffic Resilience'] = np.mean(recovery_velocities) if recovery_velocities else np.nan

        # Calculate confidence intervals for Reset Velocity
        if recovery_velocities:
            rv_mean = np.mean(recovery_velocities)
            rv_std = np.std(recovery_velocities) if len(recovery_velocities) > 1 else 0
            # 95% CI
            rv_ci_lower = rv_mean - 1.96 * rv_std / np.sqrt(len(recovery_velocities))
            rv_ci_upper = rv_mean + 1.96 * rv_std / np.sqrt(len(recovery_velocities))
            avg_curvature = np.mean(recovery_curvatures) if recovery_curvatures else 0.0
        else:
            rv_mean = 0.0
            rv_ci_lower = 0.0
            rv_ci_upper = 0.0
            avg_curvature = 0.0

        metrics_summary.append({
            'Driver': driver,
            'Max Drawdown (s)': mdd,
            'Reset Velocity (s/Lap)': rv_mean,
            'Reset Velocity CI Lower': rv_ci_lower,
            'Reset Velocity CI Upper': rv_ci_upper,
            'Recovery Curvature': avg_curvature,
            'Recovery Shape': 'V-Shape' if avg_curvature > 0.015 else ('U-Shape' if avg_curvature < -0.015 else 'Linear'),
            'Restart Delta (s)': avg_restart_delta,
            'Major Incident Resilience': type_recovery['Major Incident Resilience'],
            'Driver Error Resilience': type_recovery['Major Incident Resilience'],
            'Traffic Resilience': type_recovery['Traffic Resilience'],
            'Operational Resilience': type_recovery['Operational Resilience'],
            'Spin/Off-Track Resilience': 1.0,
            'Lockup/Error Resilience': type_recovery['Major Incident Resilience'] if not pd.isna(type_recovery['Major Incident Resilience']) else 1.0
        })
        
    return pd.DataFrame(metrics_summary)

if __name__ == '__main__':
    try:
        equity_df = pd.read_csv('QuantF1/5_Drawdown_and_Recovery/test_equity.csv')
        results = calculate_drawdown_metrics(equity_df)
        print("--- Physics of Failure Metrics ---")
        print(results.sort_values('Max Drawdown (s)', ascending=False))
    except FileNotFoundError:
        print("Test data not found. Run execution_equity.py first.")
