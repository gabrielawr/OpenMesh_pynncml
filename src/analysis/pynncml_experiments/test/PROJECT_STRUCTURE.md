# OpenMesh Project Structure

## 📁 Main Project Structure

```
OpenMesh-fresh/
├── PyNNcml/                    # Separate Git repository (your fork)
│   ├── pynncml/                # PyNNcml library source code
│   ├── examples/               # PyNNcml example notebooks
│   ├── tests/                  # PyNNcml unit tests
│   └── setup.py                # PyNNcml installation
│
├── src/                        # OpenMesh source code
│   ├── fetch_data/             # Data fetching modules
│   │   ├── noaa_asos/         # NOAA ASOS weather stations
│   │   ├── weather_underground/ # WU personal weather stations
│   │   └── OpenMesh/          # OpenMesh dataset download
│   │
│   ├── data/                   # Fetched data (gitignored)
│   │   ├── noaa_asos/         # ASOS CSV files
│   │   ├── wu_pws/            # Weather Underground data
│   │   └── openmesh/          # OpenMesh NetCDF files
│   │
│   └── analysis/              # Analysis notebooks
│       └── pynncml_experiments/
│           ├── test/           # PyNNcml setup tests
│           ├── openmesh_pynncml_analysis.ipynb
│           └── DEVELOPMENT_SETUP.md
│
├── dataset/                    # Sample data & examples
├── requirements.txt            # OpenMesh dependencies
└── README.md                   # Main project documentation
```

---

## 🔑 Key Components

### 1. **Two Git Repositories**
- **OpenMesh** - Main project (this repo)
- **PyNNcml** - Separate library repo (`git@github.com:drorjac/PyNNcml.git`)

### 2. **Data Pipeline**
```
fetch_data/ → data/ → analysis/
   (download)  (store)  (process)
```

### 3. **PyNNcml Integration**
- **Location:** `PyNNcml/` (separate repo, cloned separately)
- **Installation:** Editable mode (`pip install -e .`)
- **Usage:** Import in analysis notebooks
- **Tests:** `src/analysis/pynncml_experiments/test/`

---

## 📊 Main Directories

| Directory | Purpose | Git Status |
|-----------|---------|------------|
| `PyNNcml/` | PyNNcml library source | Separate repo |
| `src/fetch_data/` | Data download scripts | Tracked |
| `src/data/` | Downloaded datasets | Gitignored |
| `src/analysis/` | Analysis notebooks | Tracked |
| `dataset/` | Sample data/examples | Tracked |

---

## 🎯 Quick Reference

**Setup:**
1. Clone OpenMesh repo
2. Clone PyNNcml repo → `PyNNcml/`
3. `pip install -r requirements.txt`
4. `cd PyNNcml && pip install -e .`

**Workflow:**
- Edit PyNNcml → Changes are live (editable install)
- Edit OpenMesh → Commit to OpenMesh repo
- Both repos work independently

**Tests:**
- `test/test_pynncml_setup.py` - Command-line tests
- `test/test_pynncml_setup.ipynb` - Interactive notebook

---

**See:** `DEVELOPMENT_SETUP.md` for complete setup guide

