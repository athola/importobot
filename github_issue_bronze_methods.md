# Implement Missing BronzeLayer Methods

## Issue Summary
Three BronzeLayer methods in `src/importobot/medallion/bronze_layer.py` are currently not implemented despite having the necessary infrastructure already in place.

## Current Status
The methods return placeholder values with misleading comments suggesting the layer "doesn't maintain persistent records," but the infrastructure for storage already exists.

## Methods to Implement

### 1. `get_record_metadata(record_id: str)` 🟢 Low Effort
**Current**: Returns `None`
**Required**: Lookup and convert from `self._metadata_store[record_id]`
**Effort**: 30-60 minutes

```python
def get_record_metadata(self, record_id: str) -> Optional[RecordMetadata]:
    layer_metadata = self._metadata_store.get(record_id)
    if layer_metadata:
        return RecordMetadata(
            source_system=layer_metadata.source_path,
            source_file_size=0,  # Could be enhanced later
        )
    return None
```

### 2. `get_record_lineage(record_id: str)` 🟢 Low Effort
**Current**: Returns `None`
**Required**: Lookup and convert from `self._lineage_store[record_id]`
**Effort**: 30-60 minutes

```python
def get_record_lineage(self, record_id: str) -> Optional[DataLineage]:
    lineage_info = self._lineage_store.get(record_id)
    if lineage_info:
        return DataLineage(
            source_id=lineage_info.source_id,
            source_type=lineage_info.source_type,
            source_location=lineage_info.source_location,
        )
    return None
```

### 3. `get_bronze_records(filter_criteria, limit)` 🟡 Medium Effort
**Current**: Returns `[]`
**Required**: Convert stored data to BronzeRecord format with filtering
**Effort**: 2-3 hours

```python
def get_bronze_records(
    self,
    filter_criteria: Optional[dict[str, Any]] = None,
    limit: Optional[int] = None,
) -> list[BronzeRecord]:
    records = []

    for data_id, data in self._data_store.items():
        metadata = self._metadata_store.get(data_id)
        lineage = self._lineage_store.get(data_id)

        if metadata and lineage:
            # Apply filtering if specified
            if filter_criteria and not self._matches_filter(data, metadata, filter_criteria):
                continue

            # Convert to BronzeRecord
            record = BronzeRecord(
                data=data,
                metadata=RecordMetadata(...),
                format_detection=FormatDetectionResult(...),
                lineage=DataLineage(...)
            )
            records.append(record)

            # Apply limit
            if limit and len(records) >= limit:
                break

    return records

def _matches_filter(self, data, metadata, filter_criteria):
    # Implement filtering logic based on criteria
    pass
```

## Evidence of Existing Infrastructure

The BronzeLayer `ingest()` method already stores data in three dictionaries:
- `self._data_store[data_id] = data` (line 72)
- `self._metadata_store[data_id] = metadata` (line 73)
- `self._lineage_store[data_id] = lineage` (line 74)

## Implementation Tasks

### Phase 1: Quick Wins (1-2 hours)
- [ ] Implement `get_record_metadata()`
- [ ] Implement `get_record_lineage()`
- [ ] Add unit tests for both methods
- [ ] Update misleading comments

### Phase 2: Records Retrieval (2-3 hours)
- [ ] Implement `get_bronze_records()` basic functionality
- [ ] Add filtering logic for common criteria
- [ ] Implement pagination/limit support
- [ ] Add comprehensive unit tests
- [ ] Add integration tests with actual bronze layer data

### Phase 3: Documentation & Cleanup (30 minutes)
- [ ] Update method docstrings to reflect actual functionality
- [ ] Update any external documentation mentioning these methods
- [ ] Verify API consistency with medallion architecture patterns

## Acceptance Criteria
- [ ] All three methods have proper implementations
- [ ] Methods return correct data types as specified in signatures
- [ ] Comprehensive test coverage (>90%)
- [ ] All tests pass including integration tests
- [ ] Lint score remains 10.00/10
- [ ] No breaking changes to existing functionality

## Total Effort Estimate
**3-5 hours** including tests and documentation

## Priority
**Medium** - These methods complete the BronzeLayer API and are needed for full medallion architecture functionality.

## Labels
- `enhancement`
- `medallion-architecture`
- `bronze-layer`
- `good-first-issue` (for phases 1-2)
- `documentation`

---

**Note**: This issue represents low-hanging fruit since all the infrastructure is already implemented. The main work is exposing the existing functionality through the proper API methods.