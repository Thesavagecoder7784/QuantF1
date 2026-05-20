import pandas as pd


def classify_anomalies(laps: pd.DataFrame) -> pd.DataFrame:
    """Flag laps that should be excluded from clean-pace analysis."""
    laps['anomaly_flag'] = 'normal'

    laps.loc[laps['PitOutTime'].notna() & (laps['anomaly_flag'] == 'normal'), 'anomaly_flag'] = 'out_lap'
    laps.loc[laps['PitInTime'].notna() & (laps['anomaly_flag'] == 'normal'), 'anomaly_flag'] = 'in_lap'

    # TrackStatus is a string of concatenated codes; '1' = green flag only.
    laps.loc[(laps['TrackStatus'].astype(str) != '1') & (laps['anomaly_flag'] == 'normal'), 'anomaly_flag'] = 'track_status'

    laps.loc[laps['lap_time_seconds'].isna() & (laps['anomaly_flag'] == 'normal'), 'anomaly_flag'] = 'missing'

    clean = laps[laps['anomaly_flag'] == 'normal']
    for driver, group in clean.groupby('Driver'):
        median = group['lap_time_seconds'].median()
        std = group['lap_time_seconds'].std()
        outlier_mask = (
            (laps['Driver'] == driver)
            & (laps['anomaly_flag'] == 'normal')
            & (laps['lap_time_seconds'].sub(median).abs() > 5 * std)
        )
        laps.loc[outlier_mask, 'anomaly_flag'] = 'outlier'

    return laps
