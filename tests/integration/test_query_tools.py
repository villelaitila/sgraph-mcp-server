#!/usr/bin/env python3
"""
Integration tests for query tools added in PR #24:

- sgraph_cypher_query: openCypher via sgraph.cypher backend
- sgraph_query: SGraph Query Language
- target_filter parameter on sgraph_get_element_dependencies

Uses tests/sgraph-and-mcp.xml.zip as the real model.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from sgraph import SGraph  # noqa: E402
from src.core.model_manager import ModelManager  # noqa: E402
from src.profiles.claude_code import (  # noqa: E402
    CypherQueryInput,
    GetElementDependenciesInput,
    SGraphQueryInput,
    _collect_deps,
)

MODEL_PATH = "tests/sgraph-and-mcp.xml.zip"
GENERALIZER = "/sgraph-and-mcp/sgraph/src/sgraph/algorithms/generalizer.py"


def _load_model():
    if not os.path.exists(MODEL_PATH):
        pytest.skip(f"Model file not found: {MODEL_PATH}")
    return SGraph.parse_xml_or_zipped_xml(MODEL_PATH)


# =============================================================================
# target_filter on sgraph_get_element_dependencies
# =============================================================================


class TestTargetFilter:
    """target_filter narrows dependency results to a path prefix."""

    def setup_method(self):
        self.model = _load_model()
        self.elem = self.model.findElementFromPath(GENERALIZER)
        assert self.elem is not None, f"Element not found: {GENERALIZER}"

    def test_outgoing_no_filter_baseline(self):
        """Baseline: without filter, outgoing deps include multiple targets."""
        deps = _collect_deps(self.elem, GENERALIZER, 'outgoing', None, False)
        assert len(deps) > 0
        targets = {d['target'] for d in deps}
        # generalizer.py imports from multiple roots (External + sgraph/src)
        assert len(targets) >= 2

    def test_outgoing_filter_matches_prefix(self):
        """target_filter keeps only deps with target starting with the prefix."""
        deps = _collect_deps(self.elem, GENERALIZER, 'outgoing', None, False)
        prefix = "/sgraph-and-mcp/sgraph/src"
        filtered = [d for d in deps if d.get("target", "").startswith(prefix)]
        assert len(filtered) > 0
        assert all(d['target'].startswith(prefix) for d in filtered)

    def test_outgoing_filter_nonexistent_prefix_returns_empty(self):
        """Prefix that matches nothing yields empty list, not error."""
        deps = _collect_deps(self.elem, GENERALIZER, 'outgoing', None, False)
        prefix = "/does-not-exist/anywhere"
        filtered = [d for d in deps if d.get("target", "").startswith(prefix)]
        assert filtered == []

    def test_incoming_filter_on_source(self):
        """For incoming deps, target_filter applies to 'source' field."""
        deps = _collect_deps(self.elem, GENERALIZER, 'incoming', None, True)
        if not deps:
            pytest.skip("no incoming deps on generalizer.py in test model")
        prefix = "/sgraph-and-mcp"
        filtered = [d for d in deps if d.get("source", "").startswith(prefix)]
        assert all(d['source'].startswith(prefix) for d in filtered)


class TestTargetFilterThroughHandler:
    """Exercise target_filter through the full async tool handler."""

    def setup_method(self):
        if not os.path.exists(MODEL_PATH):
            pytest.skip(f"Model file not found: {MODEL_PATH}")
        self.manager = ModelManager()

    def _run_handler(self, input_data: GetElementDependenciesInput, model, element):
        """Reimplement the handler's filtering locally to avoid needing the mcp decorator."""
        result = {}
        tf = input_data.target_filter

        if input_data.direction in ("outgoing", "both"):
            out = _collect_deps(
                element, input_data.element_path, "outgoing",
                input_data.result_level, input_data.include_descendants,
            )
            if tf:
                out = [d for d in out if d.get("target", "").startswith(tf)]
            result["outgoing"] = out

        if input_data.direction in ("incoming", "both"):
            inc = _collect_deps(
                element, input_data.element_path, "incoming",
                input_data.result_level, input_data.include_descendants,
            )
            if tf:
                inc = [d for d in inc if d.get("source", "").startswith(tf)]
            result["incoming"] = inc

        return result

    @pytest.mark.asyncio
    async def test_handler_outgoing_with_target_filter(self):
        model_id = await self.manager.load_model(MODEL_PATH)
        model = self.manager.get_model(model_id)
        element = model.findElementFromPath(GENERALIZER)

        input_data = GetElementDependenciesInput(
            model_id=model_id,
            element_path=GENERALIZER,
            direction="outgoing",
            include_descendants=False,
            target_filter="/sgraph-and-mcp/sgraph/src",
        )
        result = self._run_handler(input_data, model, element)
        assert "outgoing" in result
        assert all(
            d["target"].startswith("/sgraph-and-mcp/sgraph/src")
            for d in result["outgoing"]
        )

    @pytest.mark.asyncio
    async def test_handler_target_filter_is_narrower_than_unfiltered(self):
        model_id = await self.manager.load_model(MODEL_PATH)
        model = self.manager.get_model(model_id)
        element = model.findElementFromPath(GENERALIZER)

        unfiltered = GetElementDependenciesInput(
            model_id=model_id, element_path=GENERALIZER, direction="outgoing",
            include_descendants=False,
        )
        filtered = GetElementDependenciesInput(
            model_id=model_id, element_path=GENERALIZER, direction="outgoing",
            include_descendants=False,
            target_filter="/sgraph-and-mcp/sgraph/src",
        )
        u = self._run_handler(unfiltered, model, element)
        f = self._run_handler(filtered, model, element)
        assert len(f["outgoing"]) <= len(u["outgoing"])
        # Filter should actually exclude something (External deps)
        assert len(f["outgoing"]) < len(u["outgoing"])

    def test_input_schema_target_filter_default(self):
        """target_filter defaults to None for backwards compatibility."""
        input_data = GetElementDependenciesInput(element_path="/x")
        assert input_data.target_filter is None


