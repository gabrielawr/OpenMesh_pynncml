# PyNNcml Development Setup

**Complete step-by-step guide for setting up the OpenMesh + PyNNcml development workspace**

This guide explains how to set up your workspace so you can develop and edit both OpenMesh and PyNNcml together.

---

## 📋 Overview

This project uses **two separate Git repositories**:
1. **OpenMesh** - Main project repository (this repo)
2. **PyNNcml** - Separate repository for the PyNNcml library (your fork)

Both repositories work together:
- OpenMesh uses PyNNcml for analysis
- PyNNcml is installed in **editable mode** so changes are immediately available
- You can edit both codebases and see changes instantly

---

## 🚀 Step-by-Step Setup Guide

### Step 1: Clone OpenMesh Repository

```bash
# Clone the OpenMesh repository
git clone <openmesh-repo-url> OpenMesh-fresh
cd OpenMesh-fresh
```

**Note:** Replace `<openmesh-repo-url>` with your actual OpenMesh repository URL.

### Step 2: Clone PyNNcml Repository

```bash
# From the OpenMesh project root, clone PyNNcml
git clone git@github.com:drorjac/PyNNcml.git PyNNcml
```

**Important:** 
- PyNNcml must be cloned into the `PyNNcml/` directory at the project root
- This is a **separate repository** - each collaborator needs to clone it
- PyNNcml is **not** a git submodule (it's an independent repo)

### Step 3: Set Up Python Environment

```bash
# Create virtual environment (recommended)
python3 -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate
```

### Step 4: Install Dependencies

```bash
# Install OpenMesh project dependencies
pip install -r requirements.txt

# Install PyNNcml dependencies
pip install -r PyNNcml/requirements.txt
```

### Step 5: Install PyNNcml in Editable Mode

```bash
# Install PyNNcml in editable mode
cd PyNNcml
pip install -e .
cd ..
```

**What is editable mode?**
- Creates a link to the source directory
- Changes to PyNNcml source files are **immediately available**
- No need to reinstall after each change
- Perfect for active development

### Step 6: Verify Setup

```bash
# Test that everything works
python -c "import pynncml; print('✓ PyNNcml imported successfully')"
```

Or run the test suite:
```bash
python src/analysis/pynncml_experiments/test/test_pynncml_setup.py
```

Or use the interactive notebook:
```bash
jupyter notebook src/analysis/pynncml_experiments/test/test_pynncml_setup.ipynb
```

---

## 🔧 Working with Both Repositories

### Directory Structure

```
OpenMesh-fresh/
├── PyNNcml/                    # Separate git repository
│   ├── .git/                   # PyNNcml's git
│   ├── pynncml/                # PyNNcml source code
│   └── ...
├── src/                        # OpenMesh source code
│   └── analysis/
│       └── pynncml_experiments/
├── .git/                       # OpenMesh's git
└── ...
```

### Making Changes to PyNNcml

1. **Edit PyNNcml source files:**
   ```bash
   # Edit any file in PyNNcml/pynncml/
   code PyNNcml/pynncml/utils.py
   ```

2. **Changes are immediately available:**
   - No reinstallation needed
   - Just import and use: `import pynncml`
   - Your changes are live!

3. **Commit to PyNNcml repository:**
   ```bash
   cd PyNNcml
   git add .
   git commit -m "Your changes"
   git push origin main
   cd ..
   ```

### Making Changes to OpenMesh

1. **Edit OpenMesh files:**
   ```bash
   # Edit any file in src/
   code src/analysis/pynncml_experiments/openmesh_pynncml_analysis.ipynb
   ```

2. **Commit to OpenMesh repository:**
   ```bash
   git add .
   git commit -m "Your changes"
   git push origin main
   ```

### Working Together

**For your partner/collaborator:**

1. They need to clone **both** repositories:
   ```bash
   # Clone OpenMesh
   git clone <openmesh-repo-url> OpenMesh-fresh
   cd OpenMesh-fresh
   
   # Clone PyNNcml
   git clone git@github.com:drorjac/PyNNcml.git PyNNcml
   ```

2. Then follow steps 3-6 above (environment setup)

3. When you push changes to either repo, they can pull:
   ```bash
   # Pull OpenMesh changes
   git pull
   
   # Pull PyNNcml changes
   cd PyNNcml
   git pull
   cd ..
   ```

---

## 🔄 Git Workflow

### Two Independent Repositories

**OpenMesh Repository:**
- Tracks OpenMesh project code
- Commits: analysis notebooks, data fetching scripts, project configs
- Location: Project root `.git/`

**PyNNcml Repository:**
- Tracks PyNNcml library code
- Commits: PyNNcml source code changes
- Location: `PyNNcml/.git/`

### Typical Workflow

```bash
# 1. Make changes to PyNNcml
cd PyNNcml
# ... edit files ...
git add .
git commit -m "Add new feature to PyNNcml"
git push origin main
cd ..

# 2. Use the changes in OpenMesh
# Changes are immediately available (editable install)
# ... use in notebooks/scripts ...

# 3. Commit OpenMesh work
git add .
git commit -m "Use new PyNNcml feature in analysis"
git push origin main
```

### Updating PyNNcml from Upstream

If you want to sync with the original PyNNcml repository:

```bash
cd PyNNcml

# Add upstream (if not already added)
git remote add upstream https://github.com/haihabi/PyNNcml.git

# Fetch and merge upstream changes
git fetch upstream
git merge upstream/main

# Push to your fork
git push origin main

cd ..
```

See `PyNNcml/UPDATE_FORK.md` for detailed instructions.

---

## ✅ Editable Install Benefits

When PyNNcml is installed with `pip install -e .`:

✅ **Changes to PyNNcml source files are immediately reflected**  
✅ **No need to reinstall after each code change**  
✅ **Perfect for active development**  
✅ **Python imports directly from the source directory**

### Example: Live Changes

1. Edit `PyNNcml/pynncml/utils.py`:
   ```python
   def get_working_device():
       print("🔧 [EDITABLE INSTALL TEST] Edit is live!")
       # ... rest of function
   ```

2. Use it immediately:
   ```python
   import pynncml
   pynncml.utils.get_working_device()  # Your edit is already there!
   ```

3. No reinstallation needed!

---

## 🧪 Verification

### Quick Test

```bash
python -c "import pynncml; print('✓ Import successful'); print(pynncml.__file__)"
```

Should show PyNNcml location in the source directory (editable install).

### Comprehensive Test

Run the test suite:
```bash
python src/analysis/pynncml_experiments/test/test_pynncml_setup.py
```

Or use the interactive notebook:
```bash
jupyter notebook src/analysis/pynncml_experiments/test/test_pynncml_setup.ipynb
```

---

## 📝 Current Status

- **PyNNcml location:** `PyNNcml/` (project root)
- **PyNNcml repository:** `git@github.com:drorjac/PyNNcml.git`
- **Upstream repository:** `https://github.com/haihabi/PyNNcml.git`
- **Installation:** Editable mode (`pip install -e .`)
- **Git status:** Separate repositories (not submodules)

---

## 🐛 Troubleshooting

### PyNNcml Not Found

**Error:** `ModuleNotFoundError: No module named 'pynncml'`

**Solution:**
```bash
# Make sure PyNNcml is cloned
ls PyNNcml/  # Should show PyNNcml directory

# Install in editable mode
cd PyNNcml
pip install -e .
cd ..
```

### Changes Not Reflected

**Problem:** Edits to PyNNcml don't appear

**Solution:**
1. Verify editable install: `pip show pynncml` should show location in PyNNcml directory
2. Reinstall: `cd PyNNcml && pip install -e .`
3. Restart Python kernel/terminal if needed

### Import Errors

**Problem:** Dependencies missing

**Solution:**
```bash
# Install all dependencies
pip install -r requirements.txt
pip install -r PyNNcml/requirements.txt
```

---

## 📚 Related Documentation

- `test/README.md` - Test suite documentation
- `PyNNcml/UPDATE_FORK.md` - How to update PyNNcml from upstream
- `../openmesh_pynncml_analysis.ipynb` - Example usage notebook

---

## 💡 Tips for Collaboration

1. **Communicate changes:** Let your partner know when you push to either repo
2. **Sync regularly:** Pull changes from both repos frequently
3. **Test after pulling:** Run tests after pulling PyNNcml changes
4. **Use branches:** Consider using feature branches for both repos
5. **Document edits:** Note any PyNNcml changes in commit messages

---

**Last updated:** 2025-01-26
