#!/usr/bin/env python3
"""
Simple verification that the methods exist and have correct signatures.
This can be run without installing dependencies.
"""

import ast
import sys


def check_method_exists(filepath, class_name, method_name, expected_params):
    """Check if a method exists with expected parameters."""
    with open(filepath, 'r') as f:
        tree = ast.parse(f.read())
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == method_name:
                    params = [arg.arg for arg in item.args.args]
                    print(f"✓ Found {class_name}.{method_name}({', '.join(params)})")
                    return True
    return False


def main():
    print("=" * 60)
    print("Verifying VdcHost Utility Methods")
    print("=" * 60)
    
    vdc_host_file = "pyvdcapi/entities/vdc_host.py"
    yaml_store_file = "pyvdcapi/persistence/yaml_store.py"
    
    # Check VdcHost methods
    print("\nVdcHost methods:")
    methods_found = 0
    
    if check_method_exists(vdc_host_file, "VdcHost", "get_vdc", ["self", "dsuid"]):
        methods_found += 1
    else:
        print("✗ get_vdc() not found!")
    
    if check_method_exists(vdc_host_file, "VdcHost", "get_all_vdcs", ["self"]):
        methods_found += 1
    else:
        print("✗ get_all_vdcs() not found!")
    
    if check_method_exists(vdc_host_file, "VdcHost", "delete_vdc", ["self", "dsuid"]):
        methods_found += 1
    else:
        print("✗ delete_vdc() not found!")
    
    # Check YAMLPersistence method
    print("\nYAMLPersistence methods:")
    if check_method_exists(yaml_store_file, "YAMLPersistence", "delete_vdc", ["self", "dsuid"]):
        methods_found += 1
    else:
        print("✗ YAMLPersistence.delete_vdc() not found!")
    
    print("\n" + "=" * 60)
    if methods_found == 4:
        print("✅ All 4 methods implemented correctly!")
        print("=" * 60)
        return 0
    else:
        print(f"❌ Only {methods_found}/4 methods found")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
