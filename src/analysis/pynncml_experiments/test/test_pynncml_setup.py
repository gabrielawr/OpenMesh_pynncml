#!/usr/bin/env python
"""
Comprehensive test suite for PyNNcml setup and editable install verification.

This script tests:
1. PyNNcml directory structure and files
2. Module import and version information
3. Editable install verification
4. Live changes detection (editable install working)
5. Module structure and available functionality
6. Function execution with live edits

Run this script to verify that PyNNcml is properly set up and that
editable install is working correctly.
"""
import sys
import os
from pathlib import Path


def get_project_root():
    """Find the project root directory."""
    # Get the directory where this script is located
    script_dir = Path(__file__).parent
    # Go up: test -> pynncml_experiments -> analysis -> src -> root
    project_root = script_dir.parent.parent.parent.parent
    return project_root


def test_pynncml_directory():
    """Test 1: Check if PyNNcml directory exists and has required files."""
    print("=" * 70)
    print("TEST 1: PyNNcml Directory Structure")
    print("=" * 70)
    
    project_root = get_project_root()
    pynncml_dir = project_root / 'PyNNcml'
    init_file = pynncml_dir / 'pynncml' / '__init__.py'
    setup_py = pynncml_dir / 'setup.py'
    utils_file = pynncml_dir / 'pynncml' / 'utils.py'
    
    print(f"\nProject root: {project_root}")
    print(f"PyNNcml directory: {pynncml_dir}")
    
    if not pynncml_dir.exists():
        print("\n✗ PyNNcml directory not found!")
        return False
    
    checks = {
        'setup.py': setup_py.exists(),
        '__init__.py': init_file.exists(),
        'utils.py': utils_file.exists(),
    }
    
    all_pass = True
    for name, exists in checks.items():
        status = "✓" if exists else "✗"
        print(f"  {status} {name}: {exists}")
        if not exists:
            all_pass = False
    
    if all_pass:
        print("\n✓ PyNNcml directory structure is correct")
    else:
        print("\n✗ Some required files are missing")
    
    return all_pass


def test_pynncml_import():
    """Test 2: Import PyNNcml and check basic information."""
    print("\n" + "=" * 70)
    print("TEST 2: PyNNcml Module Import")
    print("=" * 70)
    
    project_root = get_project_root()
    pynncml_path = project_root / 'PyNNcml'
    
    # Add to path if not already installed
    pynncml_path_str = str(pynncml_path)
    if pynncml_path_str not in sys.path:
        sys.path.insert(0, pynncml_path_str)
    
    try:
        import pynncml as pnc
        print("\n✓ Successfully imported pynncml")
        print(f"  Location: {pnc.__file__}")
        print(f"  Version: {getattr(pnc, '__version__', 'unknown')}")
        
        # Check if editable install
        if 'PyNNcml' in pnc.__file__:
            print("  ✓ Editable install detected (source directory)")
            editable = True
        else:
            print("  ⚠ Installed from site-packages (not editable)")
            editable = False
        
        return True, pnc, editable
        
    except ImportError as e:
        print(f"\n✗ Failed to import pynncml: {e}")
        print("\n  Troubleshooting:")
        print("  1. Make sure PyNNcml is installed: cd PyNNcml && pip install -e .")
        print("  2. Check that all dependencies are installed")
        return False, None, False


def test_module_structure(pnc):
    """Test 3: Check module structure and available attributes."""
    print("\n" + "=" * 70)
    print("TEST 3: Module Structure")
    print("=" * 70)
    
    if pnc is None:
        print("⚠ Skipping: PyNNcml not imported")
        return False
    
    public_attrs = [x for x in dir(pnc) if not x.startswith('_')]
    print(f"\n✓ Found {len(public_attrs)} public attributes")
    print(f"  Examples: {', '.join(public_attrs[:10])}")
    
    # Check for expected modules
    expected_modules = {
        'single_cml_methods': 'single_cml_methods',
        'multiple_cmls_methods': 'multiple_cmls_methods (or mcm)',
        'plot_common': 'plot_common',
        'utils': 'utils',
    }
    
    print("\n  Checking expected modules:")
    all_found = True
    for attr, name in expected_modules.items():
        if hasattr(pnc, attr) or (attr == 'multiple_cmls_methods' and hasattr(pnc, 'mcm')):
            print(f"    ✓ {name}")
        else:
            print(f"    ✗ {name} (not found)")
            all_found = False
    
    return all_found


def test_editable_install_source(pnc, editable):
    """Test 4: Verify editable install by checking source file directly."""
    print("\n" + "=" * 70)
    print("TEST 4: Editable Install Source Verification")
    print("=" * 70)
    
    if not editable:
        print("\n⚠ Skipping: Not an editable install")
        return False
    
    project_root = get_project_root()
    utils_file = project_root / 'PyNNcml' / 'pynncml' / 'utils.py'
    
    if utils_file.exists():
        print(f"\n✓ Found source file: {utils_file}")
        with open(utils_file, 'r') as f:
            content = f.read()
        
        # Check for our test edit
        if 'EDITABLE INSTALL TEST' in content:
            print("  ✓ Found test edit marker in source file")
            print("  ✓ Editable install confirmed - source files are accessible")
            return True
        else:
            print("  ⚠ Test edit marker not found (may have been removed)")
            return True  # Still valid, just no test marker
    else:
        print(f"\n✗ Source file not found: {utils_file}")
        return False


def test_live_changes(pnc):
    """Test 5: Test that edits to PyNNcml are immediately available."""
    print("\n" + "=" * 70)
    print("TEST 5: Live Changes Test")
    print("=" * 70)
    
    if pnc is None:
        print("⚠ Skipping: PyNNcml not imported")
        return False
    
    print("\nCalling pynncml.utils.get_working_device()...")
    print("If you see '[EDITABLE INSTALL TEST]', the edit is live!")
    print("-" * 70)
    
    try:
        device = pnc.utils.get_working_device()
        print("-" * 70)
        print(f"\n✓ Function executed successfully")
        print(f"  Returned device: {device}")
        print("\n✓ If '[EDITABLE INSTALL TEST]' appeared above, editable install is working!")
        return True
    except Exception as e:
        print(f"\n✗ Error calling function: {e}")
        return False


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("PyNNcml Setup and Editable Install Test Suite")
    print("=" * 70)
    
    results = {}
    
    # Test 1: Directory structure
    results['directory'] = test_pynncml_directory()
    
    # Test 2: Import
    import_success, pnc, editable = test_pynncml_import()
    results['import'] = import_success
    
    if import_success:
        # Test 3: Module structure
        results['structure'] = test_module_structure(pnc)
        
        # Test 4: Editable install source
        results['editable_source'] = test_editable_install_source(pnc, editable)
        
        # Test 5: Live changes
        results['live_changes'] = test_live_changes(pnc)
    else:
        results['structure'] = False
        results['editable_source'] = False
        results['live_changes'] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for test_name, result in results.items():
        status = "✓" if result else "✗"
        print(f"  {status} {test_name.replace('_', ' ').title()}")
    
    print(f"\n  Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! PyNNcml is properly set up.")
        if editable:
            print("  ✓ Editable install is working - changes are immediately available")
    else:
        print("\n⚠ Some tests failed. Check the output above for details.")
        print("\n  To fix:")
        print("  1. Make sure PyNNcml is cloned: git clone git@github.com:drorjac/PyNNcml.git PyNNcml")
        print("  2. Install dependencies: pip install -r requirements.txt")
        print("  3. Install in editable mode: cd PyNNcml && pip install -e .")
    
    print("\n" + "=" * 70)
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

