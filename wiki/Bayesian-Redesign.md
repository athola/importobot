# Mathematical Bayesian Redesign for Format Detection

## Problem Analysis

The current system is failing because of a **mathematical design flaw**, not parameter tuning issues.

### Root Cause Evidence
1. **JIRA_XRAY format has unique indicators**: `testExecutions` (UNIQUE weight 5), `xrayInfo` (STRONG weight 3)
2. **Other formats have only generic indicators**: ZEPHYR has `executionId`, `version` (STRONG weight 3 each)
3. **Yet likelihood ratios are only 1.69:1**, far below the required 2.0:1

This indicates that **the Bayesian scoring function is not properly weighting unique evidence**.

## Mathematical Foundation

### Current (Flawed) Approach
```python
likelihood = w₁·completeness^p₁ + w₂·quality^p₂ + w₃·uniqueness^p₃ + interactions
```

**Problems:**
1. **Power functions compress high values**: 0.8^0.45 ≈ 0.8^0.5 ≈ 0.89
2. **Linear combination dilutes discriminative power**: 65% uniqueness still gets diluted by 35% other factors
3. **No proper probabilistic interpretation**: This is an ad-hoc scoring function, not a likelihood

## Mathematically Rigorous Solution

### Option 1: Proper Hierarchical Bayesian Model

#### Stage 1: Test Data Detection (Binary Classification)
```
P(is_test_data|evidence) = Bernoulli(θ)
θ ~ Beta(α, β)  # Prior on test data prevalence

P(evidence|is_test_data=True) = Multinomial(evidence_counts | λ_test)
P(evidence|is_test_data=False) = Multinomial(evidence_counts | λ_not_test)

Posterior: P(is_test_data|evidence) = f(evidence_counts, λ_test, λ_not_test, α, β)
```

#### Stage 2: Format Discrimination (Multi-class Classification)
```
P(format|evidence, is_test_data=True) = Categorical(π)
π ~ Dirichlet(α₁, α₂, ..., αₖ)  # Format priors

P(evidence|format=i) = Product over evidence_types:
  - Unique indicators: Bernoulli(p_unique_i)
  - Strong indicators: Bernoulli(p_strong_i)
  - Moderate indicators: Bernoulli(p_moderate_i)

Posterior: P(format=i|evidence) ∝ P(evidence|format=i) * P(format=i)
```

### Option 2: Information-Theoretic Approach

#### Mutual Information-Based Scoring
```
I(format; evidence) = Σ P(format,evidence) log(P(format,evidence) / (P(format)P(evidence)))

Discriminative power = KL(P(evidence|format) || P(evidence|other_formats))

Posterior probability derived from information gain
```

### Option 3: Logistic Regression with Feature Engineering

#### Multi-class Logistic Model
```
P(format=i|features) = softmax(Wᵢ · features + bᵢ)

Features = [
  unique_indicator_count,
  strong_indicator_count,
  moderate_indicator_count,
  field_specificity_score,
  structural_complexity,
  evidence_quality_score
]

Regularization: L1 for feature selection, L2 for stability
```

## Recommended Implementation

### Phase 1: Fix Current Bayesian Model

**Immediate fix using proper probability theory:**

1. **Evidence Independence Assumption**
```python
# Current: Arbitrary weighted combination
likelihood = w₁·C^p₁ + w₂·Q^p₂ + w₃·U^p₃

# Proper: Independent evidence multiplication
likelihood = P(completeness|evidence) * P(quality|evidence) * P(uniqueness|evidence)
```

2. **Log-Likelihood for Numerical Stability**
```python
log_likelihood = log(P(completeness|evidence)) + log(P(quality|evidence)) + log(P(uniqueness|evidence))
```

3. **Proper P(Evidence|Format) Models**
```python
# For unique indicators (presence/absence)
P(unique_present|format) = Beta(α_unique_present, β_unique_present)

# For count-based evidence
P(count|format) = Poisson(λ_count) or NegativeBinomial

# For quality scores
P(quality|format) = Beta(α_quality, β_quality)
```

### Phase 2: Implement Hierarchical Model

**Stage 1**: Test data detection using:
- Evidence count models (Poisson/NegativeBinomial)
- Structural quality assessment
- Field specificity scoring

**Stage 2**: Format discrimination with:
- Dirichlet priors on format frequencies
- Bernoulli/Beta models for indicator presence
- Logarithmic scaling for rare indicators

### Phase 3: Long-Term Exploration

1. **Hierarchical Bayesian modeling** with PyMC or NumPyro for full posterior inference.
2. **Mutual information feature selection** to identify the most discriminative indicators.
3. **Hybrid Bayesian + logistic regression** approach where Bayesian priors inform logistic regression features.

## Risks and Mitigations

1. **Data sparsity**: Some formats may lack sufficient training data. Mitigate with informative priors and synthetic augmentation.
2. **Model interpretability**: Keep explanations grounded in evidence metrics and publish derived parameters.
3. **Computational overhead**: Pre-compute format-specific parameters and cache likelihood components.

## Next Steps

1. Implement evidence independence in the current scorer.
2. Replace ad-hoc likelihoods with Beta/Bernoulli models per evidence type.
3. Establish benchmarking suite aligned with `wiki/benchmarks/format_detection_benchmark.json`.
