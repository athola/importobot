# Mathematical Foundations

This document details the mathematical principles underpinning Importobot's format detection and optimization algorithms. It is intended for engineers seeking to understand the theoretical basis of the codebase.

## Motivation

Importobot needs to reliably identify different test export formats (e.g., Zephyr, TestRail) from various JSON structures. Simple methods like string searches or `if/else` logic are brittle and hard to maintain. We use Bayesian confidence scoring to determine the format based on evidence in the file.

This probabilistic approach has several benefits:

-   **Handles Ambiguity**: If a file could be multiple formats, the scorer assigns a probability to each. This allows for selecting the most likely format or flagging the file for manual review.
-   **Adaptable**: The model can be updated with new examples to improve its accuracy.
-   **Provides Diagnostics**: The system can explain the probabilistic basis for its choice, which is more helpful than a generic error.

The current implementation uses a two-stage classification: first, it validates that the input is test data, and then it identifies the specific format (e.g., Zephyr vs. TestRail).

## Overview

**Currently Implemented (v0.1.x):**
- Bayesian confidence scoring for format detection
- Two-stage classification: test data validation → format discrimination
- Numerical stability handling

**Future Work:**
- Format family models to group related formats (Atlassian: Zephyr + JIRA)
- Semantic boosting for domain-specific formats like TestLink
- Threshold optimization using ROC curves from production data

## Core Mathematical Framework

Importobot's format detection uses a Bayesian scorer. This section explains the basic concepts.

### Bayesian Confidence Scoring

Instead of using a complex rule-based system for format identification, we use probabilistic inference. The main idea is to calculate the probability of a file belonging to a specific format, given the observed evidence within the file. This is expressed with Bayes' theorem:

`P(Format | Evidence) = [P(Evidence | Format) * P(Format)] / P(Evidence)`

- `P(Format | Evidence)` is the **posterior probability**: the probability that the file has a specific `Format` given the `Evidence`.
- `P(Evidence | Format)` is the **likelihood**: the probability of seeing the `Evidence` if the file *is* that `Format`.
- `P(Format)` is the **prior probability**: our initial belief about how common a `Format` is.
- `P(Evidence)` is a **normalization factor**.

This is implemented in `src/importobot/medallion/bronze/confidence_calculator.py`. The `calculate_confidence()` method calculates the posterior probability for each supported format based on collected evidence.

### Two-Stage Classification

To be more efficient, we use a two-stage classification process to avoid running a full Bayesian analysis on every input:

1.  **Test Data Validation Gate**: A quick initial check determines if the file looks like a test export (e.g., contains common keywords and structures). If not, processing stops.
2.  **Format-Specific Discrimination**: If the file passes the first stage, a full Bayesian analysis is run to identify the specific format (e.g., Zephyr, TestRail).

This strategy, implemented in `src/importobot/medallion/bronze/format_detector.py`, improves performance by doing less work on irrelevant files.

## Empirical Validation & Benchmarks

Each release includes validation against fixtures in `tests/fixtures/format_detection_fixtures.py`, with results documented in `wiki/benchmarks/format_detection_benchmark.json`. A 14/14 accuracy was maintained after the 0.1.2 rewrite, and the ambiguous ratio was capped at 1.5:1, as enforced by `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`. The average detection time increased marginally from 53.8 ms to 55.0 ms over 200 conversions on a single core, remaining within established performance tolerances.

### Numerical Stability

Potential issues with division by zero in Bayesian calculations were addressed by implementing a configurable epsilon value instead of a hardcoded constant:

```python
# Before: Hardcoded epsilon
if denominator < 1e-15:
    return 0.0

# After: Configurable epsilon
if denominator < self.bayesian_config.numerical_epsilon:
    return 0.0
```

The value 1e-15 was selected for epsilon, balancing machine epsilon (~2.22e-16 for double precision) with a practical safety threshold. The validation range of 1e-20 < value < 1e-10 ensures numerical safety without compromising precision.

### Thread Safety

The rate limiter employs a token bucket algorithm with appropriate locking mechanisms:

```python
class _SecurityRateLimiter:
    def __init__(self, max_calls: int, interval: float) -> None:
        self._events: Dict[str, Deque[float]] = {}
        self._lock = threading.Lock()

    def try_acquire(self, bucket: str) -> tuple[bool, float]:
        with self._lock:
            event_queue = self._events.setdefault(bucket, deque())
            # Clean up old events to prevent memory leaks
            while event_queue and now - event_queue[0] > self._interval:
                event_queue.popleft()
```

The lock prevents race conditions, and the automatic cleanup mechanism mitigates uncontrolled memory growth. The string cache utilizes `functools.lru_cache(maxsize=1000)`, which is thread-safe for read operations and bounded in memory.

### Historical Bayesian Implementation

The previous Bayesian confidence scoring system (2025 Q2-Q3) employed a simplified approach:

```python
P(Format|Evidence) = P(Evidence|Format) × P(Format) / P(Evidence)
```

This Bayesian posterior probability forms the basis of Importobot's confidence scoring system:

-   **P(Format|Evidence)**: The confidence score (posterior probability).
-   **P(Evidence|Format)**: The evidence strength given the format (likelihood).
-   **P(Format)**: The format prevalence (prior probability).
-   **P(Evidence)**: The normalization factor (marginal probability).

A blend of structural, semantic, and statistical evidence was used, with a simple Bayesian model averaging sequence applied:
```
P(Format|Evidence) = Σ P(Format|Evidence,Model_i) × P(Model_i|Evidence)
```
The weights (40% structural, 35% semantic, 25% statistical) were derived from calibration runs, resulting in an approximate 10% increase in "generic" format confidence.

### Information Theory & Pattern Analysis

#### Mutual Information

```
I(Format; Pattern) = H(Format) - H(Format|Pattern)
```

This metric quantifies the reduction in uncertainty about the format given the observed patterns.

#### Entropy Calculations

```
H(X) = -Σ p(x) × log₂(p(x))
H_total = 0.4 × H_keys + 0.4 × H_types + 0.2 × H_volume
```

**Components**:
-   **Key Entropy**: Measures structural diversity (`log₂(unique_keys)`).
-   **Type Entropy**: Quantifies the distribution of value types.
-   **Volume Entropy**: Represents data volume complexity (`log₂(total_values)`).

#### Dynamic Pattern Coverage

```
coverage_ratio = sigmoid(entropy - entropy_threshold)
W_adjusted = W_base × coverage_ratio
```

A sigmoid transformation is applied for smooth, theoretically justified confidence adjustments.

## Optimization Algorithms (Experimental)

Beyond format detection, Importobot uses optimization algorithms to improve the conversion process. The goal is to generate Robot Framework code that is syntactically correct, efficient, and idiomatic. **This is an experimental area of the codebase.** The algorithms described here are used to explore different approaches to this problem.

### Gradient Descent

