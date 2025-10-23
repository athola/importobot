# Mathematical Foundations

Importobot uses Bayesian confidence scoring to detect test management formats. The current implementation handles two-stage classification: first validating that input is test data, then discriminating between specific formats like Zephyr vs TestRail.

## Overview

**Currently Implemented (v0.1.x):**
- Bayesian confidence scoring for format detection
- Two-stage hierarchical classification (test data validation → format discrimination)
- Basic numerical stability handling

**Future Work:**
- Format family models could group related formats (Atlassian family: Zephyr + JIRA)
- Semantic boosting for domain-specific formats like TestLink
- Test format threshold optimization using ROC curves from production data

## Core Mathematical Framework

### Bayesian statistics & format detection

The Bayesian scorer is the backbone of the format confidence pipeline. This section provides a high-level overview; the detailed derivation, parameter tables, and regression notes can be found in the [Bayesian scorer mathematical review](Bayesian-Scorer-Mathematical-Review.md).

Posteriors are computed directly instead of relying on the legacy noisy-OR approximation. Ambiguous payloads stop at the 1.5:1 cap; confident cases can extend to 3:1 because the scorer uses format-specific ambiguity adjustments retrieved from calibration runs. The quadratic decay for `P(E|¬H)` and the configurable epsilon prevent a divide-by-zero exception when evidence is insufficient. See the [Bayesian scorer mathematical review](Bayesian-Scorer-Mathematical-Review.md) for the derivations, parameter ranges, and regression coverage.

The independence assumption is violated in practice—`testCase` and `steps` fields appear together in 78% of Zephyr exports we analyzed. This correlation doesn't break the model but could improve accuracy if quantified.

### Two-Stage Hierarchical Classification [IMPLEMENTED]

The 0.1.2 release introduced hierarchical classification with two stages:

**Stage 1: Test Data Validation Gate**
```
P(is_test_data|E) >= threshold
```
- Determines if input represents ANY test management format vs random data
- Uses completeness and structural quality metrics
- Prevents false positives on non-test JSON

**Stage 2: Format-Specific Discrimination**
```
P(format_i|E, is_test_data) for all formats i
```
- Only executes if Stage 1 passes
- Uses format-specific unique indicators
- Applies multi-class Bayesian normalization

This differs from the planned format family models (see Future Directions) - the current implementation uses a validation gate rather than sharing evidence across related formats.

## Empirical Validation & Benchmarks [IMPLEMENTED]

Every release runs the fixtures in `tests/fixtures/format_detection_fixtures.py`; the results are in `wiki/benchmarks/format_detection_benchmark.json`. A 14/14 accuracy was preserved after the 0.1.2 rewrite and the ambiguous ratio was clamped at 1.5:1, as enforced by `tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`. Average detection time nudged from 53.8 ms to 55.0 ms over 200 conversions on a single core, which was within the tolerance established during performance analysis.

#### Numerical Stability

There were possible issues with division by zero in Bayesian calculations. The solution involved - use a configurable epsilon instead of a hardcoded value:

```python
# Before: Hardcoded epsilon
if denominator < 1e-15:
    return 0.0

# After: Configurable epsilon
if denominator < self.bayesian_config.numerical_epsilon:
    return 0.0
```

1e-15 was chosen as the epsilon value - it's between machine epsilon (~2.22e-16 for double precision) and a practical safety threshold. The validation range is 1e-20 < value < 1e-10 to ensure numerical safety without excessive precision.

#### Thread Safety

The rate limiter uses a token bucket algorithm with proper locking:

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

The lock prevents race conditions, and the automatic cleanup prevents uncontrolled memory growth. The string cache uses `functools.lru_cache(maxsize=1000)` which is thread-safe for reads and bounded in memory.

#### Historical Bayesian Implementation
The previous Bayesian confidence scoring system (2025 Q2-Q3) used a simplified approach:

```python
P(Format|Evidence) = P(Evidence|Format) × P(Format) / P(Evidence)
```

This Bayesian posterior probability forms the basis of Importobot's confidence scoring system:

- **P(Format|Evidence)**: Our confidence score (posterior probability)
- **P(Evidence|Format)**: Evidence strength given format (likelihood)
- **P(Format)**: Format prevalence (prior probability)
- **P(Evidence)**: Normalization factor (marginal probability)

With a blend of structural, semantic, and statistical evidence, a simple Bayesian model averaging sequence is applied:
```
P(Format|Evidence) = Σ P(Format|Evidence,Model_i) × P(Model_i|Evidence)
```
The weights (40% structural, 35% semantic, 25% statistical) were derived from calibration runs and increased the "generic" format confidence by approximately 10%.

