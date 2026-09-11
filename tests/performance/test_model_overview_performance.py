#!/usr/bin/env python3
"""
Comprehensive performance test for sgraph_get_model_overview tool
Tests OverviewService.get_model_overview at a range of depths.
The MCP tool layer is not covered here - both cases call the service directly
"""


import pytest
import time
import sys
import os

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.core.model_manager import ModelManager
from src.services.overview_service import OverviewService

@pytest.mark.asyncio
async def test_helper_performance():
    """Test the direct service function performance"""
    
    print("🔍 Testing OverviewService.get_model_overview performance...")
    
    # Initialize model manager
    model_manager = ModelManager()
    
    # Test with the combined model
    model_path = os.path.join(os.path.dirname(__file__), "..", "sgraph-and-mcp.xml.zip")
    
    try:
        print(f"📁 Loading model from: {model_path}")
        model_id = await model_manager.load_model(model_path)
        model = model_manager.get_model(model_id)
        
        if model is None:
            pytest.fail("Failed to retrieve model")
        
        print(f"✅ Model loaded successfully (ID: {model_id})")
        
        # Performance requirements from AI agent perspective
        test_cases = [
            {"depth": 1, "target_ms": 25, "description": "Quick root overview"},
            {"depth": 2, "target_ms": 50, "description": "Directory structure"},
            {"depth": 3, "target_ms": 75, "description": "File-level overview"},
            {"depth": 4, "target_ms": 100, "description": "Detailed structure"},
            {"depth": 5, "target_ms": 150, "description": "Deep analysis"},
        ]
        
        all_passed = True
        
        for test_case in test_cases:
            depth = test_case["depth"]
            target_ms = test_case["target_ms"]
            description = test_case["description"]
            
            print(f"\n📊 Testing depth {depth} - {description} (target: <{target_ms}ms)")
            
            # Warm up call
            OverviewService.get_model_overview(model, max_depth=depth, include_counts=True)
            
            # Multiple runs for accurate measurement
            times = []
            for i in range(5):
                start_time = time.perf_counter()
                result = OverviewService.get_model_overview(model, max_depth=depth, include_counts=True)
                end_time = time.perf_counter()
                times.append((end_time - start_time) * 1000)
            
            avg_ms = sum(times) / len(times)
            min_ms = min(times)
            max_ms = max(times)
            
            # Validate results
            total_elements = result['summary']['total_elements']
            depth_counts = result['summary']['depth_counts']
            type_counts = result['summary']['type_distribution']
            
            print(f"  ⏱️  Avg: {avg_ms:.1f}ms, Min: {min_ms:.1f}ms, Max: {max_ms:.1f}ms")
            print(f"  📈 Total elements: {total_elements}")
            print(f"  📊 Depths found: {list(depth_counts.keys())}")
            print(f"  🏷️  Types: {len(type_counts)} different types")
            
            # Check performance
            if avg_ms <= target_ms:
                print(f"  ✅ PASSED (avg {avg_ms:.1f}ms ≤ {target_ms}ms target)")
            else:
                print(f"  ❌ FAILED (avg {avg_ms:.1f}ms > {target_ms}ms target)")
                all_passed = False
            
        assert all_passed, "one or more measurements missed their target; see output above"
        
    except Exception as e:
        print(f"❌ Error during helper performance test: {str(e)}")
        raise

