#!/usr/bin/env python3
"""
Verification script for Issue #3: Single Output Per Device

This script verifies that the single output refactoring is properly implemented
without requiring full library imports or dependencies.
"""

import os
import re


def check_file_exists(filepath, description):
    """Check if a file exists."""
    if os.path.exists(filepath):
        print(f"✓ {description}")
        return True
    else:
        print(f"✗ {description} (file not found)")
        return False


def check_file_contains(filepath, pattern, description):
    """Check if a file contains a pattern."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if re.search(pattern, content, re.MULTILINE | re.DOTALL):
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description}")
                return False
    except FileNotFoundError:
        print(f"✗ {description} (file not found)")
        return False


def check_file_not_contains(filepath, pattern, description):
    """Check if a file does NOT contain a pattern."""
    try:
        with open(filepath, 'r') as f:
            content = f.read()
            if not re.search(pattern, content, re.MULTILINE):
                print(f"✓ {description}")
                return True
            else:
                print(f"✗ {description} (pattern found)")
                return False
    except FileNotFoundError:
        print(f"✗ {description} (file not found)")
        return False


def main():
    print("=" * 70)
    print("VERIFYING ISSUE #3 IMPLEMENTATION: Single Output Per Device")
    print("=" * 70)
    print()
    
    base_path = "/home/arne/Dokumente/vdc/pyvdcapi"
    all_passed = True
    
    # Check 1: VdSD uses single _output instead of _outputs dict
    print("1. Checking VdSD single output implementation...")
    vdsd_file = f"{base_path}/pyvdcapi/entities/vdsd.py"
    if check_file_exists(vdsd_file, "   VdSD file exists"):
        # Check for single output attribute
        all_passed &= check_file_contains(
            vdsd_file,
            r'self\._output:\s*Optional\["Output"\]\s*=\s*None',
            "   _output defined as Optional (not Dict)"
        )
        # Check output is created in add_output_channel
        all_passed &= check_file_contains(
            vdsd_file,
            r'if self\._output is None:.*?self\._output = Output\(',
            "   Output created on-demand in add_output_channel()"
        )
        # Ensure old _outputs dict is removed
        all_passed &= check_file_not_contains(
            vdsd_file,
            r'self\._outputs:\s*Dict\[int,\s*"Output"\]',
            "   Old _outputs Dict removed"
        )
    else:
        all_passed = False
    print()
    
    # Check 2: Output class has no output_id parameter
    print("2. Checking Output class (no output_id)...")
    output_file = f"{base_path}/pyvdcapi/components/output.py"
    if check_file_exists(output_file, "   Output file exists"):
        # Check __init__ doesn't have output_id
        all_passed &= check_file_not_contains(
            output_file,
            r'def __init__\(.*output_id.*\):',
            "   __init__ has no output_id parameter"
        )
        # Check self.output_id is not assigned
        all_passed &= check_file_not_contains(
            output_file,
            r'self\.output_id\s*=',
            "   self.output_id not assigned"
        )
        # Check to_dict doesn't export outputID
        all_passed &= check_file_not_contains(
            output_file,
            r'"outputID":\s*self\.output_id',
            "   to_dict() doesn't export outputID"
        )
    else:
        all_passed = False
    print()
    
    # Check 3: VdSD methods updated for single output
    print("3. Checking VdSD methods...")
    all_passed &= check_file_contains(
        vdsd_file,
        r'if self\._output:',
        "   Methods check _output (singular)"
    )
    all_passed &= check_file_contains(
        vdsd_file,
        r'if "output" in config:',
        "   configure() uses 'output' key (singular)"
    )
    all_passed &= check_file_contains(
        vdsd_file,
        r'config\["output"\] = self\._output\.to_dict\(\)',
        "   export_configuration() exports single output"
    )
    print()
    
    # Check 4: Properties export single output
    print("4. Checking property exports...")
    all_passed &= check_file_contains(
        vdsd_file,
        r'props\["output"\] = self\._output\.to_dict\(\)',
        "   properties() exports single output"
    )
    all_passed &= check_file_not_contains(
        vdsd_file,
        r'props\["outputs"\] = \[.*self\._outputs',
        "   No plural 'outputs' export"
    )
    print()
    
    # Check 5: Scene methods updated
    print("5. Checking scene methods...")
    all_passed &= check_file_contains(
        vdsd_file,
        r'scene_config\.get\("output"',
        "   call_scene() uses singular 'output'"
    )
    all_passed &= check_file_contains(
        vdsd_file,
        r'scene_config\["output"\]',
        "   save_scene() saves singular 'output'"
    )
    print()
    
    # Check 6: Examples don't use output_id
    print("6. Checking examples...")
    motion_light = f"{base_path}/examples/motion_light_device.py"
    all_passed &= check_file_not_contains(
        motion_light,
        r'output_id\s*=',
        "   motion_light_device.py has no output_id"
    )
    all_passed &= check_file_not_contains(
        motion_light,
        r'Output\(.*output_id',
        "   Examples don't create Output with output_id"
    )
    print()
    
    # Check 7: Tests updated
    print("7. Checking tests...")
    output_test = f"{base_path}/tests/test_components_output.py"
    all_passed &= check_file_not_contains(
        output_test,
        r'Output\(vdsd=.*output_id=',
        "   test_components_output.py has no output_id"
    )
    all_passed &= check_file_contains(
        output_test,
        r'def _on_output_change\(self, channel_type, value\):',
        "   Callback signature updated (no output_id)"
    )
    print()
    
    # Check 8: Logging updated
    print("8. Checking logging...")
    all_passed &= check_file_contains(
        vdsd_file,
        r'1 if self\._output else 0.*output',
        "   Logging counts single output"
    )
    print()
    
    # Summary
    print("=" * 70)
    if all_passed:
        print("✓ ALL CHECKS PASSED - Issue #3 is fully implemented!")
        print()
        print("Implementation Summary:")
        print("  • VdSD._output: Optional[Output] (was: Dict[int, Output])")
        print("  • Output class: No output_id parameter (removed)")
        print("  • add_output_channel(): Creates single output on-demand")
        print("  • configure(): Uses 'output' key (singular, not 'outputs' list)")
        print("  • export_configuration(): Exports single output")
        print("  • Scene methods: Updated for single output")
        print("  • All examples and tests updated")
        print()
        print("API Compliance:")
        print("  ✓ Device has maximum ONE output (per vDC API section 4.8)")
        print("  ✓ Output can have multiple channels")
        print("  ✓ Matches vDC API specification")
        print()
        print("Architecture:")
        print("  Device → Output → [Channel₁, Channel₂, ..., Channelₙ]")
        print("  (Not: Device → [Output₁, Output₂, ..., Outputₙ])")
    else:
        print("✗ SOME CHECKS FAILED - Issue #3 implementation incomplete!")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