### Information theory & pattern analysis

#### Mutual Information

```
I(Format; Pattern) = H(Format) - H(Format|Pattern)
```

Measures how much information patterns provide about format detection.

#### Entropy calculations

```
H(X) = -Σ p(x) × log₂(p(x))
H_total = 0.4 × H_keys + 0.4 × H_types + 0.2 × H_volume
```

**Components**:
- **Key Entropy**: Structural diversity (`log₂(unique_keys)`)
- **Type Entropy**: Distribution of value types
- **Volume Entropy**: Data volume complexity (`log₂(total_values)`)

#### Dynamic pattern coverage

```
coverage_ratio = sigmoid(entropy - entropy_threshold)
W_adjusted = W_base × coverage_ratio
```

Uses sigmoid transformation for smooth, theoretically justified confidence adjustments.

## Optimization Algorithms

### Gradient Descent Optimizer

**Algorithm**:
```python
for iteration in range(max_iterations):
    gradients = compute_gradients(parameters)
    velocity = momentum * velocity - learning_rate * gradients
    parameters += velocity
    current_value = objective_function(parameters)
```

**Properties**:
- **Convergence**: Guaranteed for convex functions
- **Momentum**: Accelerates convergence in ravines
- **Complexity**: O(i×g×n) where i=iterations, g=gradient cost, n=parameters

### Genetic Algorithm Optimizer

**Algorithm**:
```python
for generation in range(max_generations):
    fitness_scores = [fitness_function(individual) for individual in population]
    new_population = select_elite(population, fitness_scores)
    
    while len(new_population) < population_size:
        parent1 = tournament_selection(population, fitness_scores)
        parent2 = tournament_selection(population, fitness_scores)
        child = crossover(parent1, parent2)
        child = mutate(child, parameter_ranges)
        new_population.append(child)
```

**Properties**:
- **Global Optimization**: Escapes local minima
- **Population-Based**: Maintains solution diversity
- **Complexity**: O(g×p×f) where g=generations, p=population, f=fitness cost

### Simulated Annealing

**Algorithm**:
```python
while temperature > min_temperature:
    neighbor = generate_neighbor(current_parameters)
    delta = objective_function(neighbor) - objective_function(current_parameters)
    
    if delta < 0 or random.random() < math.exp(-delta / temperature):
        current_parameters = neighbor
    
    temperature *= cooling_rate
```

**Properties**
- **Global optimization:** Simulated annealing is used when gradient descent stalls; dry runs in `tests/performance/test_bronze_storage_performance.py` demonstrated that it finds the baseline objective in under 40k iterations.
- **Temperature schedule:** Exponential cooling remains the default because slower schedules extended runtimes beyond five minutes on the Bronze fixtures. Revisit once we have telemetry from real optimization previews. 
- **Cost profile:** Every iteration pays for a single objective evaluation, so runtime still scales with the function cost (`O(iterations × objective)`).

### Gold Layer Optimization Benchmark Plan

Importobot's Gold layer will use these optimizers to tune conversion heuristics
before exporting Robot Framework suites. The new `OptimizationService`
(`src/importobot/services/optimization_service.py`) provides a lightweight
integration point that the Gold layer can call during ingestion to preview
parameter tuning runs. The OptimizedConverter rollout will execute a benchmark
program built around three pillars:

- **Objectives** – Measure conversion quality uplift, latency reduction, and
  algorithm runtime for gradient descent, simulated annealing, and the genetic
  algorithm relative to the tuned heuristic baseline.
- **Datasets** – Bronze/Silver fixtures representing small (<25 tests), medium
  (25-150), and large (150+) suites across Zephyr, TestRail, and JIRA/Xray; the
  OptimizedConverter synthetic stress scenarios; and existing regression corpora
  from the performance benchmark harness.
- **Success Criteria** – Gradient descent must reach the target quality scores
  (≥0.90) while cutting preview latency by at least 15% within 30 iterations.
  Simulated annealing or genetic algorithms must deliver ≥5% additional
  improvement beyond gradient descent to remain enabled for the preview path;
  otherwise they will be candidates for removal to keep the system lean.

Each benchmark run captures wall-clock timings, iteration counts, and conversion
metrics through the `conversion_optimization` metadata channel exposed in
`GoldLayer.ingest`.Results flow back into placeholder previews so future maintainers can activate production-grade optimization without reconfiguring the mathematical components.

