#!/usr/bin/env python3
"""
Performance test for bulk analysis functions.

This test measures the performance of:
- sgraph_get_subtree_dependencies
- sgraph_get_dependency_chain
- sgraph_get_multiple_elements
"""


import pytest
import os
import sys
import time
from pathlib import Path

# Add project root to path to import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.model_manager import ModelManager
from src.services.dependency_service import DependencyService


@pytest.mark.asyncio
async def test_bulk_analysis_performance():
    """Test the performance of bulk analysis functions."""
    print("=== Bulk Analysis Performance Test ===")
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Path to the test model
    model_path = Path(__file__).parent.parent.parent / "sgraph-example-models" / "langchain.xml.zip"
    
    if not model_path.exists():
        pytest.fail(f"Test model not found at: {model_path}")
    
    print(f"📁 Loading model from: {model_path}")
    
    # Load the model and measure loading time
    load_start = time.perf_counter()
    try:
        model_id = await model_manager.load_model(str(model_path))
        load_end = time.perf_counter()
        load_duration = (load_end - load_start) * 1000  # Convert to milliseconds
        print(f"⏱️  Model loaded in: {load_duration:.2f} ms")
    except Exception as e:
        pytest.fail(f"Failed to load model: {e}")
    
    # Get the model for direct access
    model = model_manager.get_model(model_id)
    if model is None:
        pytest.fail("Failed to retrieve loaded model")
    
    print(f"📊 Model loaded successfully with ID: {model_id}")
    print()
    
    all_tests_passed = True
    
    # Test 1: Get subtree dependencies
    print("🌳 Test 1: Get Subtree Dependencies")
    print("-" * 40)
    
    # Test on the constitutional_ai directory
    subtree_path = "/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai"
    
    search_start = time.perf_counter()
    try:
        result = DependencyService.get_subtree_dependencies(
            model=model,
            root_path=subtree_path,
            include_external=True,
            max_depth=3
        )
        search_end = time.perf_counter()
        search_duration = (search_end - search_start) * 1000
        
        print(f"⏱️  Subtree dependencies: {search_duration:.2f} ms")
        print(f"📂 Subtree elements: {len(result['subtree_elements'])}")
        print(f"🔗 Internal deps: {len(result['internal_dependencies'])}")
        print(f"⬇️  Incoming deps: {len(result['incoming_dependencies'])}")
        print(f"⬆️  Outgoing deps: {len(result['outgoing_dependencies'])}")
        
        outside = [
            e['path'] for e in result['subtree_elements']
            if not e['path'].startswith(subtree_path)
        ]
        internal = result['internal_dependencies']
        
        if search_duration > 500:  # 500ms limit for subtree analysis
            print(f"❌ PERFORMANCE FAILURE: Analysis took {search_duration:.2f} ms, expected < 500 ms")
            all_tests_passed = False
        elif len(result['subtree_elements']) == 0:
            print(f"❌ CORRECTNESS FAILURE: No elements found in subtree")
            all_tests_passed = False
        elif outside:
            print(f"❌ CORRECTNESS FAILURE: {len(outside)} element(s) outside the "
                  f"requested subtree, e.g. {outside[0]}")
            all_tests_passed = False
        elif not internal:
            # This subtree has real edges between its own files; losing them all
            # means the traversal dropped dependencies, not that the code changed.
            print(f"❌ CORRECTNESS FAILURE: No internal dependencies found in subtree")
            all_tests_passed = False
        else:
            print(f"✅ Subtree dependencies: PASSED")
        
    except Exception:
        raise
    
    print()
    
    # Test 2: Get dependency chain
    print("🔗 Test 2: Get Dependency Chain")
    print("-" * 40)
    
    # Test dependency chain from ConstitutionalPrinciple
    # A module with real outgoing edges (273 at depth 2) and none incoming, so the
    # direction argument is observable. The previous subject had zero dependencies
    # in either direction, which made every assertion here vacuous.
    chain_element_path = "/langchain-ai/langchain/libs/core/langchain_core/runnables/base.py"
    
    search_start = time.perf_counter()
    try:
        result = DependencyService.get_dependency_chain(
            model=model,
            element_path=chain_element_path,
            direction="outgoing",
            max_depth=2
        )
        search_end = time.perf_counter()
        search_duration = (search_end - search_start) * 1000
        
        print(f"⏱️  Dependency chain: {search_duration:.2f} ms")
        print(f"🏷️  Root element: {result['root_element']}")
        print(f"🧭 Direction: {result['direction']}")
        print(f"🔗 Total dependencies: {len(result['all_dependencies'])}")
        print(f"📊 Chain paths: {len(result['chain'])}")
        
        deps = result['all_dependencies']
        wrong_direction = [d for d in deps if d.get('direction') != 'outgoing']
        not_from_root = [
            d for d in deps if d.get('depth') == 0 and d.get('from') != chain_element_path
        ]
        
        if search_duration > 300:  # 300ms limit for dependency chain
            print(f"❌ PERFORMANCE FAILURE: Analysis took {search_duration:.2f} ms, expected < 300 ms")
            all_tests_passed = False
        elif result['root_element'] != chain_element_path:
            print(f"❌ CORRECTNESS FAILURE: Root element mismatch")
            all_tests_passed = False
        elif not deps:
            print(f"❌ CORRECTNESS FAILURE: No dependencies returned for an element "
                  f"that has them")
            all_tests_passed = False
        elif wrong_direction:
            print(f"❌ CORRECTNESS FAILURE: {len(wrong_direction)} dependency/ies not "
                  f"marked 'outgoing', e.g. {wrong_direction[0]}")
            all_tests_passed = False
        elif not_from_root:
            print(f"❌ CORRECTNESS FAILURE: {len(not_from_root)} depth-0 dependency/ies "
                  f"do not originate at the root, e.g. {not_from_root[0]['from']}")
            all_tests_passed = False
        else:
            print(f"✅ Dependency chain: PASSED")
            
        # Show some example dependencies
        for dep in result['all_dependencies'][:3]:
            print(f"   - {dep['from']} -> {dep['to']} ({dep['type']})")
        
    except Exception:
        raise
    
    print()
    
    # Test 3: Get multiple elements
    print("📦 Test 3: Get Multiple Elements")
    print("-" * 40)
    
    # Test multiple element retrieval
    element_paths = [
        "/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai/models.py/ConstitutionalPrinciple",
        "/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai/base.py/ConstitutionalChain",
        "/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai/models.py",
        "/non/existent/path",  # This should not be found
        "/langchain-ai/langchain/libs/langchain/langchain/chains/constitutional_ai"
    ]
    
    search_start = time.perf_counter()
    try:
        result = DependencyService.get_multiple_elements(
            model=model,
            element_paths=element_paths,
            additional_fields=[]
        )
        search_end = time.perf_counter()
        search_duration = (search_end - search_start) * 1000
        
        print(f"⏱️  Multiple elements: {search_duration:.2f} ms")
        print(f"🎯 Requested: {result['requested_count']}")
        print(f"✅ Found: {result['found_count']}")
        print(f"❌ Not found: {len(result['not_found'])}")
        
        expected_found = {p for p in element_paths if p != "/non/existent/path"}
        returned = {e['path'] for e in result['elements']}
        
        if search_duration > 100:  # 100ms limit for multiple element retrieval
            print(f"❌ PERFORMANCE FAILURE: Retrieval took {search_duration:.2f} ms, expected < 100 ms")
            all_tests_passed = False
        elif result['found_count'] < 3:  # Should find at least 3 elements
            print(f"❌ CORRECTNESS FAILURE: Too few elements found")
            all_tests_passed = False
        elif len(result['not_found']) != 1:  # Should have exactly 1 not found
            print(f"❌ CORRECTNESS FAILURE: Expected 1 not found element")
            all_tests_passed = False
        elif returned != expected_found:
            missing = expected_found - returned
            extra = returned - expected_found
            print(f"❌ CORRECTNESS FAILURE: wrong elements returned "
                  f"(missing {sorted(missing)}, unexpected {sorted(extra)})")
            all_tests_passed = False
        else:
            print(f"✅ Multiple elements: PASSED")
            
        # Show found elements
        for element in result['elements']:
            print(f"   ✅ {element['name']} ({element['type']})")
        
        # Show not found elements  
        for path in result['not_found']:
            print(f"   ❌ {path}")
        
    except Exception:
        raise
    
    print()
    print("=" * 50)
    
    assert all_tests_passed, "performance or correctness checks failed; see output above"

