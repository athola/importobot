# Mathematical Review: Independent Bayesian Scorer

## Release Context

Release 0.1.2 replaced the weighted evidence shim with the independent Bayesian scorer. This change was necessary because ambiguous XML payloads were pushing the old noisy-OR model above 0.9 confidence even when the fixtures in `tests/fixtures/format_detection_fixtures.py` were near 0.6. After the rewrite, the fixture suite scores 14/14 formats correctly, and the ambiguous inputs now stop at the 1.5:1 ratio cap (`wiki/benchmarks/format_detection_benchmark.json`). Those numbers come from running `pytest tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`.

## Working Model

Completeness, quality, and uniqueness considered to be conditionally independent once a format hypothesis is fixed. This simplifies the likelihood calculation:
```
P(E | H) = Π P(E_i | H)
```
Multiplication in log space holds up numerically; the floor at `max(LOG_LIKELIHOOD_FLOOR, ε)` keeps the exponentiation from underflowing.

The scorer uses an affine baseline `0.05 + 0.85 × value` before applying type-specific boosts. Even zero evidence maintains a non-zero likelihood, allowing the posterior to stay defined; the penalty factor from `EvidenceMetrics` reduces the confidence for bad payloads. We cap the final likelihood at 0.95 as perfect certainty is unrealistic.

`P(E|¬H)` follows the quadratic tail `0.01 + 0.49 × (1 − L)²`. That curve keeps the wrong-format probability between 0.01 and 0.50. TODO: run a quality fitness check against the learned parameters in `shared_config.py` and swap in the learned mode once calibration is complete.

## What Changed in 0.1.2

- Evidence flows through `IndependentBayesianScorer.calculate_likelihood` instead of a weighted sum. The implementation is derived within `src/importobot/medallion/bronze/independent_bayesian_scorer.py`.
- We restored multi-class normalization using the full denominator `Σ_j P(E|H_j) P(H_j)` instead of forcing an inaccurate per-format complement implementation.
- Regression coverage now includes monotonicity and ratio-cap tests (see `tests/unit/medallion/bronze/test_independent_bayesian_scorer.py` once the new assertions are integrated).

## Open Questions

- Completeness and quality are tightly coupled. We still need correlation stats from real imports to prove the independence assumption is reasonable enough. **TODO:** capture the covariance matrix from production telemetry before the 0.2 release.
- Amplification thresholds (0.8 and 0.9) were tuned against a single fixture batch. If we add new indicators, retune the constants or switch to per-format scaling.
- Learned `P(E|¬H)` numbers are half-baked; the “learned” mode simply filters `None`. We should finish that work or delete the toggle.

## Where to Look Next

- Design fallout and future experiments: `wiki/Bayesian-Redesign.md`
- Benchmark data: `wiki/benchmarks/format_detection_benchmark.json`
- Implementation details and guard rails: `src/importobot/medallion/bronze/independent_bayesian_scorer.py`