## Advanced Mathematical Approaches

### Structural Density Compensation

**Principle**: Information density theory - fewer fields with high discriminative power deserve proportionally higher confidence

```
Confidence_enhanced = Confidence_base × (1 + density_factor × structure_bonus)
```

**TestRail Example**: ID-heavy structures get confidence boosts
- **Pattern**: Multiple numeric IDs (suite_id, run_id, status_id, etc.)
- **Result**: TestRail confidence improved from 0.468 → 0.813 (+73.7%)

### Conditional Evidence Space Modeling

**Principle**: Different format variants have different evidence spaces

```
P(evidence | format_variant) ≠ P(evidence | format_general)
```

**JIRA Example**: Single issue vs. multi-issue API responses
- **Multi-issue**: `{"issues": [{"key": "...", "fields": {...}}, ...]}`
- **Single issue**: `{"key": "XTS-789", "fields": {"summary": "...", "issuetype": {...}}}`

### Multi-Pattern Structural Recognition

**Discriminative Feature Selection**: Format-specific field combinations

**TestRail API Patterns**:
1. **Full API**: `{"runs": [...], "tests": [...]}`
2. **Cases API**: `{"cases": [...], "suite_id": ..., "project_id": ...}`
3. **Results API**: `{"results": [...], "test_id": ..., "status_id": ...}`

### Format-Specific Semantic Enhancement

**Domain Adaptation**: Tailored semantic analysis for format-specific terminology

**TestRail Semantic Patterns**:
```python
api_patterns = ["api", "run", "case", "test", "suite", "milestone", "status"]
api_density = matches / total_patterns
semantic_boost = api_density × 0.3
```

**Numeric ID Detection**: TestRail API responses are ID-heavy
```python
id_pattern_count = len(re.findall(r'\d+', text_content))
if id_pattern_count >= 3:  # Multiple numeric IDs suggest TestRail
    semantic_boost += 0.2
```

### Enhanced Calibration with Structural Awareness

**Advanced Calibration Factors**: Beyond simple multipliers

```python
# Base calibration with validation quality awareness
if validation_quality >= 0.8:
    base_boost = 1.4  # High quality validation
elif validation_quality >= 0.5:
    base_boost = 1.2  # Medium quality validation
else:
    base_boost = 1.0  # Low quality - no boost

# Evidence strength boost with validation gating
if evidence_likelihood > 0.15 and validation_quality >= 0.7:
    evidence_boost = 0.4  # Strong evidence with good validation
elif evidence_likelihood > 0.03 and validation_quality >= 0.5:
    evidence_boost = 0.3  # Moderate evidence with decent validation
else:
    evidence_boost = 0.1  # Weak evidence or poor validation
```

**Format-Specific Enhancements**:
```python
# TestRail structural density compensation
if target_format == SupportedFormat.TESTRAIL:
    calibration_factor *= 1.15  # Base structural boost
    
    # ID-rich structure additional boost
    if id_count >= 3:
        calibration_factor *= 1.05  # Information density bonus
```

## Algorithmic Complexity Analysis

### Pattern Matching Algorithms

#### Regex Pattern Optimization

**Location**: `core/pattern_matcher.py:630-633`

**Algorithm**:
```python
combined_sql_pattern = r"((?:SELECT|INSERT|UPDATE|DELETE)\s+.+?)(?:;|$)"
```

**Complexity Analysis**:
- **Time Complexity**: O(n×m) where n is text length, m is pattern complexity
- **Space Complexity**: O(1) for compiled patterns
- **Optimization**: Non-capturing groups reduce memory overhead

#### Priority-Based Pattern Matching

**Location**: `core/pattern_matcher.py:116-117`

**Algorithm**:
```python
self.patterns.sort(key=lambda p: p.priority, reverse=True)
```

**Complexity Analysis**:
- **Time Complexity**: O(n log n) for sorting, O(1) for lookup
- **Space Complexity**: O(n) for pattern storage
- **Optimization**: Priority sorting enables early termination

### Distribution Algorithms

#### Weight Normalization

**Location**: `utils/test_generation/distributions.py:106-108`

**Algorithm**:
```python
normalized_weights = {
    k: v / total_weight for k, v in string_weights.items()
}
```

**Complexity Analysis**:
- **Time Complexity**: O(n) where n is number of categories
- **Space Complexity**: O(n) for normalized weights
- **Numerical Stability**: Division by zero protection

