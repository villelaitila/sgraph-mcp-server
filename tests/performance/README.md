# Performance Tests

This directory contains performance tests for the SGraph MCP Server to ensure that search operations meet performance requirements.

## Test Files

- `test_search_performance.py` - Tests the performance of `sgraph_search_elements_by_name`
- `test_all_search_performance.py` - Search by name, type and attributes
- `test_bulk_analysis_performance.py` - Subtree and dependency-chain analysis
- `test_overview_performance.py` - `OverviewService.get_model_overview` across depths
- `test_model_overview_performance.py` - Overview service and scalability with depth
- `__init__.py` - Package initialization file

## Running Tests

These are ordinary pytest tests - there is no separate runner to register them with.

### Run All Performance Tests

```bash
uv run python tests/run_all_tests.py performance
# or directly:
uv run python -m pytest tests/performance/ -v
```

### Run a Single Test

```bash
uv run python -m pytest tests/performance/test_search_performance.py -v -s
```

`-s` shows the per-measurement output, which is where the timings are reported.

Both models used here (`tests/sgraph-and-mcp.xml.zip` and
`sgraph-example-models/langchain.xml.zip`) are committed, so these run anywhere.
They are **not** part of CI, which runs only `tests/unit/` and `tests/integration/`.

## Test Details

### Search Performance Test

**Test**: `test_search_performance.py`

**Purpose**: Verify that `sgraph_search_elements_by_name` can efficiently search large models.

**Test Case**:
- **Model**: `langchain.xml.zip` (large real-world codebase)
- **Target Element**: `ConstitutionalPrinciple` (class)
- **Expected Path**: `/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai/models.py/ConstitutionalPrinciple`
- **Performance Requirement**: Search must complete within 100ms
- **Correctness Requirement**: Must find the target element correctly

**Typical Results**:
- Model Loading: ~700-800ms (one-time cost)
- Search Duration: ~11ms (well under 100ms limit)
- Elements Found: 1 (the target ConstitutionalPrinciple class)

## Performance Benchmarks

| Operation | Duration | Requirement | Status |
|-----------|----------|-------------|--------|
| Model Loading | ~750ms | N/A (one-time) | ✅ |
| Name Search | ~11ms | < 100ms | ✅ |

## Adding New Tests

To add a new performance test:

1. Create a new test function in the appropriate test file
2. Follow the naming convention: `test_<operation>_performance`
3. Include both performance and correctness assertions - a timing bound alone
   passes happily while the code under test returns nothing
4. Update this README with test details

pytest collects the file automatically; nothing needs registering.

## Test Data

The tests use the `langchain.xml.zip` model located in `sgraph-example-models/`. This model contains:
- Real-world Python codebase structure
- Thousands of elements across multiple files
- Complex dependency relationships
- Representative of typical large software projects

This makes it ideal for performance testing as it reflects real-world usage scenarios.
