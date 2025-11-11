# RaceCraft AI - Project Structure

## Proposed Directory Organization

```
motorsport-modeling/
├── README.md                          # Project overview, quick start
├── pyproject.toml                     # Project config, dependencies (uv/pip)
├── .gitignore                         # Git exclusions
├── .python-version                    # Python version for uv
│
├── docs/                              # All documentation
│   ├── project/
│   │   ├── proposal.md               # Main project proposal
│   │   └── tiers.md                  # Implementation tiers
│   ├── domain/
│   │   ├── racing_fundamentals.md    # Racing theory
│   │   ├── racing_with_traffic.md    # Traffic management
│   │   └── quantifiable_metrics.md   # Metrics definitions
│   ├── data/
│   │   ├── data_guide.md             # Data setup & structure
│   │   ├── datasets_notes.md         # Known issues
│   │   ├── gps_availability.md       # GPS data by track
│   │   └── track_comparison.md       # Track comparisons
│   ├── technical/
│   │   ├── simulation_requirements.md
│   │   └── gps_capabilities.md
│   └── hackathon/
│       └── rules.md                  # Competition rules
│
├── src/                               # Source code (Python package)
│   ├── racecraft/
│   │   ├── __init__.py
│   │   ├── data/                     # Data loading & processing
│   │   │   ├── __init__.py
│   │   │   ├── loaders.py           # Telemetry, lap time loaders
│   │   │   ├── processors.py        # Data cleaning, transformations
│   │   │   └── validators.py        # Data quality checks
│   │   ├── metrics/                  # Performance metrics
│   │   │   ├── __init__.py
│   │   │   ├── consistency.py       # Lap time consistency
│   │   │   ├── efficiency.py        # Coasting, throttle usage
│   │   │   ├── braking.py           # Braking analysis
│   │   │   └── gps.py               # Racing line metrics
│   │   ├── models/                   # Predictive models
│   │   │   ├── __init__.py
│   │   │   ├── lap_time.py          # Lap time prediction
│   │   │   ├── position.py          # Position prediction
│   │   │   ├── degradation.py       # Tire degradation
│   │   │   └── strategy.py          # Pit strategy
│   │   ├── visualization/            # Plotting & dashboards
│   │   │   ├── __init__.py
│   │   │   ├── telemetry.py         # Telemetry plots
│   │   │   ├── gps.py               # Track maps, racing lines
│   │   │   └── dashboard.py         # Interactive dashboard
│   │   └── utils/                    # Utilities
│   │       ├── __init__.py
│   │       ├── config.py            # Configuration
│   │       └── helpers.py           # Helper functions
│
├── scripts/                           # Standalone scripts
│   ├── README.md
│   ├── create_sample_data.py         # Data sampling
│   ├── process_telemetry.py          # Batch processing
│   └── train_models.py               # Model training pipeline
│
├── notebooks/                         # Jupyter notebooks (exploratory)
│   ├── 01_data_exploration.ipynb
│   ├── 02_metrics_development.ipynb
│   ├── 03_model_training.ipynb
│   └── 04_visualization_prototypes.ipynb
│
├── tests/                             # Unit tests
│   ├── __init__.py
│   ├── conftest.py                   # Pytest fixtures
│   ├── test_data/                    # Test data fixtures
│   ├── test_loaders.py
│   ├── test_metrics.py
│   └── test_models.py
│
├── data/                              # Data directory
│   ├── raw/                          # Raw data (gitignored)
│   │   ├── *.zip
│   │   └── indianapolis/
│   ├── processed/                    # Processed data (gitignored)
│   │   └── *.parquet
│   ├── samples/                      # Sample data (committed)
│   │   └── indy_telemetry_sample.csv
│   ├── tracks/                       # Track metadata (committed)
│   │   ├── indy.json
│   │   └── indy_table.csv
│   └── README.md                     # Data directory guide
│
├── outputs/                           # Generated outputs (gitignored)
│   ├── models/                       # Trained models
│   ├── figures/                      # Generated plots
│   └── reports/                      # Analysis reports
│
└── app/                               # Dashboard application (optional)
    ├── streamlit_app.py              # Streamlit dashboard
    └── components/                    # UI components
```

## Key Principles

### 1. **Separation of Concerns**
- `src/racecraft/` - Reusable library code
- `scripts/` - One-off scripts and pipelines
- `notebooks/` - Exploratory analysis
- `docs/` - All documentation

### 2. **Data Organization**
- `data/raw/` - Never modify, gitignored
- `data/processed/` - Derived data, gitignored
- `data/samples/` - Small samples for testing, committed
- `data/tracks/` - Metadata, committed

### 3. **Code as Package**
- Install as: `uv pip install -e .`
- Import as: `from racecraft.data import load_telemetry`
- Testable with pytest

### 4. **Documentation Structure**
- **domain/** - Racing knowledge (theory, principles)
- **project/** - Project planning and design
- **data/** - Data guides and references
- **technical/** - Technical specifications
- **hackathon/** - Competition-specific info

## Migration Plan

### Phase 1: Create Structure
```bash
# Create all directories
mkdir -p src/racecraft/{data,metrics,models,visualization,utils}
mkdir -p docs/{project,domain,data,technical,hackathon}
mkdir -p notebooks tests/test_data outputs/{models,figures,reports}
mkdir -p data/{raw,processed,samples,tracks} app
```

### Phase 2: Move Existing Files

**Documentation:**
```bash
# Project docs
mv project_proposal.md docs/project/proposal.md
mv project_tiers.md docs/project/tiers.md

# Domain knowledge
mv racing_fundamentals.md docs/domain/
mv racing_with_traffic.md docs/domain/
mv quantifiable_metrics.md docs/domain/

# Data documentation
mv data_guide_vir.md docs/data/data_guide.md
mv gps_data_availability.md docs/data/
mv gps_capabilities_breakdown.md docs/data/
mv track_comparison_gps.md docs/data/

# Technical docs
mv simulation_requirements.md docs/technical/

# Hackathon
mv data/Toyota_Gazoo_Racing_Hackathon_Rules.md docs/hackathon/rules.md
mv data/Toyota_Gazoo_Racing_Datasets_Notes_KnownIssues.md docs/data/datasets_notes.md
```

**Data files:**
```bash
# Track metadata
mv data/indy.json data/tracks/
mv data/indy_table.csv data/tracks/
```

**Create empty __init__.py files:**
```bash
touch src/racecraft/__init__.py
touch src/racecraft/{data,metrics,models,visualization,utils}/__init__.py
touch tests/__init__.py
```

### Phase 3: Setup Python Environment

**Create pyproject.toml:**
- Project metadata
- Dependencies (pandas, numpy, matplotlib, etc.)
- Development dependencies (pytest, jupyter, black, etc.)
- Build system configuration

**Create .python-version:**
```
3.11
```

## Next Steps After Setup

1. Initialize uv environment
2. Install dependencies
3. Run tests (even if empty initially)
4. Start implementing in `src/racecraft/`

## Benefits of This Structure

✅ **Professional** - Standard Python project layout
✅ **Scalable** - Easy to add new features
✅ **Testable** - Clear test organization
✅ **Importable** - Use code across scripts/notebooks
✅ **Documented** - Clear documentation hierarchy
✅ **Collaborative** - Easy for others to understand
✅ **Maintainable** - Logical organization
