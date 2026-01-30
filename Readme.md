The overall idea of the project QuantF1 is to better understand the world of F1 using quantitative methods 

# Formula 1 Driver Performance: Stint-Adjusted Sharpe Ratio
The first step in doing that is understanding the Sharpe Ratio of a Driver
In general, the Sharpe Ratio is a financial metric used to evaluate an investment's return relative to the risk (also considered as its volatility). A higher ratio indicates that the investment has a better risk-adjusted performance. 

In this particular context of F1, we define:
- Return: A driver's pace relative to a dynamic, fuel- and tire-adjusted benchmark.
- Risk: The inconsistency or volatility in that pace.

The result is a "Driver Sharpe Ratio" that rewards drivers who are not only fast but also highly consistent, providing a more holistic view of their performance than raw lap times alone.

# Methodology

The core of this analysis is a sophisticated benchmarking method that isolates driver performance from changing track conditions, fuel load, and tire degradation.

## 1. Dynamic, Stint-Specific Benchmarking
A single benchmark lap time for an entire race is insufficient. This model creates a unique benchmark for each stint and tire compound combination.
- For each stint/compound group (e.g., all drivers on the Medium tire in their first stint), we fit a linear regression model to the lap times versus the lap number.
- This model (lap_time = slope * lap_number + intercept) captures the expected pace evolution, naturally accounting for the car getting lighter (fuel burn-off) and tires degrading.
- The output is a dynamic trendline representing the expected "par" performance for that specific strategic phase of the race.

## 2. Calculating "Returns" (Pace Delta)

For each driver's lap, we calculate the LapTimeDelta:
LapTimeDelta = ActualLapTime - BenchmarkTime

- A negative delta represents a "positive return," as the driver was faster than expected for that lap.
- A positive delta means the driver was slower than the benchmark.

## 3. Calculating the Sharpe Ratio

The Sharpe Ratio is calculated for each driver by aggregating their performance across all their stints.

1. Per-Stint Analysis: For each of a driver's stints, we calculate the mean and standard deviation of their LapTimeDelta.
2. Weighted Aggregation: The final "Driver Sharpe Ratio" is a weighted average of the per-stint Sharpe Ratios, weighted by the number of laps in each stint.

The formula for a given stint is:

Sharpe Ratio = -Mean(LapTimeDelta) / StdDev(LapTimeDelta)

The Mean(LapTimeDelta) is negated because a lower (more negative) delta signifies better performance.
This aligns the metric so that a higher, positive Sharpe Ratio is always better.

# File Descriptions

- driver_sharpe_ratio.py: The main script that performs the analysis for a given race. It calculates the Sharpe Ratio for all drivers and generates the output files.
- visualize_stint_modeling.py: A utility script to generate a plot that visualizes the underlying regression model for a single driver's stints.

# Interpreting the Output

The analysis generates three files in the QuantF1/plots and QuantF1/results directories.

1. Results CSV (results/{year}_{race}_Driver_Sharpe_Ratios.csv)
This file contains the detailed metrics for each driver, including:
- Mean Delta vs Benchmark (s): The driver's average pace against the expected trendline. Negative is faster.
- Lap Time Std Dev (s): The driver's inconsistency. Lower is better.
- Driver Sharpe Ratio: The final risk-adjusted performance score.

2. Sharpe Ratio Bar Chart (plots/{year}_{race}_Sharpe_Ratio_Bar_Chart.png)
This chart provides a quick ranking of drivers by their overall risk-adjusted performance.
- High Positive Ratio: Indicates the driver was significantly faster than expected and highly consistent.
- Ratio Near Zero: The driver performed close to the benchmark or was inconsistent.
- Negative Ratio: The driver was, on average, slower than the benchmark.

3. Pace vs. Consistency Scatter Plot (plots/{year}_{race}_Pace_Consistency_Scatter.png)
This plot visualizes the two core components of the Sharpe Ratio.
- Y-axis (Pace): Mean Delta (lower is faster).
- X-axis (Inconsistency): Lap Time Standard Deviation (lower is more consistent).

The ideal position on this chart is the top-left quadrant, representing drivers who are both fast (low delta) and consistent (low standard deviation).


!Pace vs Consistency Plot (plots/2025_Hungarian_Grand_Prix_Pace_Consistency_Scatter.png)

(This plot shows an example of the Pace vs. Consistency analysis for the 2025 Hungarian Grand Prix.)