@pytest.mark.asyncio
async def test_service_performance():
    """Test the service call performance"""
    
    print("\n🔧 Testing service call performance...")
    
    # Initialize model manager and load model
    model_manager = ModelManager()
    model_path = os.path.join(os.path.dirname(__file__), "..", "sgraph-and-mcp.xml.zip")
    model_id = await model_manager.load_model(model_path)
    model = model_manager.get_model(model_id)
    
    # Test MCP tool performance
    test_cases = [
        {"depth": 1, "target_ms": 30},
        {"depth": 3, "target_ms": 80}, 
        {"depth": 5, "target_ms": 160},
    ]
    
    all_passed = True
    
    for test_case in test_cases:
        depth = test_case["depth"]
        target_ms = test_case["target_ms"]
        
        print(f"\n🛠️  Testing service depth {depth} (target: <{target_ms}ms)")
        
        # Warm up
        OverviewService.get_model_overview(model, max_depth=depth, include_counts=True)
        
        # Multiple runs
        times = []
        for i in range(5):
            start_time = time.perf_counter()
            result = OverviewService.get_model_overview(model, max_depth=depth, include_counts=True)
            end_time = time.perf_counter()
            times.append((end_time - start_time) * 1000)
        
        avg_ms = sum(times) / len(times)
        
        # Validate response structure
        if not result or 'summary' not in result:
            print(f"  ❌ Service returned invalid result")
            all_passed = False
            continue
        
        elements_count = result['summary']['total_elements']
        
        print(f"  ⏱️  Avg service call: {avg_ms:.1f}ms")
        print(f"  📊 Elements returned: {elements_count}")
        
        if avg_ms <= target_ms:
            print(f"  ✅ PASSED (avg {avg_ms:.1f}ms ≤ {target_ms}ms target)")
        else:
            print(f"  ❌ FAILED (avg {avg_ms:.1f}ms > {target_ms}ms target)")
            all_passed = False
    
    assert all_passed, "one or more measurements missed their target; see output above"

@pytest.mark.asyncio
async def test_scalability():
    """Test tool performance with different model sizes"""
    
    print("\n📏 Testing scalability characteristics...")
    
    model_manager = ModelManager()
    model_path = os.path.join(os.path.dirname(__file__), "..", "sgraph-and-mcp.xml.zip")
    model_id = await model_manager.load_model(model_path)
    model = model_manager.get_model(model_id)
    
    # Test scaling with depth
    print("  🔍 Analyzing performance scaling with depth...")
    
    scaling_results = []
    for depth in range(1, 8):
        start_time = time.perf_counter()
        result = OverviewService.get_model_overview(model, max_depth=depth, include_counts=False)
        end_time = time.perf_counter()
        
        duration_ms = (end_time - start_time) * 1000
        elements = result['summary']['total_elements']
        
        depth_counts = result['summary'].get('depth_counts', {})
        max_seen = max((int(d) for d in depth_counts), default=0)

        scaling_results.append({
            "depth": depth,
            "duration_ms": duration_ms,
            "elements": elements,
            "max_seen": max_seen
        })
        
        print(f"    Depth {depth}: {duration_ms:.1f}ms, {elements} elements")
    
    # Check if performance scales reasonably (should be roughly linear or better)
    print("\n  📈 Scalability analysis:")
    for i in range(1, len(scaling_results)):
        prev = scaling_results[i-1]
        curr = scaling_results[i]
        
        element_ratio = curr["elements"] / prev["elements"] if prev["elements"] > 0 else 1
        time_ratio = curr["duration_ms"] / prev["duration_ms"] if prev["duration_ms"] > 0 else 1
        
        efficiency = element_ratio / time_ratio if time_ratio > 0 else 0
        
        print(f"    Depth {prev['depth']}→{curr['depth']}: {efficiency:.1f}x efficiency (elements/time ratio)")

    # The per-step efficiency ratios above are noise at sub-millisecond timings, so
    # assert on what is stable. Absolute wall-clock alone is a weak guard: a 100x
    # constant-factor regression still lands inside any bound loose enough to
    # survive a slow machine. Cost per element does not have that blind spot, and
    # the structural checks catch an overview that returns nothing or quietly
    # ignores max_depth - both of which a pure timing assertion rates as excellent.
    for prev, curr in zip(scaling_results, scaling_results[1:]):
        assert curr["elements"] > prev["elements"], (
            f"depth {curr['depth']} returned {curr['elements']} elements, "
            f"not more than depth {prev['depth']} at {prev['elements']}"
        )

    for row in scaling_results:
        assert row["max_seen"] == row["depth"], (
            f"asked for depth {row['depth']} but the tree reaches {row['max_seen']}"
        )

    deepest = scaling_results[-1]
    assert deepest["elements"] > 1000, (
        f"fixture model yielded only {deepest['elements']} elements at depth "
        f"{deepest['depth']}; expected >1000 - has the test model changed?"
    )

    us_per_element = deepest["duration_ms"] / deepest["elements"] * 1000
    assert us_per_element < 20, (
        f"overview cost {us_per_element:.2f} us/element, expected < 20 "
        f"({deepest['duration_ms']:.1f}ms for {deepest['elements']} elements)"
    )

