# Medallion Layer Interactions

This document illustrates the data flow through Importobot's Medallion architecture and its supporting services.

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

Supporting Notes:

-   `PerformanceCache` and `DetectionCache` accelerate detection and ingestion paths for both Bronze and Silver layers.
-   The optimization service utilizes outputs from the Bronze and Silver layers when simulating alternative exports in the Gold layer.
