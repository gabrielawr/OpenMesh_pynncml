# PyNNcml Test Suite

This directory contains tests for verifying PyNNcml setup and integration with the OpenMesh project.

## Contents

### `test_pynncml_setup.ipynb`
Interactive Jupyter notebook for testing PyNNcml setup. This is the **recommended way** to test your setup as it provides:
- Step-by-step setup verification
- Interactive dependency installation
- Visual feedback and troubleshooting
- Comprehensive test coverage

**Usage:** Open in Jupyter and run all cells.

### `test_pynncml_setup.py`
Comprehensive Python test script that can be run from the command line. Merges all previous test files into one unified test suite.

**Tests included:**
1. **Directory Structure** - Verifies PyNNcml directory exists with required files
2. **Module Import** - Tests PyNNcml can be imported and checks version
3. **Module Structure** - Verifies expected modules are available
4. **Editable Install Source** - Confirms source files are accessible
5. **Live Changes** - Tests that edits to PyNNcml are immediately available

**Usage:**
```bash
# From project root
python -m src.analysis.pynncml_experiments.test.test_pynncml_setup

# Or from this directory
cd src/analysis/pynncml_experiments/test
python test_pynncml_setup.py
```

## What is `__init__.py`?

The `__init__.py` file makes this directory a Python **package**. This allows:

1. **Module imports**: You can import the test module from other parts of the project
   ```python
   from src.analysis.pynncml_experiments.test import test_pynncml_setup
   ```

2. **Package structure**: Python recognizes this as a package, enabling:
   - Relative imports within the package
   - Running as a module: `python -m src.analysis.pynncml_experiments.test.test_pynncml_setup`
   - Better IDE support and code navigation

3. **Namespace organization**: Groups related test code together

Even if `__init__.py` is empty, it serves the important purpose of marking the directory as a package.

## Test Requirements

Before running tests, ensure:

1. **PyNNcml is cloned:**
   ```bash
   git clone git@github.com:drorjac/PyNNcml.git PyNNcml
   ```

2. **Dependencies are installed:**
   ```bash
   pip install -r requirements.txt
   pip install -r PyNNcml/requirements.txt
   ```

3. **PyNNcml is installed in editable mode:**
   ```bash
   cd PyNNcml
   pip install -e .
   ```

## What the Tests Verify

### Editable Install
When PyNNcml is installed with `pip install -e .`, it creates an **editable install**. This means:
- ✅ Changes to PyNNcml source files are immediately reflected
- ✅ No need to reinstall after each code change
- ✅ Perfect for active development and testing
- ✅ Python imports directly from the source directory

### Live Changes Test
The test suite includes a specific test that:
1. Calls a PyNNcml function (`get_working_device()`)
2. Checks for a test edit marker in the output
3. Confirms that changes to source files are immediately available

This demonstrates that editable install is working correctly.

## Troubleshooting

### Import Errors
If you see `ModuleNotFoundError: No module named 'pynncml'`:
- Make sure PyNNcml is installed: `cd PyNNcml && pip install -e .`
- Verify you're using the correct Python environment
- Check that all dependencies are installed

### Editable Install Not Working
If changes to PyNNcml source files aren't reflected:
- Verify installation: `pip show pynncml` should show location in PyNNcml directory
- Reinstall in editable mode: `cd PyNNcml && pip install -e .`
- Check that you're editing files in the correct PyNNcml directory

### Test Failures
If tests fail:
1. Check the error messages for specific issues
2. Verify PyNNcml directory structure is correct
3. Ensure all dependencies are installed
4. Try reinstalling PyNNcml in editable mode

## Related Files

- `../DEVELOPMENT_SETUP.md` - Detailed guide on editable install setup
- `../openmesh_pynncml_analysis.ipynb` - Example notebook using PyNNcml
- `../../../../PyNNcml/` - PyNNcml source directory