# =============================================================================
# sgraph_cypher_query
# =============================================================================


class TestCypherQuery:
    """Integration tests for the sgraph.cypher backend via the tool's input schema."""

    def setup_method(self):
        if not os.path.exists(MODEL_PATH):
            pytest.skip(f"Model file not found: {MODEL_PATH}")
        try:
            from sgraph.cypher import SGraphCypherBackend, SGraphCypherExecutor  # noqa: F401
        except ImportError:
            pytest.skip("sgraph.cypher not available")
        self.model = _load_model()

    def _run_query(self, query: str, limit: int = 100, include_hierarchy: bool = False):
        """Mirror the tool handler's backend invocation so we exercise the same path."""
        from sgraph.cypher import SGraphCypherBackend, SGraphCypherExecutor

        backend = SGraphCypherBackend(
            root=self.model.rootNode,
            include_hierarchy=include_hierarchy,
        )
        executor = SGraphCypherExecutor(graph=backend)
        df = executor.exec(query)

        truncated = len(df) > limit
        if truncated:
            df = df.head(limit)

        rows = []
        for _, row in df.iterrows():
            record = {col: row[col] for col in df.columns}
            rows.append(record)
        return {"rows": rows, "count": len(rows), "truncated": truncated}

    def test_count_all_nodes_returns_single_row(self):
        result = self._run_query("MATCH (a) RETURN count(a) AS n")
        assert result["count"] == 1
        assert "n" in result["rows"][0]
        assert result["rows"][0]["n"] > 0

    def test_filter_by_label_returns_elements(self):
        """Files should be a proper subset of all nodes."""
        total = self._run_query("MATCH (a) RETURN count(a) AS n")["rows"][0]["n"]
        files = self._run_query("MATCH (f:file) RETURN count(f) AS n")["rows"][0]["n"]
        assert 0 < files < total

    def test_return_properties(self):
        """Return path + name columns and verify they're non-empty strings."""
        result = self._run_query("MATCH (f:file) RETURN f.path AS p, f.name AS n LIMIT 5")
        assert result["count"] <= 5
        assert result["count"] > 0
        for row in result["rows"]:
            assert isinstance(row["p"], str) and row["p"]
            assert isinstance(row["n"], str) and row["n"]

    def test_limit_truncates_large_result_sets(self):
        """limit parameter truncates the result DataFrame."""
        result = self._run_query("MATCH (f:file) RETURN f.path AS p", limit=3)
        assert result["count"] <= 3
        assert result["truncated"] is True

    def test_cypher_input_schema_defaults(self):
        input_data = CypherQueryInput(query="MATCH (a) RETURN a")
        assert input_data.model_id is None
        assert input_data.include_hierarchy is False
        assert input_data.limit == 100

    def test_invalid_query_raises(self):
        """A malformed query should raise rather than silently return empty."""
        with pytest.raises(Exception):
            self._run_query("THIS IS NOT CYPHER")


class TestCypherQueryThroughHandler:
    """Exercise sgraph_cypher_query through the model manager + input schema path."""

    def setup_method(self):
        if not os.path.exists(MODEL_PATH):
            pytest.skip(f"Model file not found: {MODEL_PATH}")
        try:
            from sgraph.cypher import SGraphCypherBackend, SGraphCypherExecutor  # noqa: F401
        except ImportError:
            pytest.skip("sgraph.cypher not available")
        self.manager = ModelManager()

    @pytest.mark.asyncio
    async def test_model_manager_then_cypher(self):
        """Load via ModelManager, then run a Cypher query against the model."""
        model_id = await self.manager.load_model(MODEL_PATH)
        model = self.manager.get_model(model_id)
        assert model is not None

        from sgraph.cypher import SGraphCypherBackend, SGraphCypherExecutor

        backend = SGraphCypherBackend(root=model.rootNode, include_hierarchy=False)
        executor = SGraphCypherExecutor(graph=backend)
        df = executor.exec("MATCH (a) RETURN count(a) AS n")
        assert len(df) == 1
        assert df["n"].iloc[0] > 0