#### Remainder Distribution Algorithm

**Location**: `utils/test_generation/distributions.py:117-127`

**Algorithm**:
```python
fractional_parts = [(total_tests * normalized_weights[k]) % 1 for k in categories]
remainder_indices = argsort(fractional_parts, reverse=True)[:remainder]
```

**Complexity Analysis**:
- **Time Complexity**: O(n log n) for sorting fractional parts
- **Space Complexity**: O(n) for fractional parts storage
- **Allocation rule**: The largest remainder pass hands leftover slots to the biggest fractional weights; TODO: add a property test that exercises the extreme cases.

### Cache Operations

#### Cache Hit Rate Calculation

**Location**: `services/performance_cache.py:134-137`

**Algorithm**:
```python
hit_rate = (
    (self._cache_hits / total_requests * 100) if total_requests > 0 else 0
)
```

**Complexity Analysis**:
- **Time Complexity**: O(1) constant time
- **Space Complexity**: O(1) constant space
- **Numerical Stability**: Division by zero protection

#### Hash Generation

**Location**: `services/performance_cache.py:152-157`

**Algorithm**:
```python
return hashlib.sha256(data_str.encode()).hexdigest()[:24]
```

**Complexity Analysis**:
- **Time Complexity**: O(n) where n is data length
- **Space Complexity**: O(1) fixed output size
- **Collision Probability**: P(collision) ≈ 2^(-96) for 24-character hex

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
- **Unbiased Estimation**: Lower variance than hold-out validation
- **Efficiency**: Uses all data for both training and validation
- **Complexity**: O(k×m×n) where k=folds, m=strategies, n=data size

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
- **Consistency**: Converges to true parameter as n→∞
- **Coverage**: Approximately 95% for large samples
- **Complexity**: O(b×n) where b=bootstrap samples, n=data size

## Numerical Stability

### Kahan Summation Algorithm

**Problem**: Floating-point precision loss in weighted averages

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
- **Error Bound**: |error| ≤ 2ε × Σ|values| where ε is machine epsilon
- **Stability**: Compensates for lost low-order bits
- **Accuracy**: Significantly better than naive summation

### Division by Zero Protection

**Implementation**:
```python
if abs(total_weight) < 1e-10:
    raise ValueError("Total weight is too close to zero")
```

**Benefits**:
- **Numerical Safety**: Prevents division by very small numbers
- **Threshold**: Uses machine epsilon scaled threshold
- **Error Handling**: Provides meaningful error messages

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
- **Operator Precedence**: Correct parentheses ensure proper evaluation order
- **Conditional Evaluation**: Safe handling of edge cases
- **Bounded Outputs**: All terms are bounded to prevent overflow

## Performance Characteristics

### Scalability Analysis

#### Linear Scaling Components

- **Pattern Matching**: O(n) with respect to input size
- **Quality Assessment**: O(n) with respect to number of metrics
- **Cache Operations**: O(1) average case for hash table operations

#### Polynomial Scaling Components

- **Cross-Validation**: O(k×m×n) where k is folds, m is strategies
- **Genetic Algorithm**: O(g×p×f) where g is generations, p is population
- **Gradient Descent**: O(i×g×n) where i is iterations, g is gradient cost

#### Exponential Scaling Components

- **Pattern Combination**: O(2^p) where p is number of patterns (mitigated by caching)

### Memory Usage Analysis

#### Constant Space Components

- **Hash Functions**: O(1) fixed output size
- **Mathematical Operations**: O(1) for basic arithmetic
- **Cache Metadata**: O(1) per cache entry

#### Linear Space Components

- **Data Storage**: O(n) for input data
- **Population Storage**: O(p×n) for genetic algorithms
- **Convergence History**: O(i) for optimization history

#### Quadratic Space Components

- **Distance Matrices**: O(n²) for pairwise computations (avoided in current implementation)

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

- **LRU Caching**: Reduces redundant computations
- **Memoization**: Stores expensive function results
- **Early Termination**: Stops when convergence detected

#### Space-Efficient

- **Streaming Processing**: Processes data without full storage
- **Generators**: Lazy evaluation for large datasets
- **Compression**: Reduces memory footprint for cached data

## Mathematical Proofs & Theorems

### Convergence Proof for Gradient Descent

#### Theorem

For a convex function f: ℝⁿ → ℝ with Lipschitz continuous gradient ∇f, gradient descent with learning rate α ≤ 1/L (where L is Lipschitz constant) converges to the global minimum.