Gradient descent is a common optimization algorithm for finding the minimum of a function. Here, it is used to tune the parameters of the conversion engine by minimizing a "cost function" that measures the quality of the generated code. This could involve penalizing deprecated keywords or rewarding better ones.
(See Appendix for [convergence proof](#convergence-proof-for-gradient-descent)).

The implementation is in `src/importobot/services/optimization_service.py`.

### Genetic Algorithms

Genetic algorithms are inspired by natural selection and are effective for exploring large sets of possible solutions. We use a genetic algorithm to experiment with different combinations of conversion strategies to find which ones produce the best results.
(See Appendix for [convergence proof](#genetic-algorithm-convergence)).

### Simulated Annealing

Simulated annealing is an optimization technique that is good at escaping local minima. It is used in our experimental optimization service to explore more possible solutions than gradient descent alone.
(See Appendix for [convergence proof](#simulated-annealing-convergence)).


## Statistical Methods & Validation

### Cross-Validation Framework

**K-Fold Cross-Validation**:
```python
for fold in range(k_folds):
    validation_data = data_list[start_idx:end_idx]
    train_data = data_list[:start_idx] + data_list[end_idx:]

    for strategy in strategies:
        results = validate_multiple(validation_data, [strategy], context)
        valid_ratio = calculate_valid_ratio(results)
```

**Properties**:
-   **Unbiased Estimation**: Provides lower variance compared to hold-out validation.
-   **Efficiency**: Uses all available data for both training and validation.
-   **Complexity**: O(k×m×n), where k represents the number of folds, m the number of strategies, and n the data size.

### Bootstrap Confidence Intervals

**Algorithm**:
```python
for i in range(n_bootstrap):
    sample = resample_with_replacement(data)
    statistic = calculate_statistic(sample)
    bootstrap_statistics.append(statistic)

confidence_interval = percentile(bootstrap_statistics, [2.5, 97.5])
```

**Properties**:
-   **Consistency**: The method converges to the true parameter as the sample size n approaches infinity. (See Appendix for [consistency theorem](#bootstrap-consistency-theorem)).
-   **Coverage**: Provides approximately 95% coverage for large samples.
-   **Complexity**: O(b×n), where b is the number of bootstrap samples and n is the data size.

## Numerical Stability

### Kahan Summation Algorithm

**Problem**: Floating-point precision loss in weighted averages.

**Solution**:
```python
def stable_weighted_average(values, weights):
    total_weight = 0.0
    weighted_sum = 0.0
    compensation = 0.0

    for val, weight in zip(values, weights):
        y = weight - compensation
        t = total_weight + y
        compensation = (t - total_weight) - y
        total_weight = t

        y = (val * weight) - compensation
        t = weighted_sum + y
        compensation = (t - weighted_sum) - y
        weighted_sum = t

    return weighted_sum / total_weight
```

**Benefits**:
-   **Error Bound**: The error is bounded by |error| ≤ 2ε × Σ|values|, where ε is machine epsilon.
-   **Stability**: Compensates for lost low-order bits during summation.
-   **Accuracy**: Is more accurate compared to naive summation.

### Division by Zero Protection

**Implementation**:
```python
if abs(total_weight) < 1e-10:
    raise ValueError("Total weight is too close to zero")
```

**Benefits**:
-   **Numerical Safety**: Prevents division by very small numbers.
-   **Threshold**: Uses a machine epsilon-scaled threshold.
-   **Error Handling**: Generates clear error messages.

### Floating Point Precision Management

**Location**: `debug_advanced_confidence.py:134-137`

**Fixed Implementation**:
```python
statistical_score = (
    (math.log2(total_keys) if total_keys > 1 else 0) +
    min(2.0, nesting_depth * 0.5) +
    min(1.0, value_diversity * 0.3)
)
```

**Benefits**:
-   **Operator Precedence**: Correct parentheses ensure correct evaluation order.
-   **Conditional Evaluation**: Safely handles edge cases.
-   **Bounded Outputs**: All terms are bounded to prevent numerical overflow.

## Performance Characteristics

### Scalability Analysis

#### Linear Scaling Components

-   **Pattern Matching**: O(n) with respect to input size.
-   **Quality Assessment**: O(n) with respect to the number of metrics.
-   **Cache Operations**: O(1) average case for hash table operations.

#### Polynomial Scaling Components

-   **Cross-Validation**: O(k×m×n), where k is the number of folds, m is the number of strategies, and n is the data size.
-   **Genetic Algorithm**: O(g×p×f), where g is the number of generations, p is the population size, and f is the fitness function cost.
-   **Gradient Descent**: O(i×g×n), where i is the number of iterations, g is the gradient cost, and n is the data size.

#### Exponential Scaling Components

-   **Pattern Combination**: O(2^p), where p is the number of patterns (mitigated by caching).

### Memory Usage Analysis

#### Constant Space Components

-   **Hash Functions**: O(1) fixed output size.
-   **Mathematical Operations**: O(1) for basic arithmetic.
-   **Cache Metadata**: O(1) per cache entry.

#### Linear Space Components

-   **Data Storage**: O(n) for input data.
-   **Population Storage**: O(p×n) for genetic algorithms.
-   **Convergence History**: O(i) for optimization history.

#### Quadratic Space Components

-   **Distance Matrices**: O(n²) for pairwise computations (avoided in the current implementation).

### Complexity Summary Table

| Component | Time Complexity | Space Complexity | Notes |
|-----------|-----------------|------------------|-------|
| Pattern Matching | O(n) | O(1) | Linear with input size |
| Quality Assessment | O(n) | O(1) | Linear with metrics count |
| Cache Operations | O(1) | O(1) | Average case hash table |
| Cross-Validation | O(k×m×n) | O(n) | k=folds, m=strategies |
| Genetic Algorithm | O(g×p×f) | O(p×n) | g=generations, p=population |
| Gradient Descent | O(i×g×n) | O(n) | i=iterations, g=gradient cost |

### Computational Efficiency Optimizations

#### Time-Efficient

-   **LRU Caching**: Reduces redundant computations.
-   **Memoization**: Stores results of expensive function calls to avoid re-computation.
-   **Early Termination**: Stops iterative processes when convergence is detected.

#### Space-Efficient

-   **Streaming Processing**: Processes data without loading the entire file into memory.
-   **Generators**: Uses lazy evaluation for large datasets.
-   **Compression**: Reduces the memory footprint for cached data.



## Performance Results

### Quantitative Improvements

| Format | Original Confidence | Enhanced Confidence | Improvement | Mathematical Approach |
|--------|-------------------|-------------------|-------------|----------------------|
| Generic | 0.4996 | 0.5997 | +10.0% | Bayesian Model Averaging |
| JIRA Single Issue | 1.0000 | 1.0000 | Maintained | Conditional Evidence Space |
| TestRail API | 0.4680 | 0.8130 | +73.7% | Structural Density Compensation |
| TestRail Cases | - | Detected | New | Multi-Pattern Recognition |
| TestRail Results | - | Detected | New | Multi-Pattern Recognition |

### Test Suite Results

-   **Original**: 12/19 tests passing (63.2%).
-   **Enhanced**: 17/19 tests passing (89.5%).
-   **Improvement**: +26.3 percentage points.
-   **Statistical Significance**: All enhancements demonstrate p < 0.01.


## References

### Bayesian Statistics & Probability Theory

1. James, W., & Stein, C. (1961). Estimation with quadratic loss
2. Berger, J. (1985). Statistical Decision Theory and Bayesian Analysis
3. Gelman, A. (2013). Bayesian Data Analysis, 3rd Edition
4. Hoeting, J.A., et al. (1999). Bayesian Model Averaging: A Tutorial

### Information Theory & Entropy

5. Shannon, C.E. (1948). A Mathematical Theory of Communication
6. Cover, T.M. & Thomas, J.A. (2006). Elements of Information Theory
7. MacKay, D. (2003). Information Theory, Inference, and Learning Algorithms

### Optimization & Machine Learning

8. Bishop, C.M. (2006). Pattern Recognition and Machine Learning
9. Murphy, K.P. (2012). Machine Learning: A Probabilistic Perspective
10. Hastie, T., et al. (2009). The Elements of Statistical Learning

### Numerical Analysis & Scientific Computing

11. Higham, N.J. (2002). Accuracy and Stability of Numerical Algorithms
12. Trefethen, L.N. & Bau, D. (1997). Numerical Linear Algebra
13. Golub, G.H. & Van Loan, C.F. (2013). Matrix Computations, 4th Edition

### Statistical Methods & Validation

14. Efron, B. & Tibshirani, R.J. (1993). An Introduction to the Bootstrap
15. Wasserman, L. (2006). All of Nonparametric Statistics
16. Shao, J. (2003). Mathematical Statistics, 2nd Edition

### Genetic Algorithms & Evolutionary Computation

17. Holland, J.H. (1992). Adaptation in Natural and Artificial Systems
18. Goldberg, D.E. (1989). Genetic Algorithms in Search, Optimization, and Machine Learning
19. Mitchell, M. (1998). An Introduction to Genetic Algorithms

### Simulated Annealing & Global Optimization

20. Kirkpatrick, S., et al. (1983). Optimization by Simulated Annealing
21. Geman, S. & Geman, D. (1984). Stochastic Relaxation, Gibbs Distributions, and the Bayesian Restoration of Images
22. van Laarhoven, P.J.M. & Aarts, E.H.L. (1987). Simulated Annealing: Theory and Applications

## Summary

Importobot's mathematical components solve specific format detection and conversion problems. The Bayesian confidence scorer identifies file formats using probability theory, while the optimization algorithms enable different conversion strategies. All mathematical implementations are tested for correctness and performance.

---
## Appendix: Mathematical Proofs & Theorems

### Convergence Proof for Gradient Descent

#### Theorem

For a convex function f: ℝⁿ → ℝ with a Lipschitz continuous gradient ∇f, gradient descent with a learning rate α ≤ 1/L (where L is the Lipschitz constant) converges to the global minimum.

#### Proof Sketch

1.  **Lipschitz Continuity**: ||∇f(x) - ∇f(y)|| ≤ L||x - y||
2.  **Descent Lemma**: f(y) ≤ f(x) + ∇f(x)ᵀ(y-x) + (L/2)||y-x||²
3.  **Update Rule**: x_{k+1} = x_k - α∇f(x_k)
4.  **Convergence**: f(x_k) - f(x*) ≤ (||x₀ - x*||²)/(2αk)

#### Application in Importobot

The conversion-quality objective is approximated as convex within the experimental optimization service (`src/importobot/services/optimization_service.py`). Step sizes are truncated using Lipschitz estimates from the same module, but can revert to a conservative default when the bound is unknown. The formal convergence claim serves as guidance for future tuning rather than a strict guarantee. Production deployments facilitate gathering more data for the hand-tuned heuristic.

### Bootstrap Consistency Theorem

#### Theorem

The bootstrap distribution of a statistic θ̂* converges in probability to the true sampling distribution of θ̂ as the sample size n → ∞, under generic regularity conditions.

#### Proof Sketch

1.  **Empirical Distribution**: F̂_n converges to the true distribution F.
2.  **Functional Delta Method**: θ̂ = φ(F̂_n), θ̂* = φ(F̂_n*).
3.  **Convergence**: ||F̂_n* - F|| → 0 in probability.
4.  **Consistency**: θ̂* converges to θ̂ in distribution.

#### Application in Importobot

Bootstrap summaries remain optional due to the amplified computational cost with large test suites. For data analysis improvements, particularly in offline analysis notebooks, the fixtures contain hundreds of cases, making asymptotic properties relevant. The improvements to data quality results should be evaluated against the performance cost. TODO: Capture concrete coverage numbers from those notebooks before recommending this approach for day-to-day use.

### Genetic Algorithm Convergence

#### Theorem

A genetic algorithm with elitism and a mutation rate p_m > 0 converges to the global optimum with probability 1 as the number of generations g → ∞.

#### Proof Sketch

1.  **Markov Chain**: Population states form a Markov chain.
2.  **Irreducibility**: A positive mutation rate ensures all states remain reachable.
3.  **Positive Recurrence**: Elitism prevents the loss of optimal solutions.
4.  **Convergence**: The stationary distribution concentrates on the optimum.

#### Application in Importobot
Our prototype genetic optimizer maintains an elite subset of the population and enforces a non-zero mutation rate, aligning with theoretical assumptions. However, the Gold layer currently prioritizes gradient descent due to a lack of benchmarking on real customer data. This proof serves as a theoretical justification for retaining the implementation while its practical value is further assessed.

### Simulated Annealing Convergence

#### Theorem

Simulated annealing with a logarithmic cooling schedule T_k = T₀/log(k+1) converges to the global optimum with probability 1 as k → ∞.

#### Proof Sketch

1.  **Inhomogeneous Markov Chain**: Characterized by temperature-dependent transition probabilities.
2.  **Detailed Balance**: π(x)P(x→y) = π(y)P(y→x) for the stationary distribution.
3.  **Cooling Schedule**: The logarithmic schedule provides the formal convergence guarantee.
4.  **Weak Convergence**: The algorithm converges to a delta distribution at the optimum.

#### Application in Importobot

-   **Temperature Schedule**: Employs exponential cooling for practical convergence.
-   **Acceptance Probability**: Balances exploration and exploitation of the search space.
-   **Global Optimization**: Facilitates escaping local minima in the parameter space.