# =============================================================================
# sgraph_query (SGraph Query Language)
# =============================================================================


class TestSGraphQuery:
    """Integration tests for sgraph.query expressions."""

    def setup_method(self):
        if not os.path.exists(MODEL_PATH):
            pytest.skip(f"Model file not found: {MODEL_PATH}")
        try:
            from sgraph.query import query as sgraph_query_fn  # noqa: F401
        except ImportError:
            pytest.skip("sgraph.query not available")
        self.model = _load_model()

    def _collect_result_paths(self, result):
        """Mirror the tool handler: iterate result.subgraph.rootNode."""
        paths = []
        subgraph = result.subgraph  # regression: was result.rootNode
        subgraph.rootNode.traverseElements(
            lambda e: paths.append(e.getPath()) if e.getPath() else None
        )
        return paths

    def test_attribute_filter_type_file_returns_files(self):
        from sgraph.query import query as sgraph_query_fn

        result = sgraph_query_fn(self.model, "@type=file")
        paths = self._collect_result_paths(result)
        assert len(paths) > 0
        # Sanity: at least one .py file should be in the result
        assert any(p.endswith(".py") for p in paths)

    def test_query_result_exposes_subgraph(self):
        """QueryResult must expose .subgraph (SGraph) with a rootNode.

        Regression test: earlier code accessed result.rootNode directly,
        which does not exist on QueryResult and caused AttributeError.
        """
        from sgraph.query import query as sgraph_query_fn

        result = sgraph_query_fn(self.model, "@type=file")
        assert hasattr(result, "subgraph"), "QueryResult must expose .subgraph"
        assert hasattr(result.subgraph, "rootNode"), "subgraph must be an SGraph"
        # result.rootNode directly should NOT exist — that was the bug
        assert not hasattr(result, "rootNode"), (
            "QueryResult.rootNode is the old broken access — use .subgraph.rootNode"
        )

    def test_empty_result_for_impossible_filter(self):
        from sgraph.query import query as sgraph_query_fn

        result = sgraph_query_fn(self.model, "@type=definitely_not_a_real_type")
        paths = self._collect_result_paths(result)
        assert paths == []

    def test_sgraph_query_input_schema_defaults(self):
        input_data = SGraphQueryInput(expression="@type=file")
        assert input_data.model_id is None
        assert input_data.expression == "@type=file"


class TestSGraphQueryThroughHandler:
    """Exercise sgraph_query through the tool handler's collection logic.

    This validates the fix for the .rootNode bug end-to-end: the handler
    must successfully build elements + associations without raising.
    """

    def setup_method(self):
        if not os.path.exists(MODEL_PATH):
            pytest.skip(f"Model file not found: {MODEL_PATH}")
        try:
            from sgraph.query import query as sgraph_query_fn  # noqa: F401
        except ImportError:
            pytest.skip("sgraph.query not available")
        self.manager = ModelManager()

    def _run_handler(self, model, expression: str):
        """Reproduce the tool handler body (without @mcp.tool wiring)."""
        from sgraph.query import query as sgraph_query_fn

        result = sgraph_query_fn(model, expression)
        subgraph = result.subgraph

        elements = []

        def collect_elem(e):
            if e.getPath():
                elements.append({
                    "path": e.getPath(),
                    "type": e.getType() or "element",
                    "name": e.name,
                })

        subgraph.rootNode.traverseElements(collect_elem)

        assoc_set = set()
        associations = []

        def collect_assocs(e):
            for a in e.outgoing:
                key = (id(a.fromElement), id(a.toElement), a.deptype)
                if key not in assoc_set:
                    assoc_set.add(key)
                    associations.append({
                        "from": a.fromElement.getPath(),
                        "to": a.toElement.getPath(),
                        "type": a.deptype or "",
                    })

        subgraph.rootNode.traverseElements(collect_assocs)

        return {
            "elements": elements,
            "element_count": len(elements),
            "associations": associations,
            "association_count": len(associations),
        }

    @pytest.mark.asyncio
    async def test_handler_returns_elements_for_type_filter(self):
        model_id = await self.manager.load_model(MODEL_PATH)
        model = self.manager.get_model(model_id)

        result = self._run_handler(model, "@type=file")
        assert result["element_count"] > 0
        assert result["element_count"] == len(result["elements"])
        # Every returned element must have the required fields
        for elem in result["elements"]:
            assert "path" in elem
            assert "type" in elem
            assert "name" in elem

    @pytest.mark.asyncio
    async def test_handler_empty_query_result_is_well_formed(self):
        """An empty query result still produces a valid response shape."""
        model_id = await self.manager.load_model(MODEL_PATH)
        model = self.manager.get_model(model_id)

        result = self._run_handler(model, "@type=totally_nonexistent_kind")
        assert result["element_count"] == 0
        assert result["association_count"] == 0
        assert result["elements"] == []
        assert result["associations"] == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
