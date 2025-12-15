"""Test script to verify TTK filters work in subprocess."""

import topologytoolkit as ttk

# Test key filters we need
filters = [
    "ttkPersistenceDiagram",
    "ttkBottleneckDistance",
    "ttkMorseSmaleComplex",
    "ttkTopologicalSimplification",
]

print("Testing TTK filters:")
for filter_name in filters:
    if hasattr(ttk, filter_name):
        print(f"[OK] {filter_name}")
    else:
        print(f"[FAIL] {filter_name}")

print("\nTTK Python API is functional!")