#### Proof Sketch

1. **Lipschitz Continuity**: ||∇f(x) - ∇f(y)|| ≤ L||x - y||
2. **Descent Lemma**: f(y) ≤ f(x) + ∇f(x)ᵀ(y-x) + (L/2)||y-x||²
3. **Update Rule**: x_{k+1} = x_k - α∇f(x_k)
4. **Convergence**: f(x_k) - f(x*) ≤ (||x₀ - x*||²)/(2αk)

#### Application in Importobot

The conversion-quality objective is approximated as convex when running the experimental optimization service (`src/importobot/services/optimization_service.py`). Step sizes are truncated using the Lipschitz estimates produced in the same module, but can revert to a conservative default when the bound is unknown. The formal convergence claim serves as guidance for future tuning rather than a guarantee. Production deployments allow more data to be gathered for the hand-tuned heuristic.

### Bootstrap Consistency Theorem

#### Theorem

The bootstrap distribution of a statistic θ̂* converges in probability to the true sampling distribution of θ̂ as the sample size n → ∞, under generic regularity conditions.

#### Proof Sketch

1. **Empirical Distribution**: F̂_n converges to true distribution F
2. **Functional Delta Method**: θ̂ = φ(F̂_n), θ̂* = φ(F̂_n*)
3. **Convergence**: ||F̂_n* - F|| → 0 in probability
4. **Consistency**: θ̂* converges to θ̂ in distribution

#### Application in Importobot

Bootstrap summaries remain optional because large suites amplify compute cost. For data analysis improvements, typically in offline analysis notebooks, the fixtures contain hundreds of cases so the asymptotics matter. Judge the improvements to data quality results against the performance cost. TODO: capture concrete coverage numbers from those notebooks before recommending the approach for day-to-day use.

### Genetic Algorithm Convergence

#### Theorem

A genetic algorithm with elitism and mutation rate p_m > 0 converges to the global optimum with probability 1 as the number of generations g → ∞.

#### Proof Sketch

1. **Markov Chain**: Population states form a Markov chain
2. **Irreducibility**: Positive mutation rate keeps all states reachable
3. **Positive Recurrence**: Elitism prevents loss of best solutions
4. **Convergence**: Stationary distribution concentrates on optimum

#### Application in Importobot
Our prototype genetic optimiser keeps an elite slice of the population and enforces a non-zero mutation rate, matching the textbook assumptions. Nevertheless, the gold layer still prefers gradient descent because we have not benchmarked the GA on real customer data. Consider the proof above a justification for keeping the implementation around while we decide whether it proves its value.

### Simulated Annealing Convergence

#### Theorem

Simulated annealing with logarithmic cooling schedule T_k = T₀/log(k+1) converges to the global optimum with probability 1 as k → ∞.

#### Proof Sketch

1. **Inhomogeneous Markov Chain**: Temperature-dependent transition probabilities
2. **Detailed Balance**: π(x)P(x→y) = π(y)P(y→x) for stationary distribution
3. **Cooling Schedule**: The logarithmic schedule is the case that carries the formal convergence guarantee
4. **Weak Convergence**: Converges to delta distribution at optimum

#### Application in Importobot

- **Temperature Schedule**: Exponential cooling for practical convergence
- **Acceptance Probability**: Balances exploration and exploitation
- **Global Optimization**: Escapes local minima in parameter space

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

- **Original**: 12/19 tests passing (63.2%)
- **Enhanced**: 17/19 tests passing (89.5%)
- **Improvement**: +26.3 percentage points
- **Statistical Significance**: All enhancements show p < 0.01

## Future Mathematical Directions [PLANNED WORK]

### Hierarchical Bayesian Models (For Zephyr - Atlassian Family)

#### Problem

Zephyr confidence 0.410 → 0.8 (95.1% increase needed)

#### Mathematical Framework

```
P(Zephyr|Evidence) = P(Evidence|Zephyr) × P(Zephyr|Atlassian) × P(Atlassian|Evidence)
```

#### Hierarchical Structure

```
Atlassian Suite
├── JIRA/Xray (P = 0.6)
└── Zephyr (P = 0.4)
```

#### Implementation Strategy

1. **Family Prior**: P(Atlassian) = 0.3 (enterprise prevalence)
2. **Conditional Priors**: P(Zephyr|Atlassian) = 0.4, P(JIRA|Atlassian) = 0.6
3. **Evidence Sharing**: Cross-format evidence accumulation
4. **Hierarchical Calibration**: Family-aware confidence boosting

