# Medallion Layer Interactions

This diagram illustrates how data flows through Importobot's medallion
architecture and supporting services.

```mermaid
flowchart TD
    ext["External Sources<br/>API, CLI, Connectors"]
    sec["SecurityGateway<br/>- XSS sanitization<br/>- DoS rate limiting"]
    bronze["Bronze Layer<br/>- Raw ingestion<br/>- Metadata capture<br/>- Lineage seeds"]
    silver["Silver Layer<br/>- Validation rules<br/>- Quality scoring<br/>- Normalization"]
    gold["Gold Layer<br/>- Optimization service<br/>- Export adapters<br/>- Final lineage"]
    targets["Target Systems<br/>Robot, Zephyr, TestRail, ..."]

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
