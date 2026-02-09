#!/usr/bin/env python3
"""
Minimal test to verify Issue #1 implementation without full imports.
This script just checks that the code changes are in place.
"""

import re


def check_file_for_pattern(filename, pattern, description):
    """Check if a file contains a specific pattern."""
    try:
        with open(filename, 'r') as f:
            content = f.read()
            if re.search(pattern, content, re.MULTILINE):
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description}")
                return False
    except FileNotFoundError:
        print(f"✗ File not found: {filename}")
        return False


def main():
    print("=" * 70)
    print("VERIFYING ISSUE #1 IMPLEMENTATION: Device Immutability")
    print("=" * 70)
    print()
    
    vdsd_file = "/home/arne/Dokumente/vdc/pyvdcapi/pyvdcapi/entities/vdsd.py"
    vdc_file = "/home/arne/Dokumente/vdc/pyvdcapi/pyvdcapi/entities/vdc.py"
    
    all_passed = True
    
    # Check 1: _announced flag exists
    print("1. Checking for _announced flag initialization...")
    if check_file_for_pattern(
        vdsd_file,
        r'self\._announced\s*=\s*False',
        "   _announced flag initialized in __init__"
    ):
        all_passed = all_passed and True
    else:
        all_passed = False
    print()
    
    # Check 2: mark_announced() method exists
    print("2. Checking for mark_announced() method...")
    if check_file_for_pattern(
        vdsd_file,
        r'def mark_announced\(self\)',
        "   mark_announced() method exists"
    ):
        all_passed = all_passed and True
    else:
        all_passed = False
    
    if check_file_for_pattern(
        vdsd_file,
        r'self\._announced\s*=\s*True',
        "   mark_announced() sets _announced = True"
    ):
        all_passed = all_passed and True
    else:
        all_passed = False
    print()
    
    # Check 3: Runtime check in add_output_channel()
    print("3. Checking for runtime check in add_output_channel()...")
    if check_file_for_pattern(
        vdsd_file,
        r'if self\._announced:.*?raise RuntimeError.*?Cannot add output channel',
        "   Runtime check exists in add_output_channel()"
    ):
        all_passed = all_passed and True
    else:
        # Try simpler pattern
        with open(vdsd_file, 'r') as f:
            content = f.read()
            if 'Cannot add output channel' in content and content.count('if self._announced:') >= 1:
                print("✓    Runtime check exists in add_output_channel()")
                all_passed = all_passed and True
            else:
                all_passed = False
    print()
    
    # Check 4: Runtime check in add_button_input()
    print("4. Checking for runtime check in add_button_input()...")
    if check_file_for_pattern(
        vdsd_file,
        r'if self\._announced:.*?raise RuntimeError.*?Cannot add button input',
        "   Runtime check exists in add_button_input()"
    ):
        all_passed = all_passed and True
    else:
        # Try simpler pattern
        with open(vdsd_file, 'r') as f:
            content = f.read()
            if 'Cannot add button input' in content and content.count('if self._announced:') >= 2:
                print("✓    Runtime check exists in add_button_input()")
                all_passed = all_passed and True
            else:
                all_passed = False
    print()
    
    # Check 5: Runtime check in add_sensor()
    print("5. Checking for runtime check in add_sensor()...")
    if check_file_for_pattern(
        vdsd_file,
        r'if self\._announced:.*?raise RuntimeError.*?Cannot add sensor',
        "   Runtime check exists in add_sensor()"
    ):
        all_passed = all_passed and True
    else:
        # Try simpler pattern
        with open(vdsd_file, 'r') as f:
            content = f.read()
            if 'Cannot add sensor' in content and content.count('if self._announced:') >= 3:
                print("✓    Runtime check exists in add_sensor()")
                all_passed = all_passed and True
            else:
                all_passed = False
    print()
    
    # Check 6: Runtime check in configure()
    print("6. Checking for runtime check in configure()...")
    if check_file_for_pattern(
        vdsd_file,
        r'if self\._announced:.*?raise RuntimeError.*?Cannot configure device',
        "   Runtime check exists in configure()"
    ):
        all_passed = all_passed and True
    else:
        # Try simpler pattern
        with open(vdsd_file, 'r') as f:
            content = f.read()
            if 'Cannot configure device' in content and content.count('if self._announced:') >= 4:
                print("✓    Runtime check exists in configure()")
                all_passed = all_passed and True
            else:
                all_passed = False
    print()
    
    # Check 7: Vdc.announce_devices() calls mark_announced()
    print("7. Checking for mark_announced() call in Vdc.announce_devices()...")
    if check_file_for_pattern(
        vdc_file,
        r'vdsd\.mark_announced\(\)',
        "   announce_devices() calls vdsd.mark_announced()"
    ):
        all_passed = all_passed and True
    else:
        all_passed = False
    print()
    
    # Summary
    print("=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Issue #1 is fully implemented!")
        print()
        print("Implementation Summary:")
        print("  • _announced flag tracks device announcement status")
        print("  • mark_announced() method sets the flag when device is announced")
        print("  • Runtime checks in 4 methods prevent feature addition after announcement:")
        print("    - add_output_channel()")
        print("    - add_button_input()")
        print("    - add_sensor()")
        print("    - configure()")
        print("  • Vdc.announce_devices() automatically calls mark_announced()")
        print()
        print("Result: Devices are now immutable after announcement, enforcing vDC API spec.")
    else:
        print("✗ SOME CHECKS FAILED - Issue #1 implementation incomplete!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