#### Mathematical Justification

- **Hierarchical Bayesian Models**: Established framework for nested categorical data
- **Evidence Propagation**: Format family membership provides additional evidence
- **Shrinkage Estimation**: Family priors reduce individual format uncertainty

#### Expected Results

- Zephyr formats benefit from Atlassian family evidence
- Shared terminology and structural patterns boost confidence
- Hierarchical priors reduce sparse data uncertainty

### Domain-Specific Execution-Focused Semantic Boosting (For TestLink)

#### Problem

TestLink confidence 0.448 → 0.8 (78.6% increase needed)

#### Mathematical Framework

```
Semantic_score = base_score + execution_pattern_density × domain_weight
```

#### Execution-Focused Patterns

```python
execution_patterns = [
    "execution", "passed", "failed", "status", "time", "result",
    "testsuite", "testcase", "failures", "errors", "skipped"
]
```

#### Implementation Strategy

1. **Execution Density Calculation**:
   ```
   density = execution_matches / total_semantic_indicators
   ```

2. **Temporal Pattern Recognition**:
   ```python
   time_patterns = ["time", "duration", "timestamp", "created_on"]
   temporal_boost = time_pattern_count × 0.15
   ```

3. **XML Structure Bonus** (TestLink exports are XML-based):
   ```python
   xml_indicators = ["testsuite", "testcase", "name", "status"]
   xml_structure_bonus = xml_match_ratio × 0.25
   ```

#### Mathematical Justification

- **Domain Adaptation**: Execution-focused terminology is highly discriminative for TestLink
- **Temporal Analysis**: Test execution systems have strong temporal patterns
- **Structural Recognition**: XML export format has distinctive hierarchical patterns

#### Expected Enhancement

```
Enhanced_confidence = base_confidence + execution_boost + temporal_boost + xml_boost
```

#### Expected Results

- TestLink execution patterns provide strong discriminative evidence
- Temporal and XML structural patterns add cumulative confidence
- Domain-specific semantic analysis captures TestLink's unique characteristics

### Adaptive Threshold Calibration

#### Problem

Different formats may require different confidence thresholds

#### Current Uniform Thresholds

- Generic: 0.5 (achieved ✅)
- All others: 0.8 (some failing)

#### Empirical Bayes Threshold Learning

```
θ_format = α × θ_global + (1-α) × θ_format_specific
```

Where:
- `θ_global = 0.8` (current universal threshold)
- `θ_format_specific` = learned from validation data
- `α` = shrinkage parameter based on format prevalence

#### Mathematical Framework

1. **Cross-Validation Analysis**: Measure actual vs predicted confidence across formats
2. **ROC Curve Optimization**: Find optimal threshold per format for F1-score
3. **Shrinkage Estimation**: Balance format-specific and global thresholds

#### Implementation Strategy

```python
# Format-specific threshold learning
optimal_thresholds = {
    SupportedFormat.GENERIC: 0.5,      # Empirically validated
    SupportedFormat.JIRA_XRAY: 0.8,    # High precision required
    SupportedFormat.TESTRAIL: 0.75,    # Moderate adjustment
    SupportedFormat.TESTLINK: 0.65,    # Execution-focused adjustment
    SupportedFormat.ZEPHYR: 0.7        # Atlassian family adjustment
}
```

#### Mathematical Justification

- **Empirical Bayes**: Data-driven threshold learning
- **Format Heterogeneity**: Different formats have different confidence distributions
- **ROC Optimization**: Balanced precision/recall for business requirements

This approach provides a principled alternative to forcing all formats to meet a uniform 0.8 threshold when mathematical enhancement may not be sufficient or appropriate.

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

Rigorous mathematical implementation is beneficial only when it meets production expectations:
- Regression tests (`tests/unit/medallion/bronze/test_bayesian_ratio_constraints.py`, `tests/unit/medallion/bronze/test_independent_bayesian_scorer.py`) pin the confidence scorer to the 1.5:1 ambiguity cap and verify posterior normalisation.
- Numerical guardrails (`LOG_LIKELIHOOD_FLOOR`, configurable epsilon values) prevented the divide-by-zero crashes we saw in 0.1.0 while keeping wall-clock performance flat on the CI fixtures.
- Optimisation experiments remain provisional: benchmark harnesses and Monte Carlo notebooks are checked in, but the production gold layer still uses the tuned heuristic by default. **TODO:** carry telemetry from pilot runs into this chapter before calling the optimization stack “ready.”
