# QuantF1 🏁📊🏎️ 

A quantitative framework for understanding Formula 1 driver performance under uncertainty

QuantF1 applies concepts from quantitative finance, risk management, and statistical learning to Formula 1 race data to model driver performance as a stochastic process, not a highlight reel.

Instead of asking “Who’s fastest?”, QuantF1 asks:

Who is structurally advantaged, under which conditions, and why?

The project builds a full analytical arc — from efficiency, to behavior, to context, to resilience, to repeatability — and ends with probabilistic inference rather than deterministic predictions.

## Core Philosophy

Formula 1 performance is:
- Noisy
- Context-dependent
- Regime-sensitive
- Path-dependent
- Non-stationary

So QuantF1 treats each driver as a risk-bearing strategy, each lap as a return, and each race as a realized distribution, not a result.

This repo is not about takes.
It’s about structure.

## Analytical Arc (Step-by-Step Framework)
### 1. Sharpe Ratio of a Driver — Efficiency

Question:
How much pace does a driver extract per unit of chaos?

This establishes the baseline distinction between:

Raw speed

Risk-adjusted performance

It proves that “fast” and “efficient” are not the same thing.

Output: Driver efficiency scores across races and stints
Role: Baseline lens (used throughout the framework)

### 2. Sortino Ratio of a Driver — Controlled Aggression

Question:
Which mistakes actually matter?

We refine risk from:

variance → downside variance

This separates:

productive aggression
from

destructive volatility

Output: Asymmetric risk-adjusted performance
Role: Complements Sharpe, adds behavioral nuance

### 3. Execution Profile — How Performance Is Delivered

Question:
What did the race actually look like?

Here, the project becomes behavioral.

We model:

smooth vs turbulent execution

improving vs fading performance

intra-race shape of performance

Output: Execution curves and shape signatures
Role: Narrative engine + reusable behavioral representation

### 4. Track & Regime Sensitivity — Context Dependence

Question:
When does a driver’s execution work—and when doesn’t it?

We introduce race regimes:

degradation profiles

aero vs traction sensitivity

overtaking constraints

volatility environments

This is the bridge from description → inference.

Output: Driver × track regime sensitivity matrix
Role: Makes prediction possible without hype

### 5. Drawdown & Recovery — Fragility vs Resilience

Question:
What happens when things go wrong?

We analyze:

depth of collapse

speed of recovery

volatility decay vs compounding

This captures downside dynamics that averages hide.

Output: Drawdown severity and recovery half-life
Role: Essential for season-level modeling

### 6. Consistency Across Races — Repeatability

Question:
Is this structural skill or situational brilliance?

We test:

temporal stability

cross-context persistence

regime robustness

This guards against overfitting and narrative traps.

Output: Stability scores and confidence bands
Role: Converts insight into conviction

### 7. Synthesis — From Profiles to Probabilities

Final Question:
Given this context, who is structurally advantaged?

We combine:

efficiency

aggression

execution style

context sensitivity

resilience

consistency

The result is probabilistic advantage, not predictions.

Output: Driver advantage distributions by race context
Role: Decision-grade inference

## What This Project Is (and Isn’t)

QuantF1 is:

A research framework

A modeling pipeline

A lens for reasoning under uncertainty

A bridge between sports and quantitative finance

QuantF1 is not:

A prediction bot

A hype machine

A ranking generator

A fantasy optimizer

## Why QuantF1 Exists

Most F1 analysis collapses complexity into:

lap times

positions

opinions

QuantF1 keeps complexity but gives it structure.

This is a framework for thinking clearly about performance when:

the data is noisy

the environment shifts

and outcomes lie

## Status

- 🚧 Active research project
- 📈 Metrics evolving
