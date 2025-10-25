# Medallion Layer Interactions

This diagram illustrates how data flows through Importobot's medallion
architecture and supporting services.

```mermaid
flowchart TD
    ext["External Sources
    (API, CLI, Connectors)"]
    sec["SecurityGateway
    - XSS sanitization
    - DoS rate limiting"]
    bronze["Bronze Layer
    - Raw ingestion
    - Metadata capture
    - Lineage seeds"]
    silver["Silver Layer
    - Validation rules
    - Quality scoring
    - Normalization"]
    gold["Gold Layer
    - Optimization service
    - Export adapters
    - Final lineage"]
    targets["Target Systems
    (Robot, Zephyr, TestRail)"]

    ext --> sec --> bronze --> silver --> gold --> targets

    subgraph Shared Services
        perf[PerformanceCache]
        detect[DetectionCache]
    end
    perf -.-> bronze
    detect -.-> bronze
    detect -.-> silver

    opt[OptimizationService]
    opt -.-> gold
```

Supporting notes:

- `PerformanceCache` and `DetectionCache` accelerate detection and ingestion
  paths shared by Bronze/Silver layers.
- The optimization service consults Bronze/Silver outputs when simulating
  alternative exports in Gold.
